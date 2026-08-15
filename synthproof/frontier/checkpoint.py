"""Per-cell checkpointing for long experiment grids.

WHY THIS EXISTS. The 75-cell H1 grid has now been lost twice: once to a `MemoryError` inside
private-PGM at cell 59, and once to a session teardown at cell 64. Both times the entire run —
hours of compute — was discarded, because results were only written at the end.

A cell is expensive and independent, so each one is written the moment it completes and a
restart skips whatever is already on disk. A teardown now costs at most the single cell in
flight.

TWO PROPERTIES THAT MATTER MORE THAN THEY LOOK:

  * **Atomic writes.** A cell file is written to a temporary path and then `os.replace`d, which
    is atomic on POSIX and on Windows for same-volume renames. Writing in place would leave a
    half-written JSON if the process died mid-write, and the next run would either crash
    parsing it or — far worse — silently treat a truncated cell as complete.

  * **Config hashing.** A cached cell is only reused when the configuration that produced it
    matches the configuration being requested. Without that, changing the epsilon grid or the
    canary count would silently re-use results computed under the old settings, which is a
    quiet way to publish numbers that never came from the code that claims them.
"""

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

CHECKPOINT_VERSION = 1


def config_hash(config: Dict[str, Any]) -> str:
    """Stable hash of a cell's configuration.

    Sorted keys and a fixed separator, so the same configuration always hashes the same way
    regardless of dict ordering. Floats are formatted rather than repr'd so 1.0 and 1 agree.
    """
    def norm(v):
        # bool before int: bool IS an int in Python, and True would otherwise hash as "1",
        # colliding with the integer 1.
        if isinstance(v, bool):
            return f"bool:{v}"
        # Ints and floats go through the SAME formatting. Formatting only floats made
        # eps=1.0 and eps=1 hash differently, which would silently invalidate good cache
        # every time a grid was written with integer epsilons.
        if isinstance(v, (int, float)):
            return f"{float(v):.10g}"
        if isinstance(v, (list, tuple)):
            return [norm(x) for x in v]
        if isinstance(v, dict):
            return {k: norm(v[k]) for k in sorted(v)}
        return v

    payload = json.dumps(norm(config), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass
class CellRecord:
    """One completed grid cell."""

    index: int
    config: Dict[str, Any]
    config_hash: str
    metrics: Dict[str, float]
    completed: bool = True
    version: int = CHECKPOINT_VERSION

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "config": self.config,
            "config_hash": self.config_hash,
            "metrics": self.metrics,
            "completed": self.completed,
            "version": self.version,
        }


class GridCheckpoint:
    """Reads and writes per-cell results under a directory."""

    def __init__(self, directory: Path):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, index: int) -> Path:
        return self.dir / f"cell_{index:04d}.json"

    # ------------------------------------------------------------------ read

    def load(self, index: int, expected_hash: str) -> Optional[Dict[str, float]]:
        """Returns a cell's metrics if it completed under THIS configuration, else None.

        A mismatched hash, a missing `completed` flag, or unparseable JSON all return None —
        the cell is simply recomputed. Silently trusting a stale or truncated file is the one
        outcome this must never produce.
        """
        path = self.path_for(index)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        if not data.get("completed"):
            return None
        if data.get("config_hash") != expected_hash:
            return None
        if data.get("version") != CHECKPOINT_VERSION:
            return None

        metrics = data.get("metrics")
        return metrics if isinstance(metrics, dict) else None

    def completed_indices(self) -> List[int]:
        out = []
        for p in sorted(self.dir.glob("cell_*.json")):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                if d.get("completed"):
                    out.append(int(d["index"]))
            except Exception:
                continue
        return out

    # ------------------------------------------------------------------ write

    def save(self, record: CellRecord) -> Path:
        """Writes a cell atomically: temp file in the same directory, then `os.replace`.

        Same directory matters — `os.replace` is only atomic within a filesystem, and a temp
        file in the system temp dir may be on another volume.
        """
        path = self.path_for(record.index)
        fd, tmp = tempfile.mkstemp(dir=str(self.dir), prefix=".tmp_cell_", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(record.to_dict(), f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())   # the rename is atomic; the CONTENTS must be on disk first
            os.replace(tmp, path)
        except BaseException:
            # Never leave a stray temp file that a later glob might pick up.
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        return path


def run_with_checkpoints(
    cells: List[Dict[str, Any]],
    compute: Callable[[Dict[str, Any]], Dict[str, float]],
    directory: Path,
    progress: Optional[Callable[[str], None]] = None,
) -> List[Dict[str, float]]:
    """Runs `compute` over `cells`, skipping any already completed under the same config.

    Returns metrics in cell order. Raises if any cell fails, WITHOUT aggregating — a partial
    grid must never be mistaken for a complete one, which is precisely how the reduced 3-seed
    run ended up sitting in `results/h1_all_families.json` while a 5-seed run was believed to
    be committed.
    """
    ckpt = GridCheckpoint(directory)
    out: List[Dict[str, float]] = []
    reused = 0

    for i, cfg in enumerate(cells):
        h = config_hash(cfg)
        cached = ckpt.load(i, h)
        if cached is not None:
            reused += 1
            if progress:
                progress(f"  [{i + 1}/{len(cells)}] cached  {_label(cfg)}")
            out.append(cached)
            continue

        if progress:
            progress(f"  [{i + 1}/{len(cells)}] running {_label(cfg)}")
        metrics = compute(cfg)
        ckpt.save(CellRecord(index=i, config=cfg, config_hash=h, metrics=metrics))
        out.append(metrics)

    if progress and reused:
        progress(f"  resumed {reused} of {len(cells)} cells from checkpoints")
    return out


def _label(cfg: Dict[str, Any]) -> str:
    parts = [f"{k}={cfg[k]}" for k in ("mechanism", "target_eps", "seed") if k in cfg]
    return "  ".join(parts) if parts else str(cfg)

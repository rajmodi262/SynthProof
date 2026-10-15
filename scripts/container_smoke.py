"""Drives a running SynthProof service end to end: health, one real release, ledger verification.

Used by CI against the built Docker image, and again after the container is replaced on the same
volume, to prove an upgrade keeps the signed ledger. Standard library only, so it runs on a bare
runner without installing the package.

    python scripts/container_smoke.py --url http://127.0.0.1:8000
    python scripts/container_smoke.py --url ... --no-run --expect-entries 1   # after a restart

Exit status is non-zero on any failure, with the reason printed.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

REQUIRED_MECHANISMS = {"independent", "pairwise", "aim", "mst"}


def _req(url: str, key: str, body: dict | None = None, timeout: float = 30.0):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["X-API-Key"] = key
    if not url.startswith(("http://", "https://")):
        raise SystemExit(f"FAIL: only http(s) service URLs are accepted, got {url!r}")
    data = json.dumps(body).encode() if body is not None else None
    # The scheme is checked above, so file:// and custom schemes cannot reach urlopen.
    return urllib.request.urlopen(  # noqa: S310  # nosec B310
        urllib.request.Request(url, data=data, headers=headers), timeout=timeout
    )


def wait_healthy(base: str, deadline_s: float) -> dict:
    end = time.time() + deadline_s
    last = ""
    while time.time() < end:
        try:
            with _req(f"{base}/api/health", "") as r:
                return json.load(r)
        except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            last = str(exc)
            time.sleep(2)
    raise SystemExit(f"FAIL: service never became healthy at {base}: {last}")


def run_release(base: str, key: str, mechanism: str) -> dict:
    body = {"dataset": "toy", "mechanism": mechanism, "target_eps": 1.0, "rows": 300, "seed": 7}
    event, done = None, None
    with _req(f"{base}/api/run", key, body, timeout=600) as r:
        for raw in r:
            line = raw.decode("utf-8").rstrip("\n")
            if line.startswith("event: "):
                event = line[7:]
            elif line.startswith("data: ") and event in ("done", "error"):
                payload = json.loads(line[6:])
                if event == "error":
                    raise SystemExit(f"FAIL: /api/run ({mechanism}) streamed an error: {payload}")
                done = payload
    if done is None:
        raise SystemExit(f"FAIL: /api/run ({mechanism}) ended without a 'done' event")
    sheet = done.get("sheet") or {}
    if not sheet.get("signature"):
        raise SystemExit(f"FAIL: the {mechanism} release carries no signed sheet")
    return done


def ledger(base: str, key: str) -> dict:
    with _req(f"{base}/api/ledger", key) as r:
        return json.load(r)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--api-key", default="")
    ap.add_argument("--wait", type=float, default=120.0, help="seconds to wait for health")
    ap.add_argument("--no-run", action="store_true", help="only check health and the ledger")
    ap.add_argument("--mechanisms", default="pairwise,aim", help="releases to run, in order")
    ap.add_argument("--expect-entries", type=int, default=None, help="exact ledger entry count")
    args = ap.parse_args()
    base = args.url.rstrip("/")

    health = wait_healthy(base, args.wait)
    missing = REQUIRED_MECHANISMS - set(health.get("mechanisms_available", []))
    if missing:
        raise SystemExit(f"FAIL: image is missing mechanisms {sorted(missing)}: {health}")
    if not health.get("ledger_verified"):
        raise SystemExit(f"FAIL: ledger does not verify at startup: {health}")
    print(f"health ok: auth={health['auth']} mechanisms={health['mechanisms_available']}")

    if not args.no_run:
        for mech in [m for m in args.mechanisms.split(",") if m]:
            t0 = time.time()
            done = run_release(base, args.api_key, mech)
            eps = done["sheet"].get("total_proved_eps")
            print(f"release ok: {mech} proved eps={eps} ({time.time() - t0:.0f}s)")

    led = ledger(base, args.api_key)
    if not led["verified"]:
        raise SystemExit(f"FAIL: ledger chain does not verify: head={led['head']}")
    if args.expect_entries is not None and led["count"] != args.expect_entries:
        raise SystemExit(
            f"FAIL: expected {args.expect_entries} ledger entries, found {led['count']}"
        )
    print(f"ledger ok: {led['count']} entries, verified, head={led['head'][:16]}")


if __name__ == "__main__":
    sys.exit(main())

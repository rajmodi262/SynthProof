"""Two defects found while splitting `_run_stream` (2026-10-16), pinned so they stay fixed."""

import json

from fastapi.testclient import TestClient

from synthproof.api.main import app
from synthproof.api.routes import run as run_routes

client = TestClient(app)


def _events(text):
    out = []
    for frame in text.split("\n\n"):
        ev, data = None, []
        for line in frame.split("\n"):
            if line.startswith("event: "):
                ev = line[7:]
            elif line.startswith("data: "):
                data.append(line[6:])
        if ev and data:
            out.append((ev, json.loads("\n".join(data))))
    return out


def _run():
    body = {"dataset": "toy", "mechanism": "independent", "target_eps": 1.0, "rows": 300, "seed": 1}
    return _events(client.post("/api/run", json=body).text)


def test_the_ledger_note_tells_the_truth_about_durability():
    """It used to say the key is never persisted -- false for a file-backed ledger."""

    class Entry:
        entry_id, prev_hash, signature = "e", "p", "s"

        def compute_hash(self):
            return "h"

    class Ctx:
        ledger = client.app.state.ctx.ledger

        def __init__(self, durable):
            self.ledger_durable = durable

    durable = run_routes._ledger_frame(Ctx(True), Entry())
    assert durable["signed"] is True and "persists" in durable["signature_note"]
    demo = run_routes._ledger_frame(Ctx(False), Entry())
    assert demo["signed"] is False and "IN-MEMORY" in demo["signature_note"]


def test_a_signing_failure_is_an_error_not_an_unsigned_sheet(monkeypatch):
    """Signing sat in `except Exception: pass`, so a failure shipped a sheet with no signature."""

    class BrokenKey:
        def sign(self, _payload):
            raise RuntimeError("signing key unavailable")

    client.post("/api/ledger/reset")
    # The ledger of the app this client serves: after another test reloads `state`, the
    # module-level default is a different instance.
    led = client.app.state.ctx.ledger
    real_key = led._private_key
    events = None
    try:
        # Break signing only after the ledger entry is appended (append also signs).
        real_append = led.append

        def append_then_break(entry):
            out = real_append(entry)
            led._private_key = BrokenKey()
            return out

        monkeypatch.setattr(led, "append", append_then_break)
        events = _run()
    finally:
        led._private_key = real_key
        client.post("/api/ledger/reset")
    kinds = [e for e, _ in events]
    assert "done" not in kinds
    assert any(
        e == "error" and "signing key unavailable" in p.get("message", "") for e, p in events
    )

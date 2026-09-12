"""HTTP routes, grouped by what they are for.

Split out of a 1,225-line `main.py` on 2026-09-13. Shared module state -- the ledger, the
API key, the upload cache -- lives in `synthproof.api.state`, so a router imports what it
needs rather than reaching back into the application object.
"""

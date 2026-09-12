"""FastAPI service backing the SynthProof console.

Design rule for this module, inherited from the project's standing rules: **the API returns
only what the pipeline measured.** Where something is not implemented, the response says so
explicitly (see `/api/mechanisms` and the `attacks` block of a run result) rather than
omitting it and letting the console imply a pass. A previous version of the console displayed
four hardcoded "PASSED" attack verdicts, including one for an attack that does not exist.

The run endpoint drives `frontier.experiment.run_cell` through its `on_stage` callback rather
than reimplementing the pipeline. That is deliberate: three parallel pipelines already drifted
apart in this repository, and a fourth living in the web layer would be the worst of them.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from synthproof.api.routes import artifacts as artifacts_routes
from synthproof.api.routes import datasets as datasets_routes
from synthproof.api.routes import ledger as ledger_routes
from synthproof.api.routes import run as run_routes
from synthproof.api.state import (  # noqa: F401  (re-exported for tests)
    _DEMO_DATASETS,
    _MAX_UPLOAD_BYTES,
    _MAX_UPLOAD_ROWS,
    _MAX_UPLOADS,
    _UPLOAD_CHUNK,
    _UPLOADS,
    API_KEY,
    AUTH_ENABLED,
    DEMO_MODE,
    GLOBAL_LEDGER,
    _init_demo_datasets,
    _ledger_conn,
    _register_upload,
    _require_demo_ledger,
    require_api_key,
)

app = FastAPI(
    title="SynthProof API",
    description="Synthetic data that ships with its proof — console backend.",
    version="0.2.0",
)

# Wildcard origins with credentials is rejected by browsers and unsafe besides. Credentials
# stay off: this service authenticates with a header, not a cookie, so there is nothing for a
# browser to attach automatically and nothing for CSRF to abuse.
#
# The wildcard is narrowed once a key is configured. SYNTHPROOF_CORS_ORIGINS takes a
# comma-separated list; it defaults to the dev console's origin rather than "*", because a
# deployment with a key should not also be reachable from any page on the internet.
_CORS = os.environ.get("SYNTHPROOF_CORS_ORIGINS", "").strip()
if _CORS:
    _ALLOWED_ORIGINS = [o.strip() for o in _CORS.split(",") if o.strip()]
elif os.environ.get("SYNTHPROOF_API_KEY", "").strip():
    _ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
else:
    _ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


app.include_router(run_routes.router)
app.include_router(datasets_routes.router)
app.include_router(ledger_routes.router)
app.include_router(artifacts_routes.router)

# --------------------------------------------------------------------------- static

_here = os.path.dirname(__file__)

# `static/` holds the hand-written legacy console, which is a tracked source file.
# `console/` holds the built React console and is a generated directory (gitignored).
static_dir = os.path.join(_here, "static")
console_dir = os.path.join(_here, "console")
os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Vite emits absolute `/assets/...` URLs so the dev server and a production build use
# identical paths. Mounting the built asset directory at that same path lets this service
# serve the console unchanged, rather than forcing a `base` override that could only ever be
# correct in one of the two environments.
_assets_dir = os.path.join(console_dir, "assets")
if os.path.isdir(_assets_dir):
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")


@app.get("/", response_class=HTMLResponse)
def serve_index():
    """Serves the built React console, falling back to a pointer at the dev server."""
    built = os.path.join(console_dir, "index.html")
    if os.path.exists(built):
        with open(built, "r", encoding="utf-8") as f:
            return f.read()
    return (
        "<!doctype html><meta charset='utf-8'>"
        "<title>SynthProof API</title>"
        "<style>body{font:16px/1.6 system-ui;max-width:44rem;margin:4rem auto;padding:0 1.5rem}"
        "code{background:#eee;padding:.15em .4em;border-radius:3px}</style>"
        "<h1>SynthProof API</h1>"
        "<p>The API is running, but the console has not been built.</p>"
        "<p>Dev server: <code>cd web &amp;&amp; npm install &amp;&amp; npm run dev</code> "
        "then open <a href='http://localhost:5173'>localhost:5173</a>.</p>"
        "<p>Or build it into this service: <code>cd web &amp;&amp; npm run build</code>, "
        "then reload this page.</p>"
        "<p>API docs: <a href='/docs'>/docs</a> · "
        "Legacy console: <a href='/static/index.html'>/static/index.html</a></p>"
    )

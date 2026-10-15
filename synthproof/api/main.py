"""FastAPI service backing the SynthProof console.

Design rule for this module, inherited from the project's standing rules: **the API returns
only what the pipeline measured.** Where something is not implemented, the response says so
explicitly (see `/api/mechanisms` and the `attacks` block of a run result) rather than
omitting it and letting the console imply a pass. A previous version of the console displayed
four hardcoded "PASSED" attack verdicts, including one for an attack that does not exist.

The run endpoint drives `frontier.experiment.run_cell` through its `on_stage` callback rather
than reimplementing the pipeline. That is deliberate: three parallel pipelines already drifted
apart in this repository, and a fourth living in the web layer would be the worst of them.

APP FACTORY (2026-10-16). `create_app(ctx)` builds an application around an explicit
`AppContext` (`api/context.py`); routes receive it by dependency injection. Importing this
module does no work: `app` -- the default instance `uvicorn synthproof.api.main:app` serves -- is
created on first access, from the environment.
"""

import math
import os
from typing import List, Mapping, Optional

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from synthproof import __version__
from synthproof.api.context import AppContext, build_context

_here = os.path.dirname(__file__)
# `static/` holds the hand-written legacy console, which is a tracked source file.
# `console/` holds the built React console and is a generated directory (gitignored).
static_dir = os.path.join(_here, "static")
console_dir = os.path.join(_here, "console")


def allowed_origins(env: Mapping[str, str]) -> List[str]:
    """CORS origins.

    Wildcard origins with credentials is rejected by browsers and unsafe besides. Credentials stay
    off: this service authenticates with a header, not a cookie, so there is nothing for a browser
    to attach automatically and nothing for CSRF to abuse. The wildcard is narrowed once a key is
    configured: SYNTHPROOF_CORS_ORIGINS takes a comma-separated list and otherwise defaults to the
    dev console's origin, because a deployment with a key should not also be reachable from any
    page on the internet.
    """
    cors = env.get("SYNTHPROOF_CORS_ORIGINS", "").strip()
    if cors:
        return [o.strip() for o in cors.split(",") if o.strip()]
    if env.get("SYNTHPROOF_API_KEY", "").strip() or env.get("SYNTHPROOF_API_KEYS", "").strip():
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    return ["*"]


def _finite(value):
    """Replaces NaN/Infinity (which JSON cannot carry) with their names, recursively."""
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    if isinstance(value, dict):
        return {k: _finite(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_finite(v) for v in value]
    return value


async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """A 422 that can always be serialised.

    FOUND BY FUZZING 2026-10-16 (tests/test_fuzz.py). Python's JSON parser accepts the tokens
    `Infinity` and `NaN`, validation then rejects the value correctly -- and FastAPI's default
    handler echoed the offending input back, failed to JSON-encode `inf`, and answered 500. The
    request was refused either way; the status code said the server broke. Now it says 422.
    """
    return JSONResponse(
        status_code=422, content={"detail": _finite(jsonable_encoder(exc.errors()))}
    )


def _serve_index():
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


def create_app(
    ctx: Optional[AppContext] = None, env: Optional[Mapping[str, str]] = None
) -> FastAPI:
    """An application around `ctx` (built from `env`, default os.environ, when not given)."""
    from synthproof.api.routes import artifacts, datasets, ledger, run

    env = os.environ if env is None else env
    application = FastAPI(
        title="SynthProof API",
        description="Synthetic data that ships with its proof — console backend.",
        version=__version__,  # one source; this literal had drifted to 0.2.0
    )
    application.state.ctx = ctx if ctx is not None else build_context(env)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins(env),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    application.add_exception_handler(RequestValidationError, _validation_error)  # type: ignore[arg-type]
    for module in (run, datasets, ledger, artifacts):
        application.include_router(module.router)

    os.makedirs(static_dir, exist_ok=True)
    application.mount("/static", StaticFiles(directory=static_dir), name="static")
    # Vite emits absolute `/assets/...` URLs so the dev server and a production build use
    # identical paths. Mounting the built asset directory at that same path lets this service
    # serve the console unchanged.
    assets_dir = os.path.join(console_dir, "assets")
    if os.path.isdir(assets_dir):
        application.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    application.get("/", response_class=HTMLResponse)(_serve_index)
    application.openapi = lambda: _openapi_with_stream_frames(application)  # type: ignore[method-assign]
    return application


def _openapi_with_stream_frames(application: FastAPI) -> dict:
    """The OpenAPI document, plus the run stream's frame schemas.

    FastAPI cannot infer the body of a server-sent-event stream, so `/api/run` would document
    nothing the console actually consumes. The start and done frames are added as named
    components and referenced from the endpoint, so the console's generated types cover them.
    """
    if application.openapi_schema:
        return application.openapi_schema
    from fastapi.openapi.utils import get_openapi

    from synthproof.api.schemas import STREAM_FRAMES

    spec = get_openapi(
        title=application.title,
        version=application.version,
        description=application.description,
        routes=application.routes,
    )
    components = spec.setdefault("components", {}).setdefault("schemas", {})
    for name, model in STREAM_FRAMES.items():
        schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
        components.update(schema.pop("$defs", {}))
        components[name] = schema
    run_op = spec["paths"]["/api/run"]["post"]
    run_op["responses"]["200"]["content"] = {
        "text/event-stream": {
            "schema": {
                "description": "Server-sent events: one `start`, then `stage` events, then "
                "`done` (or `error`).",
                "oneOf": [{"$ref": f"#/components/schemas/{n}"} for n in STREAM_FRAMES],
            }
        }
    }
    application.openapi_schema = spec
    return spec


# A reload (`importlib.reload`) re-executes this module in its old namespace; drop any default
# instance built under the previous configuration so the next access rebuilds it.
globals().pop("app", None)


def __getattr__(name: str):
    """The default `app`, built on first access; and compatibility names for older callers."""
    if name == "app":
        from synthproof.api import state

        instance = create_app(state.default_context())
        globals()["app"] = instance
        return instance
    if name == "_ALLOWED_ORIGINS":
        return allowed_origins(os.environ)
    from synthproof.api import state

    try:
        return getattr(state, name)
    except AttributeError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None

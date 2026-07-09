from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from src import config
from src.api.middleware.auth_middleware import AuthMiddleware
from src.api.router import router as api_router
from src.bootstrap_admin import seed_admin_from_env
from src.db import make_engine, make_session_factory
from src.migrations.runner import run_migrations
from src.schema.cameras import seed_unknown_camera


def create_app(*, database_path: str | None = None) -> FastAPI:
    db_path = database_path or config.DATABASE_PATH

    # StaticFiles requires the directory to exist at mount time, so this
    # can't be deferred to lifespan (which only runs once the app actually
    # starts serving, e.g. under uvicorn or a TestClient context).
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(config.ASSETS_DIR).mkdir(parents=True, exist_ok=True)
    Path(config.IMPORT_DIR).mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        run_migrations(db_path)

        engine = make_engine(db_path)
        seed_admin_from_env(engine)
        seed_unknown_camera(engine)
        app.state.engine = engine
        app.state.session_factory = make_session_factory(engine)

        yield

        engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(AuthMiddleware)
    # Added after AuthMiddleware so it ends up outermost (Starlette wraps in
    # reverse add order) and can short-circuit CORS preflight OPTIONS
    # requests before they ever reach the auth check.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[config.FRONTEND_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # Content-Disposition isn't in the browser's default cross-origin header
        # exposure safelist; without this, JS can't read a download's server-supplied
        # filename (see the CSV export button in the dataset admin panel).
        expose_headers=["Content-Disposition"],
    )
    app.mount("/assets", StaticFiles(directory=config.ASSETS_DIR), name="assets")
    app.include_router(api_router, prefix="/api")

    # Mounted last so it doesn't shadow /assets or /api: Starlette matches
    # routes in registration order, and Mount("/") would otherwise catch
    # every path. Only mounted if present, since an unbuilt frontend (fresh
    # checkout, backend-only dev, pytest) is a normal state, not an error.
    frontend_dist = Path(config.FRONTEND_DIST_DIR)
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(create_app(), host="0.0.0.0", port=8000)

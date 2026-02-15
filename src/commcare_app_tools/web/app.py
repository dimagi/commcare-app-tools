"""FastAPI application for CommCare App Tools web UI."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.cli import router as cli_router
from .api.config import router as config_router


def create_app(dev_mode: bool = False) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        dev_mode: If True, enables CORS for local development (React dev server)

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="CommCare App Tools",
        description="Local web UI for CommCare app testing and debugging",
        version="0.1.0",
    )

    # CORS for development (React dev server on different port)
    if dev_mode:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # API routes
    app.include_router(config_router, prefix="/api")
    app.include_router(cli_router, prefix="/api")

    # Static files (built React app)
    static_dir = Path(__file__).parent / "frontend" / "dist"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app


# Default app instance for uvicorn
app = create_app(dev_mode=True)

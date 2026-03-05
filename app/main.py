"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .config import get_settings
from .dashboard import DASHBOARD_HTML
from .database import Base
from .database import engine as db_engine
from .engine import PruneEngine
from .routers import audit, prune


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and load profiles on startup; dispose DB on shutdown."""
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.engine = PruneEngine()
    yield
    await db_engine.dispose()


settings = get_settings()

app = FastAPI(
    title="ContextGate",
    description=(
        "Generic LLM context-pruning middleware. "
        "Strip irrelevant metadata, mask sensitive fields, and return "
        "a minimal token-optimized payload for any LLM."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prune.router)
app.include_router(audit.router)


@app.get("/health", tags=["Health"])
async def health() -> dict:
    """Liveness probe for container orchestrators."""
    return {"status": "ok", "service": "ContextGate"}


@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard():
    """Real-time pruning dashboard."""
    return DASHBOARD_HTML

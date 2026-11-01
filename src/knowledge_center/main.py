from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from knowledge_center import articles, auth, documents
from knowledge_center.db import create_tables, pool

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Runs once on startup (before `yield`) and once on shutdown (after it).
    pool.open()
    create_tables()
    yield
    pool.close()


app = FastAPI(title="Knowledge Center", lifespan=lifespan)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


# Every API route lives under /api, so the frontend can own every other URL.
api = APIRouter(prefix="/api")
api.include_router(auth.router)
api.include_router(articles.router)
api.include_router(documents.router)
app.include_router(api)

# Serve the frontend (index.html, app.js, styles.css) at "/".
# Mounted last, so /api and /health routes are matched first.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

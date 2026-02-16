"""Direct Lending Graph Visualization API."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from db import lifespan
from routes import entities, graph, nodes, stats

app = FastAPI(title="Direct Lending Graph", lifespan=lifespan)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
async def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/entity/{label}/{name}", include_in_schema=False)
async def entity_page(label: str, name: str) -> FileResponse:
    return FileResponse(STATIC_DIR / "entity.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(entities.router)
app.include_router(graph.router)
app.include_router(nodes.router)
app.include_router(stats.router)

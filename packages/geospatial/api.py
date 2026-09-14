# Copyright (c) Ultrone Contributors. All rights reserved.
"""ULTRONE geo API: FastAPI surface for the Global Eye globe (``apps/globe``).

Exposes :class:`packages.geospatial.service.GeoService` snapshots over HTTP
plus a live WebSocket stream. Two ways to serve it:

- Standalone dev server (used by ``apps/globe`` via Vite proxy)::

      python -m packages.geospatial.api   # 127.0.0.1:8001

- Mounted into the main ULTRONE API (production)::

      from packages.geospatial.api import router as geo_router
      app.include_router(geo_router)

All routes live under ``/api/ultrone``.
"""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/ultrone", tags=["ultrone-geo"])

_service = None


def get_service():
    """Process-wide geo service singleton (dev-friendly; use DI in prod)."""
    global _service
    if _service is None:
        from packages.geospatial.service import GeoService

        _service = GeoService()
    return _service


class SimCommand(BaseModel):
    steps: int = Field(default=1, ge=1, le=100)


@router.get("/health")
async def health() -> JSONResponse:
    svc = get_service()
    snap = svc.snapshot(advance=False)
    return JSONResponse(
        {
            "status": "ok",
            "service": "ultrone-geo",
            "entities": snap["count"],
            "tracks": len(snap["tracks"]),
            "sim_attached": svc.sim is not None,
            "time": time.time(),
        }
    )


@router.get("/entities")
async def entities() -> JSONResponse:
    return JSONResponse(get_service().snapshot())


@router.get("/tracks")
async def tracks(history: int = Query(default=20, ge=1, le=200)) -> JSONResponse:
    svc = get_service()
    snap = svc.snapshot()
    trimmed = {eid: pts[-history:] for eid, pts in snap["tracks"].items()}
    return JSONResponse(
        {
            "generated_at": snap["generated_at"],
            "tracks": trimmed,
            "theater": snap["theater"],
        }
    )


@router.post("/sim/reset")
async def sim_reset() -> JSONResponse:
    svc = get_service()
    svc.attach_sim()
    return JSONResponse({"status": "reset", "sim_attached": True})


@router.post("/sim/step")
async def sim_step(cmd: SimCommand) -> JSONResponse:
    result = get_service().step_sim(cmd.steps)
    return JSONResponse({"status": "stepped", **result})


@router.websocket("/stream")
async def stream(websocket: WebSocket, hz: float = 1.0) -> None:
    await websocket.accept()
    hz = min(max(hz, 0.2), 5.0)
    svc = get_service()
    try:
        while True:
            await websocket.send_json({"type": "snapshot", **svc.snapshot()})
            await asyncio.sleep(1.0 / hz)
    except WebSocketDisconnect:
        pass


def create_geo_app():
    """Standalone FastAPI app serving the geo router (dev + microservice)."""
    from fastapi import FastAPI

    app = FastAPI(title="ULTRONE Geo", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.get("/healthz")
    async def healthz() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return app


def main() -> None:  # pragma: no cover - manual dev entry point
    import os
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent
    while not (root / "pyproject.toml").is_file() and root != root.parent:
        root = root.parent
    sys.path.insert(0, str(root))
    from _ultrone_paths import ensure_on_syspath

    ensure_on_syspath(root)

    import uvicorn

    host = os.environ.get("ULTRONE_GEO_HOST", "127.0.0.1")
    port = int(os.environ.get("ULTRONE_GEO_PORT", "8001"))
    uvicorn.run(create_geo_app(), host=host, port=port)


if __name__ == "__main__":  # pragma: no cover
    main()

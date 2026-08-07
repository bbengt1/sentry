"""Preview routes: status JSON, MJPEG stream, root HTML (UI-01).

Handlers only call bus.get_latest / capture_loop.build_status.
They never open cameras or call source.read — encode from bus only.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import cv2
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

BOUNDARY = "frame"
JPEG_QUALITY = 80
MJPEG_SLEEP_S = 0.033  # ~30 FPS UI path; independent of capture FPS

# Packaged static Live Preview page (ui/static next to api/ package tree).
_INDEX_HTML = (
    Path(__file__).resolve().parents[1] / "ui" / "static" / "index.html"
)

router = APIRouter()


def _bus(request: Request) -> Any:
    return request.app.state.bus


def _capture_loop(request: Request) -> Any:
    return request.app.state.capture_loop


def _bind(request: Request) -> str:
    return str(request.app.state.bind)


@router.get("/api/status")
async def api_status(request: Request) -> dict[str, Any]:
    """Return capture status + bus metrics as JSON."""
    loop = _capture_loop(request)
    snapshot = loop.build_status(bind=_bind(request))
    return snapshot.model_dump()


async def _mjpeg_generator(
    bus: Any,
    jpeg_quality: int = JPEG_QUALITY,
) -> AsyncIterator[bytes]:
    """Yield multipart JPEG parts from the keep-latest bus slot."""
    boundary = BOUNDARY.encode()
    while True:
        item = bus.get_latest()
        if item is not None:
            ok, buf = cv2.imencode(
                ".jpg",
                item.image_bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality],
            )
            if ok:
                chunk = buf.tobytes()
                yield (
                    b"--"
                    + boundary
                    + b"\r\n"
                    + b"Content-Type: image/jpeg\r\n\r\n"
                    + chunk
                    + b"\r\n"
                )
        await asyncio.sleep(MJPEG_SLEEP_S)


@router.get("/preview/mjpeg")
async def preview_mjpeg(request: Request) -> StreamingResponse:
    """MJPEG multipart stream of the latest bus frame (subscriber only)."""
    bus = _bus(request)
    return StreamingResponse(
        _mjpeg_generator(bus),
        media_type=f"multipart/x-mixed-replace; boundary={BOUNDARY}",
    )


@router.get("/", response_model=None)
async def root_preview() -> FileResponse | HTMLResponse:
    """Serve the packaged Live Preview page at GET /."""
    if _INDEX_HTML.is_file():
        return FileResponse(
            path=_INDEX_HTML,
            media_type="text/html; charset=utf-8",
        )
    # Fallback if package data is missing (should not happen in wheels).
    return HTMLResponse(
        content=(
            "<!DOCTYPE html><html><head>"
            "<title>Sentry AI — Live Preview</title></head>"
            "<body><h1>Sentry AI — Live Preview</h1>"
            "<p>Live Preview page is not packaged.</p>"
            '<img src="/preview/mjpeg" alt="Live camera preview" />'
            "</body></html>"
        ),
        status_code=500,
    )

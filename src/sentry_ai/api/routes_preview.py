"""Preview routes: status JSON, MJPEG stream, root HTML (UI-01).

Handlers only call bus.get_latest / capture_loop.build_status / store snapshots.
They never open cameras or call source.read — encode from bus only.
Detection, depth, and free-space overlays are drawn from PerceptionStore
(same truth as /v1 snapshot — UI-06). Never invent free-space from raw depth.

MJPEG generators exit on client disconnect, app shutdown_flag, or cancel so
``sentry serve`` Ctrl+C does not hang on open browser streams.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import cv2
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

from sentry_ai.api.assemble import DEFAULT_TTL_MS
from sentry_ai.models.depth.colormap import blend_depth
from sentry_ai.models.detection.overlay import draw_detections
from sentry_ai.spatial.overlay import draw_free_space

BOUNDARY = "frame"
JPEG_QUALITY = 80
MJPEG_SLEEP_S = 0.033  # ~30 FPS UI path; independent of capture FPS
MJPEG_POLL_S = 0.01  # interruptible sleep slice for fast Ctrl+C
DEPTH_BLEND_ALPHA = 0.45

# Packaged static Live Preview page (ui/static next to api/ package tree).
_INDEX_HTML = (
    Path(__file__).resolve().parents[1] / "ui" / "static" / "index.html"
)

router = APIRouter()


class QuietStreamingResponse(StreamingResponse):
    """StreamingResponse that treats cancel-on-shutdown as normal exit.

    Uvicorn cancels open MJPEG tasks after graceful timeout; without this,
    Starlette logs a full ERROR traceback for asyncio.CancelledError.
    """

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        try:
            await super().__call__(scope, receive, send)
        except asyncio.CancelledError:
            return


def _bus(request: Request) -> Any:
    return request.app.state.bus


def _capture_loop(request: Request) -> Any:
    return request.app.state.capture_loop


def _bind(request: Request) -> str:
    return str(request.app.state.bind)


def _perception_store(request: Request) -> Any:
    return getattr(request.app.state, "perception_store", None)


def _detection_worker(request: Request) -> Any:
    return getattr(request.app.state, "detection_worker", None)


@router.get("/api/status")
async def api_status(request: Request) -> dict[str, Any]:
    """Return capture status + bus metrics + optional det/depth/free_space JSON."""
    loop = _capture_loop(request)
    snapshot = loop.build_status(bind=_bind(request))
    data = snapshot.model_dump()

    store = _perception_store(request)
    worker = _detection_worker(request)
    if store is not None:
        product = store.snapshot()
        metrics = store.metrics_snapshot()
        if product is not None:
            data["detections_count"] = len(product.detections)
            data["det_latency_ms"] = product.latency_ms
            data["det_frame_id"] = product.frame_id
            if product.conf is not None:
                data["det_conf"] = product.conf
        data["det_fps"] = metrics.det_fps
        if data.get("det_latency_ms") is None and metrics.last_latency_ms is not None:
            data["det_latency_ms"] = metrics.last_latency_ms

        # Depth telemetry from the same PerceptionStore (DEPTH-04 / Pattern 7).
        depth_product = store.snapshot_depth()
        data["depth_fps"] = metrics.depth_fps
        if depth_product is not None:
            data["depth_latency_ms"] = depth_product.latency_ms
            data["depth_frame_id"] = depth_product.frame_id
            # kind may be DepthKind enum — coerce to string for JSON.
            kind = depth_product.kind
            data["depth_kind"] = kind.value if hasattr(kind, "value") else str(kind)
            if depth_product.unit is not None:
                # Omit for relative (honesty): only set when non-null.
                data["depth_unit"] = depth_product.unit
            if depth_product.error is not None:
                data["depth_error"] = depth_product.error
        elif metrics.last_depth_latency_ms is not None:
            data["depth_latency_ms"] = metrics.last_depth_latency_ms

        # Free-space telemetry from the same store (SPACE-03 / UI-02 / UI-06).
        free_product = store.snapshot_free_space()
        data["free_space_fps"] = metrics.free_space_fps
        if free_product is not None:
            data["free_space_latency_ms"] = free_product.latency_ms
            data["free_space_frame_id"] = free_product.frame_id
            data["obstacle_count"] = free_product.obstacle_count
            age_ms = max(0.0, (time.time() - free_product.t_capture) * 1000.0)
            data["free_space_age_ms"] = age_ms
            data["free_space_stale"] = age_ms > DEFAULT_TTL_MS["free_space"]
            if free_product.error is not None:
                data["free_space_error"] = free_product.error
        elif metrics.last_free_space_latency_ms is not None:
            data["free_space_latency_ms"] = metrics.last_free_space_latency_ms

    if worker is not None and data.get("det_conf") is None:
        try:
            data["det_conf"] = float(worker.get_conf())
        except Exception:  # noqa: BLE001 — status is best-effort
            pass

    # Pipeline stage flags + free-space cuts (UI-03/UI-04/UI-05).
    pipeline_state = getattr(request.app.state, "pipeline_state", None)
    if pipeline_state is not None:
        try:
            pipe = pipeline_state.snapshot()
            data["detection_enabled"] = pipe.get("detection_enabled")
            data["depth_enabled"] = pipe.get("depth_enabled")
            data["free_space_enabled"] = pipe.get("free_space_enabled")
            data["near_cut"] = pipe.get("near_cut")
            data["mid_cut"] = pipe.get("mid_cut")
        except Exception:  # noqa: BLE001 — status is best-effort
            pass
    return data


async def _mjpeg_generator(
    bus: Any,
    store: Any | None = None,
    jpeg_quality: int = JPEG_QUALITY,
    *,
    request: Request | None = None,
    shutdown_flag: threading.Event | None = None,
) -> AsyncIterator[bytes]:
    """Yield multipart JPEG parts from the keep-latest bus slot.

    Draw order (UI-02 / UI-06): depth blend → free-space → detection boxes.
    Free-space is drawn only from store free-space product (never computed
    from raw depth_map here). Temporal skew across products is accepted.
    Never runs inference or Spatial Post.

    Stops when:
    - ``shutdown_flag`` is set (app lifespan / serve Ctrl+C),
    - the HTTP client disconnects (``request.is_disconnected``),
    - or the task is cancelled (uvicorn graceful shutdown).
    """
    boundary = BOUNDARY.encode()

    async def _interruptible_sleep(seconds: float) -> bool:
        """Sleep in slices; return True if shutdown requested mid-sleep."""
        remaining = seconds
        while remaining > 0:
            if shutdown_flag is not None and shutdown_flag.is_set():
                return True
            step = min(MJPEG_POLL_S, remaining)
            await asyncio.sleep(step)
            remaining -= step
        return shutdown_flag is not None and shutdown_flag.is_set()

    try:
        while True:
            if shutdown_flag is not None and shutdown_flag.is_set():
                break
            if request is not None:
                try:
                    if await request.is_disconnected():
                        break
                except RuntimeError:
                    # Request has no receive channel (unit tests building
                    # Request(scope) without ASGI receive).
                    pass

            item = bus.get_latest()
            if item is not None:
                image = item.image_bgr
                if store is not None:
                    depth_product = store.snapshot_depth()
                    if (
                        depth_product is not None
                        and depth_product.error is None
                        and depth_product.depth_map is not None
                    ):
                        image = blend_depth(
                            image,
                            depth_product.depth_map,
                            alpha=DEPTH_BLEND_ALPHA,
                        )
                    free_product = store.snapshot_free_space()
                    if free_product is not None and free_product.error is None:
                        image = draw_free_space(
                            image,
                            free_mask=free_product.free_mask,
                            occupied_mask=free_product.occupied_mask,
                            obstacles=free_product.obstacles,
                        )
                    product = store.snapshot()
                    if product is not None:
                        image = draw_detections(image, product.detections)
                ok, buf = cv2.imencode(
                    ".jpg",
                    image,
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
            if await _interruptible_sleep(MJPEG_SLEEP_S):
                break
    except asyncio.CancelledError:
        # Normal path when uvicorn cancels streaming tasks on shutdown.
        return


@router.get("/preview/mjpeg")
async def preview_mjpeg(request: Request) -> QuietStreamingResponse:
    """MJPEG multipart stream of the latest bus frame (subscriber only)."""
    bus = _bus(request)
    store = _perception_store(request)
    shutdown_flag = getattr(request.app.state, "shutdown_flag", None)
    return QuietStreamingResponse(
        _mjpeg_generator(
            bus,
            store=store,
            request=request,
            shutdown_flag=shutdown_flag,
        ),
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

"""CR-002: depth loss must invalidate free-space on REST/WS and MJPEG."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import numpy as np
from fastapi.testclient import TestClient

from sentry_ai.api import routes_preview
from sentry_ai.api.app import create_app
from sentry_ai.api.assemble import assemble_perception_frame
from sentry_ai.api.routes_preview import _mjpeg_generator
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.models.depth.loop import DepthLoop
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.frame import Frame
from sentry_ai.sources.synthetic import SyntheticSource
from sentry_ai.spatial.loop import FreeSpaceLoop
from sentry_ai.state.perception_store import PerceptionStore


def _wait_until(
    predicate: Any,
    *,
    timeout: float = 2.0,
    interval: float = 0.01,
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def _depth_map() -> np.ndarray:
    depth = np.full((20, 20), 5.0, dtype=np.float32)
    depth[12:, 6:14] = 0.4
    return depth


def _seed_clear_looking_free_space(
    store: PerceptionStore,
    *,
    t_capture: float,
    frame_id: int = 1,
) -> None:
    """A successful all-far free-space product younger than the 750 ms TTL."""
    store.set_depth(
        frame_id=frame_id,
        camera_id="cam0",
        t_capture=t_capture,
        depth_map=_depth_map(),
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=1.0,
    )
    free = np.full((20, 20), 255, dtype=np.uint8)
    store.set_free_space(
        frame_id=frame_id,
        camera_id="cam0",
        t_capture=t_capture,
        latency_ms=1.0,
        depth_kind=DepthKind.RELATIVE,
        obstacle_count=0,
        obstacles=[],
        bands={"near_frac": 0.0, "mid_frac": 0.0, "far_frac": 1.0},
        free_mask=free,
        occupied_mask=np.zeros((20, 20), dtype=np.uint8),
        error=None,
        units="ordinal",
    )


def _camera_frame() -> ImageFrame:
    meta = Frame(
        frame_id=1,
        camera_id="cam0",
        t_capture=time.time(),
        t_ingest=time.time(),
        width=20,
        height=20,
    )
    return ImageFrame(meta=meta, image_bgr=np.zeros((20, 20, 3), dtype=np.uint8))


def _one_jpeg(bus: FrameBus, store: PerceptionStore) -> bytes:
    async def _pull() -> bytes:
        gen = _mjpeg_generator(bus, store=store)
        try:
            return await gen.__anext__()
        finally:
            await gen.aclose()

    return asyncio.run(_pull())


def test_clear_depth_drops_free_space_before_ttl() -> None:
    """Disabling depth must not leave a fresh complete free-space product."""
    store = PerceptionStore()
    t0 = time.time()
    _seed_clear_looking_free_space(store, t_capture=t0)
    loop = DepthLoop(FrameBus(), object(), store)
    loop.set_enabled(False)
    assert store.snapshot_depth() is None
    assert store.snapshot_free_space() is None

    frame = assemble_perception_frame(store, now=t0 + 0.5)
    assert frame is None or frame.completeness.free_space is False
    if frame is not None:
        assert frame.free_space is None


def test_depth_error_drops_free_space_before_ttl() -> None:
    """A depth error product must not keep the previous clearance complete."""
    store = PerceptionStore()
    t0 = time.time()
    _seed_clear_looking_free_space(store, t_capture=t0)
    store.set_depth(
        frame_id=2,
        camera_id="cam0",
        t_capture=t0 + 0.1,
        depth_map=None,
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=1.0,
        error="depth failed",
    )
    assert store.snapshot_free_space() is None
    frame = assemble_perception_frame(store, now=t0 + 0.5)
    assert frame is not None
    assert frame.completeness.depth is False
    assert frame.completeness.free_space is False
    assert frame.depth is None
    assert frame.free_space is None

    store2 = PerceptionStore()
    _seed_clear_looking_free_space(store2, t_capture=t0)
    store2.set_depth(
        frame_id=3,
        camera_id="cam0",
        t_capture=t0 + 0.1,
        depth_map=None,
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=1.0,
        error=None,
    )
    assert store2.snapshot_free_space() is None


def test_snapshot_and_status_are_not_clear_after_depth_cleared() -> None:
    """REST snapshot, /v1 snapshot, and /api/status share the cleared product."""
    store = PerceptionStore()
    t0 = time.time()
    _seed_clear_looking_free_space(store, t_capture=t0)
    store.clear_depth()
    source = SyntheticSource(camera_id="cam0", fps=0.0)
    bus = FrameBus()
    capture = CaptureLoop(source, bus)
    app = create_app(
        bus=bus,
        capture_loop=capture,
        bind="127.0.0.1:8000",
        perception_store=store,
    )
    with TestClient(app) as client:
        for path in ("/api/snapshot", "/v1/snapshot"):
            resp = client.get(path)
            assert resp.status_code == 404, path
        status = client.get("/api/status")
        assert status.status_code == 200
        data = status.json()
        # Schema keys stay present; a cleared product must not look like a
        # zero-obstacle clearance (obstacle_count 0 with a frame id).
        assert data.get("obstacle_count") is None
        assert data.get("free_space_frame_id") is None
        assert data.get("free_space_error") in (None, "")


def test_free_space_write_after_depth_clear_does_not_resurrect() -> None:
    store = PerceptionStore()
    t0 = time.time()
    _seed_clear_looking_free_space(store, t_capture=t0)
    revision = store.depth_revision()
    store.clear_depth()
    store.set_free_space(
        frame_id=1,
        camera_id="cam0",
        t_capture=t0,
        latency_ms=1.0,
        depth_kind=DepthKind.RELATIVE,
        obstacle_count=0,
        bands={"far_frac": 1.0},
        free_mask=np.full((20, 20), 255, dtype=np.uint8),
        error=None,
        units="ordinal",
        depth_revision=revision,
    )
    assert store.snapshot_free_space() is None


def test_free_space_loop_resets_smoother_when_depth_cleared() -> None:
    store = PerceptionStore()
    loop = FreeSpaceLoop(store)
    try:
        loop.start()
        store.set_depth(
            frame_id=1,
            camera_id="cam0",
            t_capture=1.0,
            depth_map=_depth_map(),
            kind=DepthKind.RELATIVE,
            unit=None,
            latency_ms=1.0,
        )
        assert _wait_until(
            lambda: (snap := store.snapshot_free_space()) is not None
            and snap.frame_id == 1
            and snap.error is None,
        )
        store.set_depth(
            frame_id=2,
            camera_id="cam0",
            t_capture=2.0,
            depth_map=_depth_map(),
            kind=DepthKind.RELATIVE,
            unit=None,
            latency_ms=1.0,
        )
        assert _wait_until(
            lambda: (snap := store.snapshot_free_space()) is not None
            and snap.frame_id == 2
            and snap.error is None,
        )
        assert loop._smoother._ema is not None
        store.clear_depth()
        assert store.snapshot_free_space() is None
        assert _wait_until(lambda: loop._smoother._ema is None)
        assert loop._last_frame_id is None
        store.set_depth(
            frame_id=3,
            camera_id="cam0",
            t_capture=3.0,
            depth_map=_depth_map(),
            kind=DepthKind.RELATIVE,
            unit=None,
            latency_ms=1.0,
        )
        assert _wait_until(
            lambda: (snap := store.snapshot_free_space()) is not None
            and snap.frame_id == 3
            and snap.error is None,
        )
    finally:
        loop.stop()


def test_mjpeg_does_not_draw_free_space_after_depth_cleared(
    monkeypatch: Any,
) -> None:
    calls = {"free": 0, "depth": 0}

    def spy_free(image: np.ndarray, *args: Any, **kwargs: Any) -> np.ndarray:
        calls["free"] += 1
        return image

    def spy_depth(image: np.ndarray, *args: Any, **kwargs: Any) -> np.ndarray:
        calls["depth"] += 1
        return image

    monkeypatch.setattr(routes_preview, "draw_free_space", spy_free)
    monkeypatch.setattr(routes_preview, "blend_depth", spy_depth)

    store = PerceptionStore()
    t0 = time.time()
    _seed_clear_looking_free_space(store, t_capture=t0)
    bus = FrameBus()
    bus.publish(_camera_frame())
    _one_jpeg(bus, store)
    assert calls["free"] == 1
    assert calls["depth"] == 1

    calls["free"] = 0
    calls["depth"] = 0
    store.clear_depth()
    _one_jpeg(bus, store)
    assert calls["free"] == 0
    assert calls["depth"] == 0


def test_mjpeg_skips_stale_depth_and_free_space_overlays(monkeypatch: Any) -> None:
    calls = {"free": 0, "depth": 0}

    def spy_free(image: np.ndarray, *args: Any, **kwargs: Any) -> np.ndarray:
        calls["free"] += 1
        return image

    def spy_depth(image: np.ndarray, *args: Any, **kwargs: Any) -> np.ndarray:
        calls["depth"] += 1
        return image

    monkeypatch.setattr(routes_preview, "draw_free_space", spy_free)
    monkeypatch.setattr(routes_preview, "blend_depth", spy_depth)

    store = PerceptionStore()
    _seed_clear_looking_free_space(store, t_capture=time.time() - 10.0)
    bus = FrameBus()
    bus.publish(_camera_frame())
    chunk = _one_jpeg(bus, store)
    assert b"\xff\xd8" in chunk
    assert calls["free"] == 0
    assert calls["depth"] == 0


def test_mjpeg_does_not_draw_free_space_when_depth_errors(
    monkeypatch: Any,
) -> None:
    calls = {"free": 0}

    def spy_free(image: np.ndarray, *args: Any, **kwargs: Any) -> np.ndarray:
        calls["free"] += 1
        return image

    monkeypatch.setattr(routes_preview, "draw_free_space", spy_free)
    store = PerceptionStore()
    t0 = time.time()
    _seed_clear_looking_free_space(store, t_capture=t0)
    store.set_depth(
        frame_id=2,
        camera_id="cam0",
        t_capture=t0,
        depth_map=None,
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=1.0,
        error="depth failed",
    )
    bus = FrameBus()
    bus.publish(_camera_frame())
    _one_jpeg(bus, store)
    assert calls["free"] == 0
    assert store.snapshot_free_space() is None

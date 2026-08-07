"""PerceptionStore keep-latest detection product (DET-04 single truth prep)."""

from __future__ import annotations

import threading
import time

from sentry_ai.schemas.perception import Detection
from sentry_ai.state.perception_store import DetectionProduct, PerceptionStore


def _det(name: str = "person", conf: float = 0.9) -> Detection:
    return Detection(
        class_name=name,
        confidence=conf,
        bbox_xyxy=(0.0, 0.0, 10.0, 10.0),
    )


def test_snapshot_none_before_set() -> None:
    store = PerceptionStore()
    assert store.snapshot() is None


def test_set_detections_returns_product_fields() -> None:
    store = PerceptionStore()
    store.set_detections(
        frame_id=3,
        camera_id="cam0",
        t_capture=1.5,
        detections=[_det()],
        latency_ms=12.5,
        conf=0.25,
        model_name="yolo-fixed",
    )
    snap = store.snapshot()
    assert snap is not None
    assert isinstance(snap, DetectionProduct)
    assert snap.frame_id == 3
    assert snap.camera_id == "cam0"
    assert snap.t_capture == 1.5
    assert len(snap.detections) == 1
    assert snap.detections[0].class_name == "person"
    assert snap.latency_ms == 12.5
    assert snap.conf == 0.25
    assert snap.model_name == "yolo-fixed"
    assert snap.error is None


def test_set_overwrites_keep_latest() -> None:
    store = PerceptionStore()
    store.set_detections(
        frame_id=1,
        camera_id="cam0",
        t_capture=1.0,
        detections=[_det("a")],
        latency_ms=1.0,
    )
    store.set_detections(
        frame_id=2,
        camera_id="cam0",
        t_capture=2.0,
        detections=[_det("b"), _det("c")],
        latency_ms=2.0,
    )
    snap = store.snapshot()
    assert snap is not None
    assert snap.frame_id == 2
    assert len(snap.detections) == 2
    assert snap.detections[0].class_name == "b"


def test_snapshot_returns_isolated_copy() -> None:
    store = PerceptionStore()
    original = [_det("orig")]
    store.set_detections(
        frame_id=1,
        camera_id="cam0",
        t_capture=1.0,
        detections=original,
        latency_ms=1.0,
    )
    snap = store.snapshot()
    assert snap is not None
    # Mutate returned list and product fields
    snap.detections.append(_det("mutated"))
    snap.detections[0] = _det("replaced")
    # Mutate caller's original list too
    original.append(_det("caller"))

    again = store.snapshot()
    assert again is not None
    assert len(again.detections) == 1
    assert again.detections[0].class_name == "orig"


def test_empty_detections_list_is_valid_product() -> None:
    """Empty list means stage ran with no hits (completeness semantics)."""
    store = PerceptionStore()
    store.set_detections(
        frame_id=9,
        camera_id="cam0",
        t_capture=9.0,
        detections=[],
        latency_ms=3.0,
    )
    snap = store.snapshot()
    assert snap is not None
    assert snap.detections == []
    assert snap.frame_id == 9


def test_set_error_detail() -> None:
    store = PerceptionStore()
    store.set_detections(
        frame_id=1,
        camera_id="cam0",
        t_capture=1.0,
        detections=[],
        latency_ms=0.0,
        error="predict failed: boom",
    )
    snap = store.snapshot()
    assert snap is not None
    assert snap.error == "predict failed: boom"


def test_concurrent_set_and_snapshot_no_raise() -> None:
    store = PerceptionStore()
    errors: list[BaseException] = []
    stop = threading.Event()

    def writer() -> None:
        i = 0
        try:
            while not stop.is_set():
                store.set_detections(
                    frame_id=i,
                    camera_id="cam0",
                    t_capture=float(i),
                    detections=[_det(f"c{i % 3}")],
                    latency_ms=float(i),
                )
                i += 1
        except BaseException as exc:  # noqa: BLE001 — surface to main
            errors.append(exc)

    def reader() -> None:
        try:
            for _ in range(200):
                _ = store.snapshot()
                time.sleep(0.0005)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [
        threading.Thread(target=writer, daemon=True),
        threading.Thread(target=reader, daemon=True),
        threading.Thread(target=reader, daemon=True),
    ]
    for t in threads:
        t.start()
    time.sleep(0.05)
    stop.set()
    for t in threads:
        t.join(timeout=2.0)
    assert errors == []
    # Store should have some product after concurrent writes
    assert store.snapshot() is not None

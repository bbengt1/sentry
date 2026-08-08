"""OVD-03: assemble merges fixed + open-vocab with source tags."""

from __future__ import annotations

from sentry_ai.api.assemble import assemble_perception_frame
from sentry_ai.schemas.perception import Detection
from sentry_ai.state.perception_store import PerceptionStore


def test_ov_only_completeness_and_source() -> None:
    store = PerceptionStore()
    store.set_open_vocab(
        frame_id=9,
        camera_id="cam0",
        t_capture=50.0,
        detections=[
            Detection(
                class_name="cup",
                confidence=0.7,
                bbox_xyxy=(1, 2, 3, 4),
                source="open_vocab",
            )
        ],
        latency_ms=33.0,
        model_name="yoloe-open-vocab",
        prompt="cup",
    )
    frame = assemble_perception_frame(store, now=50.1)
    assert frame is not None
    assert frame.completeness.detections is True
    assert frame.detections is not None
    assert len(frame.detections) == 1
    assert frame.detections[0].source == "open_vocab"
    assert frame.detections[0].class_name == "cup"
    assert frame.stats is not None
    assert frame.stats["ov_latency_ms"] == 33.0
    assert frame.stats["ov_count"] == 1


def test_merge_fixed_first_then_ov() -> None:
    store = PerceptionStore()
    store.set_detections(
        frame_id=1,
        camera_id="cam0",
        t_capture=100.0,
        detections=[
            Detection(
                class_name="person",
                confidence=0.9,
                bbox_xyxy=(0, 0, 10, 10),
            )
        ],
        latency_ms=10.0,
    )
    store.set_open_vocab(
        frame_id=2,
        camera_id="cam0",
        t_capture=100.1,
        detections=[
            Detection(
                class_name="toolbox",
                confidence=0.6,
                bbox_xyxy=(5, 5, 15, 15),
                source="open_vocab",
            )
        ],
        latency_ms=40.0,
        prompt="toolbox",
    )
    frame = assemble_perception_frame(store, now=100.2)
    assert frame is not None
    assert frame.completeness.detections is True
    assert frame.detections is not None
    assert len(frame.detections) == 2
    assert frame.detections[0].class_name == "person"
    assert frame.detections[0].source == "fixed"
    assert frame.detections[1].class_name == "toolbox"
    assert frame.detections[1].source == "open_vocab"
    assert frame.stats is not None
    assert "ov_latency_ms" in frame.stats
    assert "det_latency_ms" in frame.stats


def test_neither_product_detections_false_when_only_depth_absent() -> None:
    """Empty store still None; OV alone is enough for non-None frame."""
    store = PerceptionStore()
    assert assemble_perception_frame(store) is None

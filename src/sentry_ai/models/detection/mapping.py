"""Map Ultralytics Results-like objects to Detection schemas (DET-02).

Pure transform: no I/O, no ultralytics import required when duck-typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sentry_ai.schemas.perception import Detection

__all__ = ["results_to_detections"]


def _to_sequence(value: Any) -> Sequence[Any]:
    """Coerce tensor-like / numpy / list boxes fields to a sequence."""
    if value is None:
        return []
    # Ultralytics torch tensors: .cpu().numpy()
    cpu = getattr(value, "cpu", None)
    if callable(cpu):
        value = cpu()
        numpy_fn = getattr(value, "numpy", None)
        if callable(numpy_fn):
            value = numpy_fn()
    # numpy ndarray: tolist for easy indexing
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        value = tolist()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return value
    # Scalar fallback
    return [value]


def _class_name(names: Any, cls_id: int) -> str:
    """Resolve class id via names dict/list; fall back to str(cls_id)."""
    if names is None:
        return str(cls_id)
    if isinstance(names, Mapping):
        # Try int then str keys (Ultralytics uses int keys)
        if cls_id in names:
            return str(names[cls_id])
        if str(cls_id) in names:
            return str(names[str(cls_id)])
        return str(cls_id)
    # list/tuple index
    try:
        return str(names[cls_id])
    except (IndexError, KeyError, TypeError):
        return str(cls_id)


def results_to_detections(result: Any) -> list[Detection]:
    """Convert one Ultralytics Results-like object to ``list[Detection]``.

    Empty or missing boxes yield ``[]`` (not ``None``). Completeness is
    decided by the perception store / loop, not this mapper.
    """
    if result is None:
        return []
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return []
    try:
        n = len(boxes)
    except TypeError:
        return []
    if n == 0:
        return []

    names = getattr(result, "names", None)
    xyxy_seq = _to_sequence(getattr(boxes, "xyxy", None))
    conf_seq = _to_sequence(getattr(boxes, "conf", None))
    cls_seq = _to_sequence(getattr(boxes, "cls", None))

    detections: list[Detection] = []
    for i in range(n):
        try:
            row = xyxy_seq[i]
        except (IndexError, TypeError):
            continue
        # row may be list/tuple of 4 floats
        coords = _to_sequence(row)
        if len(coords) < 4:
            continue
        x1 = float(coords[0])
        y1 = float(coords[1])
        x2 = float(coords[2])
        y2 = float(coords[3])

        try:
            conf = float(conf_seq[i]) if i < len(conf_seq) else 0.0
        except (TypeError, ValueError, IndexError):
            conf = 0.0

        try:
            cls_id = int(float(cls_seq[i])) if i < len(cls_seq) else -1
        except (TypeError, ValueError, IndexError):
            cls_id = -1

        detections.append(
            Detection(
                class_name=_class_name(names, cls_id),
                confidence=conf,
                bbox_xyxy=(x1, y1, x2, y2),
            )
        )
    return detections

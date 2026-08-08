"""YOLOE open-vocabulary detection worker (OVD-01).

Implements ModelWorker. Never opens cameras — only consumes ImageFrame.image_bgr.
Real YOLOE load is optional; inject ``model`` for tests (no weight download).

AGPL: Ultralytics YOLOE weights — see THIRD_PARTY_MODELS.md.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.models.cache import configure_model_cache
from sentry_ai.models.detection.mapping import results_to_detections
from sentry_ai.models.device import resolve_device
from sentry_ai.schemas.perception import Detection

logger = logging.getLogger(__name__)

DEFAULT_CONF = 0.25
DEFAULT_IMGSZ = 640
DEFAULT_WEIGHTS = "yoloe-26s-seg.pt"

__all__ = ["DEFAULT_WEIGHTS", "YoloeOpenVocabWorker", "resolve_device"]


class YoloeOpenVocabWorker:
    """Open-vocab YOLOE ModelWorker (plugin name ``yoloe-open-vocab``)."""

    name: str = "yoloe-open-vocab"

    def __init__(
        self,
        weights: str = DEFAULT_WEIGHTS,
        conf: float = DEFAULT_CONF,
        device: str | None = None,
        model: Any | None = None,
    ) -> None:
        self._weights = weights
        self._device_arg = device
        self._device: str | None = None
        self._model = model
        self._conf_lock = threading.Lock()
        self._conf = self._validate_conf(conf)
        self._load_lock = threading.Lock()
        self._prompt_lock = threading.Lock()
        self._classes: list[str] = []
        self._classes_dirty: bool = False

    # --- conf -----------------------------------------------------------------

    @staticmethod
    def _validate_conf(conf: float) -> float:
        value = float(conf)
        if value < 0.0 or value > 1.0:
            raise ValueError(f"conf must be in [0, 1], got {conf!r}")
        return value

    def set_conf(self, conf: float) -> None:
        """Update confidence threshold for the next ``process`` call."""
        value = self._validate_conf(conf)
        with self._conf_lock:
            self._conf = value

    def get_conf(self) -> float:
        with self._conf_lock:
            return self._conf

    # --- prompt classes -------------------------------------------------------

    def set_prompt_classes(self, classes: list[str]) -> None:
        """Set text prompt classes; strips empties; marks dirty for set_classes."""
        cleaned: list[str] = []
        for item in classes:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                cleaned.append(text)
        with self._prompt_lock:
            self._classes = cleaned
            self._classes_dirty = True

    def get_prompt_classes(self) -> list[str]:
        with self._prompt_lock:
            return list(self._classes)

    # --- model load -----------------------------------------------------------

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model
        with self._load_lock:
            if self._model is not None:
                return self._model
            configure_model_cache()
            try:
                from ultralytics import YOLOE  # type: ignore[import-untyped]
            except ImportError as exc:
                raise ImportError(
                    "ultralytics is required for YoloeOpenVocabWorker. "
                    "Install the detect extra: uv sync --extra detect"
                ) from exc
            self._device = resolve_device(self._device_arg)
            logger.info(
                "Loading YOLOE weights=%s device=%s",
                self._weights,
                self._device,
            )
            model = YOLOE(self._weights)
            # Optional warm-up skipped for OV — set_classes required first.
            self._model = model
            return self._model

    # --- ModelWorker ----------------------------------------------------------

    def process(self, frame: ImageFrame | object) -> list[Detection]:
        """Run open-vocab detection on ``frame.image_bgr``; tag source=open_vocab."""
        image_bgr = getattr(frame, "image_bgr", None)
        if image_bgr is None:
            logger.warning("YoloeOpenVocabWorker.process: frame missing image_bgr")
            return []

        with self._prompt_lock:
            classes = list(self._classes)
            dirty = self._classes_dirty

        if not classes:
            return []

        model = self._ensure_model()

        if dirty:
            # YOLOE text prompts: set_classes once per prompt change.
            model.set_classes(classes)
            with self._prompt_lock:
                # Only clear dirty if classes still match what we applied.
                if self._classes == classes:
                    self._classes_dirty = False

        conf = self.get_conf()
        device = self._device if self._device is not None else resolve_device(
            self._device_arg
        )
        if self._device is None:
            self._device = device

        results = model.predict(
            source=image_bgr,
            conf=conf,
            imgsz=DEFAULT_IMGSZ,
            device=device,
            verbose=False,
            save=False,
        )
        if not results:
            return []
        mapped = results_to_detections(results[0])
        # Re-tag source after mapping (mapper defaults to fixed).
        return [
            Detection(
                class_name=d.class_name,
                confidence=d.confidence,
                bbox_xyxy=d.bbox_xyxy,
                source="open_vocab",
            )
            for d in mapped
        ]

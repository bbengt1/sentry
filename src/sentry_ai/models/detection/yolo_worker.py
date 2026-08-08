"""YOLO26 fixed-class detection worker (DET-01).

Implements ModelWorker. Never opens cameras — only consumes ImageFrame.image_bgr.
Real YOLO load is optional; inject ``model`` for tests (no weight download).
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
DEFAULT_WEIGHTS = "yolo26n.pt"

__all__ = ["YoloDetectionWorker", "resolve_device"]


class YoloDetectionWorker:
    """Fixed-class YOLO26 ModelWorker (plugin name ``yolo-fixed``)."""

    name: str = "yolo-fixed"

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

    # --- conf (DET-03 foundation) ---------------------------------------------

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

    # --- model load -----------------------------------------------------------

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model
        with self._load_lock:
            if self._model is not None:
                return self._model
            configure_model_cache()
            try:
                from ultralytics import YOLO  # type: ignore[import-untyped]
            except ImportError as exc:
                raise ImportError(
                    "ultralytics is required for YoloDetectionWorker. "
                    "Install the detect extra: uv sync --extra detect"
                ) from exc
            self._device = resolve_device(self._device_arg)
            logger.info(
                "Loading YOLO weights=%s device=%s",
                self._weights,
                self._device,
            )
            model = YOLO(self._weights)
            # Optional warm-up on zeros so first real frame is not cold.
            try:
                import numpy as np

                dummy = np.zeros((DEFAULT_IMGSZ, DEFAULT_IMGSZ, 3), dtype=np.uint8)
                model.predict(
                    source=dummy,
                    conf=self.get_conf(),
                    imgsz=DEFAULT_IMGSZ,
                    device=self._device,
                    verbose=False,
                    save=False,
                )
                logger.info("YOLO model ready (warm-up complete)")
            except Exception:  # noqa: BLE001 — warm-up is best-effort
                logger.debug("YOLO warm-up skipped/failed", exc_info=True)
            self._model = model
            return self._model

    # --- ModelWorker ----------------------------------------------------------

    def process(self, frame: ImageFrame | object) -> list[Detection]:
        """Run detection on ``frame.image_bgr``; return list[Detection]."""
        image_bgr = getattr(frame, "image_bgr", None)
        if image_bgr is None:
            logger.warning("YoloDetectionWorker.process: frame missing image_bgr")
            return []

        model = self._ensure_model()
        conf = self.get_conf()
        device = self._device if self._device is not None else resolve_device(
            self._device_arg
        )
        # Cache resolved device for subsequent calls when model was injected.
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
        return results_to_detections(results[0])

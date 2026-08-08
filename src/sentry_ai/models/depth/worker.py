"""Depth Anything V2 Small worker (DEPTH-01).

Implements ModelWorker. Never opens cameras — only consumes ImageFrame.image_bgr.
Real HF load is optional; inject ``model`` + ``processor`` for tests (no download).
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any

import numpy as np

from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.models.cache import configure_model_cache
from sentry_ai.models.depth.mapping import MODE_TO_MODEL, kind_for_mode
from sentry_ai.models.depth.preprocess import bgr_to_rgb_uint8
from sentry_ai.schemas.enums import DepthKind

logger = logging.getLogger(__name__)

__all__ = [
    "DepthAnythingWorker",
    "DepthResult",
    "resolve_device",
]


@dataclass
class DepthResult:
    """In-process depth product from one ``process`` call."""

    depth_map: np.ndarray | None
    kind: DepthKind
    unit: str | None
    width: int = 0
    height: int = 0
    error: str | None = None


def resolve_device(device: str | None = None) -> str:
    """Pick inference device: explicit arg, else cuda > mps > cpu."""
    if device is not None:
        return device
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        mps = getattr(getattr(torch, "backends", None), "mps", None)
        if mps is not None and getattr(mps, "is_available", lambda: False)():
            return "mps"
    except ImportError:
        pass
    return "cpu"


class DepthAnythingWorker:
    """DAV2 Small ModelWorker (plugin name ``depth-anything-v2-small``)."""

    name: str = "depth-anything-v2-small"

    def __init__(
        self,
        model_id: str | None = None,
        depth_mode: str = "relative",
        device: str | None = None,
        model: Any | None = None,
        processor: Any | None = None,
    ) -> None:
        if depth_mode not in MODE_TO_MODEL:
            raise ValueError(
                f"unknown depth_mode: {depth_mode!r}; "
                f"expected one of {sorted(MODE_TO_MODEL)}"
            )
        self._depth_mode_lock = threading.Lock()
        self._depth_mode = depth_mode
        self._model_id = model_id if model_id is not None else MODE_TO_MODEL[depth_mode]
        self._device_arg = device
        self._device: str | None = None
        self._model = model
        self._processor = processor
        self._load_lock = threading.Lock()

    @property
    def model_id(self) -> str:
        return self._model_id

    def get_depth_mode(self) -> str:
        with self._depth_mode_lock:
            return self._depth_mode

    def set_depth_mode(self, mode: str) -> None:
        """Update depth_mode for next process (kind/unit from mode only)."""
        if mode not in MODE_TO_MODEL:
            raise ValueError(
                f"unknown depth_mode: {mode!r}; "
                f"expected one of {sorted(MODE_TO_MODEL)}"
            )
        with self._depth_mode_lock:
            self._depth_mode = mode
            # Keep model_id aligned when caller did not pin a custom id path.
            # Always update to mapped Small id for the new mode.
            self._model_id = MODE_TO_MODEL[mode]

    def _ensure_model(self) -> tuple[Any, Any]:
        if self._model is not None and self._processor is not None:
            return self._model, self._processor
        with self._load_lock:
            if self._model is not None and self._processor is not None:
                return self._model, self._processor
            configure_model_cache()
            try:
                from transformers import (  # type: ignore[import-untyped]
                    AutoImageProcessor,
                    AutoModelForDepthEstimation,
                )
            except ImportError as exc:
                raise ImportError(
                    "transformers is required for DepthAnythingWorker. "
                    "Install the depth extra: uv sync --extra depth"
                ) from exc

            self._device = resolve_device(self._device_arg)
            logger.info(
                "Loading depth model_id=%s device=%s",
                self._model_id,
                self._device,
            )
            processor = AutoImageProcessor.from_pretrained(self._model_id)
            model = AutoModelForDepthEstimation.from_pretrained(self._model_id)
            model.to(self._device).eval()
            self._processor = processor
            self._model = model
            return self._model, self._processor

    def process(self, frame: ImageFrame | object) -> DepthResult:
        """Run monocular depth on ``frame.image_bgr``; return DepthResult."""
        mode = self.get_depth_mode()
        kind, unit = kind_for_mode(mode)

        image_bgr = getattr(frame, "image_bgr", None)
        if image_bgr is None:
            logger.warning("DepthAnythingWorker.process: frame missing image_bgr")
            return DepthResult(
                depth_map=None,
                kind=kind,
                unit=unit,
                width=0,
                height=0,
                error="frame missing image_bgr",
            )

        h = int(image_bgr.shape[0])
        w = int(image_bgr.shape[1])
        rgb = bgr_to_rgb_uint8(image_bgr)

        model, processor = self._ensure_model()
        device = self._device if self._device is not None else resolve_device(
            self._device_arg
        )
        if self._device is None:
            self._device = device

        # Prefer PIL Image for HF processors when pillow is available.
        try:
            from PIL import Image

            pil_image = Image.fromarray(rgb)
            images_arg: Any = pil_image
        except ImportError:
            images_arg = rgb

        # Injected fakes may not need torch; real path does.
        inputs = processor(images=images_arg, return_tensors="pt")

        depth_map = self._forward_depth(model, inputs, h=h, w=w, device=device)
        return DepthResult(
            depth_map=depth_map,
            kind=kind,
            unit=unit,
            width=w,
            height=h,
            error=None,
        )

    @staticmethod
    def _normalize_model_inputs(inputs: Any, device: str) -> dict[str, Any]:
        """Normalize HF BatchFeature / Mapping / bare tensor to kwargs for model(**).

        AutoImageProcessor returns BatchFeature, which is *not* always a plain
        dict. Passing it as a single positional arg makes DINOv2 look for
        ``pixel_values.shape`` on the BatchFeature and raises AttributeError.
        """
        # Mapping / BatchFeature / UserDict-style
        if hasattr(inputs, "items") and not hasattr(inputs, "shape"):
            items = dict(inputs.items())
        elif isinstance(inputs, dict):
            items = dict(inputs)
        else:
            # Bare tensor or array treated as pixel_values
            items = {"pixel_values": inputs}

        moved: dict[str, Any] = {}
        for key, value in items.items():
            if hasattr(value, "to"):
                try:
                    moved[key] = value.to(device)
                except (TypeError, RuntimeError, AttributeError):
                    moved[key] = value
            else:
                moved[key] = value
        return moved

    def _forward_depth(
        self,
        model: Any,
        inputs: Any,
        *,
        h: int,
        w: int,
        device: str,
    ) -> np.ndarray:
        """Run model and return HxW float32 depth map at original resolution."""
        # Fake path: model returns SimpleNamespace with numpy predicted_depth.
        try:
            import torch
            import torch.nn.functional as F
        except ImportError:
            torch = None  # type: ignore[assignment]
            F = None  # type: ignore[assignment]

        kwargs = self._normalize_model_inputs(inputs, device)

        if torch is not None:
            with torch.no_grad():
                outputs = model(**kwargs)
        else:
            outputs = model(**kwargs)

        predicted = getattr(outputs, "predicted_depth", outputs)

        # Convert to numpy HxW.
        if torch is not None and hasattr(predicted, "detach"):
            pred = predicted.detach()
            if pred.ndim == 3:
                # (B, H', W') — take first batch
                pred = pred[0:1]
            elif pred.ndim == 2:
                pred = pred.unsqueeze(0)
            # Interpolate to original size when spatial dims differ.
            if pred.shape[-2] != h or pred.shape[-1] != w:
                assert F is not None
                # pred is (B, H', W'); interpolate needs (N, C, H, W)
                pred4 = pred.unsqueeze(1) if pred.ndim == 3 else pred
                pred4 = F.interpolate(
                    pred4,
                    size=(h, w),
                    mode="bilinear",
                    align_corners=False,
                )
                pred = pred4.squeeze(1)
            depth_np = pred.squeeze().float().cpu().numpy().astype(np.float32)
            return depth_np

        # Numpy / fake path
        arr = np.asarray(predicted, dtype=np.float32)
        if arr.ndim == 3:
            arr = arr[0]
        if arr.shape[0] != h or arr.shape[1] != w:
            # Prefer exact size from fake models in tests.
            if arr.size == h * w:
                arr = arr.reshape(h, w)
            else:
                import cv2

                arr = cv2.resize(arr, (w, h), interpolation=cv2.INTER_LINEAR)
        return arr.astype(np.float32, copy=False)

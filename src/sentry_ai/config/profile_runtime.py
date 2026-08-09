"""Profile → weights + device policy for serve construction (EDGE-02).

Pure helpers only — no FastAPI, no torch import, no weight download.

``preferred_backend`` selects a detection **loader branch** at serve via
``build_detection_worker`` (Phase 8+). Live identity comes from the factory
``backend_live`` field — not from device policy alone. ``device_for_backend``
still maps preferred_backend → torch device strings for the live worker
(never a fake ``\"tensorrt\"`` device).
"""

from __future__ import annotations

from dataclasses import dataclass

from sentry_ai.config.models import SentryConfig
from sentry_ai.models.cache import tier_to_open_vocab_weight, tier_to_weight
from sentry_ai.models.depth.mapping import tier_to_depth_model_id
from sentry_ai.schemas.enums import BackendName, RuntimeProfile

__all__ = [
    "ProfileRuntime",
    "device_for_backend",
    "profile_runtime",
]


@dataclass(frozen=True)
class ProfileRuntime:
    """Resolved serve-time model tiers and device policy for a profile."""

    profile: RuntimeProfile
    detector_weights: str
    open_vocab_weights: str
    depth_model_id: str
    depth_tier: str
    preferred_backend: str
    device: str | None
    device_id: str


def device_for_backend(
    backend: BackendName | str,
    device_id: str,
) -> str | None:
    """Map preferred_backend + device_id to a live worker device string.

    Honesty (v1 — live path remains PyTorch Ultralytics/HF):

    - ``cpu`` / ``onnxruntime`` → force ``\"cpu\"`` (ORT is export target)
    - ``torch`` → explicit cuda-like device_id, or None for resolve_device()
    - ``tensorrt`` → cuda-like device for live PyTorch path (not TRT runtime)
    - ``openvino`` → None (advisory only; no runtime)

    Never returns a fake ``\"tensorrt\"`` torch device string.
    """
    b = str(backend).strip().lower()
    # Handle "BackendName.TORCH" style if someone str()'s the enum oddly.
    if b.startswith("backendname."):
        b = b.split(".", 1)[1].lower()
    did = (device_id or "").strip()

    if b in {"cpu", "onnxruntime"}:
        return "cpu"

    if b in {"torch", "tensorrt"}:
        if not did or did.lower() == "cpu":
            # torch+cpu → auto; tensorrt with no usable id → cuda:0 default
            if b == "tensorrt":
                return "cuda:0"
            return None
        if did.startswith("cuda"):
            return did
        # Bare GPU index (Jetson device_id: "0") → cuda:N
        if did.isdigit():
            return f"cuda:{did}"
        # Other non-cpu ids (e.g. "mps") pass through for torch
        if b == "torch":
            return did
        return "cuda:0"

    # openvino and unknown: advisory only
    return None


def profile_runtime(cfg: SentryConfig) -> ProfileRuntime:
    """Compose detector/OV/depth weights + device policy from a loaded config."""
    detector_tier = cfg.models.detector_tier
    # Optional open_vocab_tier if present; else derive from detector_tier (A7).
    ov_tier = getattr(cfg.models, "open_vocab_tier", None) or detector_tier
    depth_tier_raw = cfg.models.depth_tier or "small"
    depth_model_id = tier_to_depth_model_id(depth_tier_raw, depth_mode="relative")
    preferred = cfg.device.preferred_backend
    preferred_str = (
        preferred.value if isinstance(preferred, BackendName) else str(preferred)
    )
    device_id = cfg.device.device_id or "cpu"
    device = device_for_backend(preferred, device_id)

    return ProfileRuntime(
        profile=cfg.profile,
        detector_weights=tier_to_weight(detector_tier),
        open_vocab_weights=tier_to_open_vocab_weight(ov_tier),
        depth_model_id=depth_model_id,
        depth_tier=str(depth_tier_raw).strip().lower(),
        preferred_backend=preferred_str,
        device=device,
        device_id=device_id,
    )

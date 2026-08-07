"""Hot-path runtime frame container (not a Pydantic/wire model).

``ImageFrame`` pairs schema identity (``Frame``) with a BGR image array.
Keep numpy off ``schemas.frame.Frame`` so wire contracts stay identity-only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sentry_ai.schemas.frame import Frame


@dataclass(slots=True)
class ImageFrame:
    """Process-local frame: identity metadata + BGR uint8 image."""

    meta: Frame
    image_bgr: np.ndarray  # HxWx3 uint8, contiguous preferred

    @property
    def frame_id(self) -> int:
        return self.meta.frame_id

    @property
    def camera_id(self) -> str:
        return self.meta.camera_id

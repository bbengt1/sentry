"""Synthetic patterned-BGR camera source (CAM-03).

Produces deterministic ImageFrames without hardware or model inference.
Default fps=0.0 avoids sleep in unit tests; serve demos may pass fps>0.
"""

from __future__ import annotations

import time

import numpy as np

from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.schemas.frame import Frame


class SyntheticSource:
    """Yields patterned BGR ImageFrames without camera hardware."""

    name: str = "synthetic"

    def __init__(
        self,
        camera_id: str = "synthetic0",
        width: int = 640,
        height: int = 480,
        fps: float = 0.0,
    ) -> None:
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self._next_frame_id = 0
        self._open = False

    def open(self) -> None:
        self._open = True
        self._next_frame_id = 0

    def read(self) -> ImageFrame:
        if not self._open:
            raise RuntimeError("SyntheticSource is not open; call open() first")

        # Moving green bar keyed by frame_id — deterministic for tests.
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        x = (self._next_frame_id * 8) % max(self.width, 1)
        bar_end = min(x + 16, self.width)
        img[:, x:bar_end] = (0, 255, 0)

        now = time.time()
        meta = Frame(
            frame_id=self._next_frame_id,
            camera_id=self.camera_id,
            t_capture=now,
            t_ingest=now,
            width=self.width,
            height=self.height,
        )
        self._next_frame_id += 1

        if self.fps > 0:
            time.sleep(1.0 / self.fps)

        return ImageFrame(meta=meta, image_bgr=img)

    def close(self) -> None:
        self._open = False

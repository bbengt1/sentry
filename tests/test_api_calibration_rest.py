"""Compute/apply/cancel/clear REST tests (helpers in test_api_calibration)."""

from __future__ import annotations

import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.control.calibration_state import CalibrationState
from sentry_ai.models.depth.loop import DepthLoop
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.frame import Frame
from sentry_ai.state.perception_store import PerceptionStore

from tests.test_api_calibration import (
    _LoopDepthWorker,
    _app,
    _compute,
    _sample_body,
    _seed_depth,
)

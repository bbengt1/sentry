"""MODEL-01 policy: local open-source models on the core path.

No network calls. Weight names are documentation / allowlist hooks only;
downloads and inference land in later phases.
"""

from __future__ import annotations

# Core perception path must not require cloud inference (MODEL-01).
CORE_PATH_LOCAL_OSS_ONLY: bool = True
DEFAULT_ALLOW_CLOUD: bool = False

# Default commercially friendly weight keys (names only; no downloads).
DEFAULT_DEPTH_WEIGHT_KEY: str = "depth-anything-v2-small"
DEFAULT_COMMERCIALLY_FRIENDLY_WEIGHTS: frozenset[str] = frozenset(
    {
        "depth-anything-v2-small",
    }
)

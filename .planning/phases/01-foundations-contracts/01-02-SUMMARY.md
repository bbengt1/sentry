---
phase: 01-foundations-contracts
plan: 02
subsystem: schemas-config
tags: [pydantic-v2, depth-kind, perception-frame, yaml-config, runtime-profile, model-01, pytest, tdd]

# Dependency graph
requires:
  - phase: 01-foundations-contracts/01-01
    provides: "Installable sentry_ai package, pytest/ruff, Wave 0 test stubs"
provides:
  - "Frame / PerceptionFrame / Completeness / DepthPayload contracts"
  - "DepthKind honesty validators (no meters on relative; no depth_m)"
  - "RuntimeProfile multi-profile YAML config with yaml.safe_load"
  - "MODEL-01 local OSS policy constants and allow_cloud default false"
affects: [01-03, foundations-contracts, frame-bus, perception-workers]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic v2 wire models with extra=forbid"
    - "StrEnum for DepthKind / RuntimeProfile / BackendName"
    - "DepthPayload model_validator forbids unit on relative depth"
    - "Config merge: built-in profile YAML → user file → env overrides"
    - "yaml.safe_load only for untrusted config input"
    - "TDD RED test commits before GREEN feat commits"

key-files:
  created:
    - src/sentry_ai/schemas/__init__.py
    - src/sentry_ai/schemas/enums.py
    - src/sentry_ai/schemas/frame.py
    - src/sentry_ai/schemas/perception.py
    - src/sentry_ai/schemas/validators.py
    - src/sentry_ai/config/__init__.py
    - src/sentry_ai/config/models.py
    - src/sentry_ai/config/load.py
    - src/sentry_ai/config/profiles/desktop-gpu.yaml
    - src/sentry_ai/config/profiles/jetson.yaml
    - src/sentry_ai/config/profiles/cpu-fallback.yaml
    - src/sentry_ai/policy/__init__.py
    - src/sentry_ai/policy/models.py
  modified:
    - tests/conftest.py
    - tests/test_schemas_frame.py
    - tests/test_schemas_depth_kind.py
    - tests/test_schemas_perception.py
    - tests/test_config_profiles.py
    - pyproject.toml

key-decisions:
  - "DepthPayload lives in perception.py with shared validator helper"
  - "StrEnum instead of (str, Enum) to satisfy ruff UP042 on Python 3.11+"
  - "Thin Detection / FreeSpacePayload models instead of bare dict placeholders"
  - "Profile YAML path resolved via Path(__file__).parent; hatch force-include for wheels"
  - "SENTRY_ALLOW_CLOUD env is the explicit opt-in path; model/YAML default false"

patterns-established:
  - "Pattern: TDD RED (test commit) → GREEN (feat commit) per task"
  - "Pattern: epoch float timestamps documented in module docstrings"
  - "Pattern: synthetic_frame_factory fixture in conftest for schema-valid Frames"
  - "Pattern: policy constants module with no network I/O"

requirements-completed: [FOUND-02, FOUND-03, FOUND-06, MODEL-01]

# Metrics
duration: 4min
completed: 2026-08-07
---

# Phase 1 Plan 02: Schemas & Config Summary

**Pydantic v2 Frame/PerceptionFrame contracts with DepthKind honesty validators, three runtime profile YAMLs, and MODEL-01 local-only defaults.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-08-07T14:27:08Z
- **Completed:** 2026-08-07T14:30:55Z
- **Tasks:** 3/3
- **Files modified:** 19 created/updated

## Accomplishments

- `Frame` requires `frame_id`, `camera_id`, epoch `t_capture`; `extra="forbid"`
- `DepthKind` = relative | metric_estimated | metric_calibrated; relative + unit="m" rejected; no `depth_m` field
- `PerceptionFrame` with Completeness defaults, nested honest depth, Detection/FreeSpace placeholders, no motor/cmd fields
- Three profiles (`desktop-gpu`, `jetson`, `cpu-fallback`) load via `yaml.safe_load`; `allow_cloud` defaults false
- Policy module exposes `CORE_PATH_LOCAL_OSS_ONLY = True` and default weight key hooks

## Task Commits

Each task was committed atomically (TDD RED → GREEN):

1. **Task 1 RED: Frame/DepthKind tests** - `db0a846` (test)
2. **Task 1 GREEN: Frame, DepthKind, DepthPayload** - `f7135d5` (feat)
3. **Task 2 RED: PerceptionFrame tests** - `97e8772` (test)
4. **Task 2 GREEN: PerceptionFrame + Completeness** - `2c07a44` (feat)
5. **Task 3 RED: config/profile tests** - `78935de` (test)
6. **Task 3 GREEN: multi-profile config + MODEL-01** - `1c58f3e` (feat)

**Plan metadata:** (pending final docs commit)

## Files Created/Modified

- `src/sentry_ai/schemas/enums.py` — DepthKind, RuntimeProfile, BackendName (StrEnum)
- `src/sentry_ai/schemas/frame.py` — Frame identity contract
- `src/sentry_ai/schemas/perception.py` — PerceptionFrame, Completeness, DepthPayload, Detection, FreeSpacePayload
- `src/sentry_ai/schemas/validators.py` — relative-depth unit guard
- `src/sentry_ai/schemas/__init__.py` — public re-exports
- `src/sentry_ai/config/models.py` — SentryConfig tree (`allow_cloud: False` default)
- `src/sentry_ai/config/load.py` — `load_profile` / `load_config` with safe YAML + env
- `src/sentry_ai/config/profiles/*.yaml` — three built-in profiles
- `src/sentry_ai/policy/models.py` — MODEL-01 constants
- `tests/test_schemas_*.py`, `tests/test_config_profiles.py` — real coverage (no longer skipped)
- `tests/conftest.py` — `make_synthetic_frame` + fixture
- `pyproject.toml` — hatch force-include for profile YAMLs

## Decisions Made

- Used `enum.StrEnum` (ruff UP042) rather than `(str, Enum)` from research sketch — values unchanged
- Placed `DepthPayload` in `perception.py` with validator helper in `validators.py` (single definition)
- Preferred typed `Detection` / `FreeSpacePayload` over bare dicts per research Q4 recommendation
- Config path uses filesystem relative to package module (works for editable install); wheel packaging via hatch force-include

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] StrEnum for ruff UP042 compliance**
- **Found during:** Task 1 GREEN
- **Issue:** ruff UP042 rejects `class X(str, Enum)` on Python 3.11+
- **Fix:** Use `enum.StrEnum` with identical string values
- **Files modified:** `src/sentry_ai/schemas/enums.py`
- **Verification:** ruff clean; enum value tests pass
- **Committed in:** `f7135d5`

**2. [Rule 1 - Bug] Synthetic factory test import path**
- **Found during:** Task 1 GREEN
- **Issue:** `from tests.conftest import make_synthetic_frame` failed (`tests` not a package)
- **Fix:** Expose factory via `synthetic_frame_factory` pytest fixture
- **Files modified:** `tests/conftest.py`, `tests/test_schemas_frame.py`
- **Verification:** factory test passes
- **Committed in:** `f7135d5`

---

**Total deviations:** 2 auto-fixed (1 Rule 2, 1 Rule 1)
**Impact on plan:** Minor correctness/tooling fixes; no scope creep into 01-03

## Issues Encountered

None beyond the auto-fixed deviations above.

## Verification Results

```text
uv run pytest -q tests/test_schemas_*.py tests/test_config_profiles.py  # 44 passed
uv run pytest -q                                                         # 47 passed, 3 skipped (01-03)
uv run ruff check src tests                                              # All checks passed
DepthKind values relative|metric_estimated|metric_calibrated             # OK
relative + unit=m raises ValidationError                                 # OK
"depth_m" not in DepthPayload.model_fields                               # OK
three profiles load; allow_cloud False                                   # OK
yaml.safe_load only in config/load.py                                    # OK
no torch/opencv/fastapi added                                            # OK
```

## Requirement Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FOUND-02 | Satisfied | Frame + PerceptionFrame identity fields, completeness, tests |
| FOUND-03 | Satisfied | DepthKind enum + relative unit rejection + no depth_m |
| FOUND-06 | Satisfied (profile portion) | RuntimeProfile + three YAML profiles + load_profile |
| MODEL-01 | Satisfied | allow_cloud default false; CORE_PATH_LOCAL_OSS_ONLY |

Note: FOUND-06 device/backend **protocol stubs** remain for 01-03; this plan ships profile enum + config only as specified.

## Known Stubs

Intentional Phase 1 stubs (do not block this plan's goals):

| File | Stub | Resolved by |
|------|------|-------------|
| `Detection` / `FreeSpacePayload` | Minimal fields only | Phases 3 / 5 |
| `stats: dict \| None` | Loose until Phase 5 | Phase 5 |
| `preferred_backend` | Advisory string/enum; not executed | Later inference phases |
| CLI `smoke` | Still skeleton (no Frame validation) | 01-03 |
| Plugin/backend tests | Still skip-marked | 01-03 |

## Threat Flags

None new beyond plan threat model (T-1-01 safe_load, T-1-04 allow_cloud false, T-1-05 perception-only fields, depth honesty).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for **01-03**: plugin registry, InferenceBackend protocols, `THIRD_PARTY_MODELS.md`, full smoke validating synthetic Frames → PerceptionFrame
- Schemas and config are importable: `from sentry_ai.schemas import Frame, PerceptionFrame, DepthKind`
- Config: `from sentry_ai.config import load_profile, load_config`

## Self-Check: PASSED

- Created files exist under `src/sentry_ai/schemas/`, `config/`, `policy/`
- Commits present: `db0a846`, `f7135d5`, `97e8772`, `2c07a44`, `78935de`, `1c58f3e`
- Full suite green: 47 passed, 3 skipped; ruff clean

---
*Phase: 01-foundations-contracts*
*Completed: 2026-08-07*

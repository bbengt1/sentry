---
phase: 07-edge-profiles-extension-stubs
plan: 01
subsystem: edge-runtime
tags: [profiles, headless, device-policy, yolo26, yoloe, depth-anything, probe_device, fastapi]

# Dependency graph
requires:
  - phase: 01-foundations-contracts
    provides: RuntimeProfile YAML, load_config, BackendName, probe_device stub
  - phase: 03-detection
    provides: YoloDetectionWorker + tier_to_weight at serve
  - phase: 04-depth
    provides: DepthAnythingWorker + MODE_TO_MODEL Small allowlist
  - phase: 06-developer-controls-open-vocab
    provides: YoloeOpenVocabWorker + KNOWN_WEIGHTS yoloe n/s
provides:
  - ProfileRuntime pure helpers (detector/OV/depth weights + device policy)
  - Serve-time profile application for YOLO/YOLOE/Depth workers
  - Light non-raising probe_device with optional torch.cuda
  - Headless serve via create_app(serve_ui=False) + sentry serve --no-ui
affects: [07-02-export-recipes, 07-03-extension-stubs-docs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "profile_runtime(cfg) composes tier maps + device_for_backend honesty"
    - "preferred_backend is device policy/export target; live path stays PyTorch"
    - "create_app(serve_ui=...) gates GET / HTML only; MJPEG/API/v1 stay"

key-files:
  created:
    - src/sentry_ai/config/profile_runtime.py
    - tests/test_profile_application.py
    - tests/test_headless_serve.py
  modified:
    - src/sentry_ai/models/cache.py
    - src/sentry_ai/models/depth/mapping.py
    - src/sentry_ai/backend/protocols.py
    - src/sentry_ai/cli.py
    - src/sentry_ai/api/app.py
    - src/sentry_ai/api/routes_preview.py
    - src/sentry_ai/config/profiles/desktop-gpu.yaml
    - src/sentry_ai/config/profiles/jetson.yaml
    - src/sentry_ai/config/profiles/cpu-fallback.yaml
    - tests/test_model_cache.py
    - tests/test_depth_mapping.py
    - tests/test_config_profiles.py
    - tests/test_cli_serve.py
    - tests/test_backend_protocols.py

key-decisions:
  - "Serve default remains cpu-fallback; no CUDA auto-switch to desktop-gpu"
  - "Open-vocab weights derive from detector_tier (no open_vocab_tier YAML field)"
  - "tensorrt/onnxruntime preferred_backend → device policy + honesty logs only"
  - "depth_tier Small-only allowlist; Base/Large NC raise ValueError"
  - "Headless is --no-ui / serve_ui=False, not separate sentry api command"
  - "probe_device never raises; cpu-fallback available=True; GPU profiles use torch.cuda when present"

patterns-established:
  - "ProfileRuntime frozen dataclass for serve construction"
  - "device_for_backend maps backend enum → torch device string or None"
  - "Banner prints profile/weights/backend/device/probe before bind line"
  - "root_preview reads app.state.serve_ui (default True for compat)"

requirements-completed: [EDGE-02, EDGE-05]

# Metrics
duration: 6min
completed: 2026-08-08
---

# Phase 7 Plan 01: Edge Profiles + Headless Serve Summary

**Runtime profiles drive detector/OV/depth tiers and honest device policy at serve; headless `--no-ui` serves perception APIs without Live Preview HTML**

## Performance

- **Duration:** 6 min
- **Started:** 2026-08-08T17:02:33Z
- **Completed:** 2026-08-08T17:08:39Z
- **Tasks:** 3
- **Files modified:** 18

## Accomplishments

- `ProfileRuntime` + `device_for_backend` map all three profiles to weights and device policy without torch/FastAPI imports
- `sentry serve` constructs YOLO/YOLOE/Depth workers from profile tiers; banner is honest about tensorrt/onnxruntime export targets
- Headless mode: `create_app(serve_ui=False)` and `sentry serve --no-ui` gate GET `/` HTML while keeping `/api/*`, `/v1/*`, `/preview/mjpeg`
- Light `probe_device` never raises; optional CUDA check; cpu-fallback reports available

## Task Commits

Each task was committed atomically:

1. **Task 1: ProfileRuntime helpers — OV tier, depth tier, device policy** - `deb8301` (feat)
2. **Task 2: Wire serve profile application + light probe_device + startup banner** - `d79cd48` (feat)
3. **Task 3: Headless serve — serve_ui flag, --no-ui, API without HTML** - `29d28dc` (feat)

**Plan metadata:** (pending final docs commit)

## Files Created/Modified

- `src/sentry_ai/config/profile_runtime.py` — ProfileRuntime, profile_runtime(), device_for_backend()
- `src/sentry_ai/models/cache.py` — tier_to_open_vocab_weight (n→yoloe-26n, s/m→yoloe-26s)
- `src/sentry_ai/models/depth/mapping.py` — ALLOWED_DEPTH_TIERS, assert_depth_tier_allowed, tier_to_depth_model_id
- `src/sentry_ai/backend/protocols.py` — light non-raising probe_device
- `src/sentry_ai/cli.py` — profile application, banner honesty, --no-ui
- `src/sentry_ai/api/app.py` — create_app(serve_ui=...)
- `src/sentry_ai/api/routes_preview.py` — root_preview gates HTML when headless
- `src/sentry_ai/config/profiles/*.yaml` — comments: preferred_backend is device policy
- `tests/test_profile_application.py` — EDGE-02 unit coverage
- `tests/test_headless_serve.py` — EDGE-05 create_app + API tests
- Extended: test_model_cache, test_depth_mapping, test_config_profiles, test_cli_serve, test_backend_protocols

## Decisions Made

- Kept serve default `cpu-fallback` (safe CI/laptop path; desktop-gpu is opt-in)
- Derived open-vocab tier from `detector_tier` without adding YAML `open_vocab_tier`
- tensorrt → `cuda:0` (or cuda-like from device_id) for live PyTorch; never claim TRT inference
- onnxruntime → force `device=cpu`; log ORT as export target
- Headless keeps MJPEG for debug; only GET `/` HTML is gated
- Non-localhost warning still fires under `--no-ui`

## Deviations from Plan

None - plan executed exactly as written.

Minor test adjustment (not a plan deviation): headless tests seed a detection product so `/v1/snapshot` returns 200 (empty store correctly returns 404 per existing API contract); route presence checked via `url_path_for` / OpenAPI because FastAPI `_IncludedRouter` hides nested path attrs.

## Issues Encountered

None blocking. FastAPI route introspection required using named routes rather than walking `app.routes` path attributes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for wave 2: **07-02** ONNX/TensorRT export recipes (scripts + docs only)
- Ready for **07-03** extension stubs + desktop-gpu / safety docs that document `--profile desktop-gpu` and `--no-ui`
- No Jetson/TRT hardware required for 07-01 verification
- No stubs that block EDGE-02/EDGE-05 goals

## Self-Check: PASSED

- All key artifacts present on disk
- Commits `deb8301`, `d79cd48`, `29d28dc` present in git log
- Verification: `112 passed` across plan test suite

---
*Phase: 07-edge-profiles-extension-stubs*
*Completed: 2026-08-08*

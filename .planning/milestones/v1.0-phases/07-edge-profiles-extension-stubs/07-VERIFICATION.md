---
phase: 07-edge-profiles-extension-stubs
verified: 2026-08-08T17:24:40Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
re_verification: false
gaps: []
deferred: []
human_verification: []
---

# Phase 7: Edge Profiles & Extension Stubs — Verification Report

**Phase Goal:** Make multi-target deployment real and leave clean extension points for post-v1 capabilities.  
**Verified:** 2026-08-08T17:24:40Z  
**Status:** passed  
**Re-verification:** No — initial verification  

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Desktop GPU full pipeline is documented end-to-end as the primary maker path | ✓ VERIFIED | `docs/desktop-gpu.md` (132 lines): primary path, extras detect+depth, `--profile desktop-gpu`, USB/synthetic, cache, Live Preview + `/v1`, `--no-ui`. README links under "Primary maker path". `tests/test_desktop_docs.py` green. |
| 2 | Runtime profiles select model tiers/backends for desktop, Jetson-class, and CPU/lite | ✓ VERIFIED | YAML profiles + `profile_runtime()` → weights/device. Live: desktop→`yolo26s.pt`/`torch`/`cuda:0`; jetson→`yolo26n.pt`/`tensorrt`→device `cuda:0` (not TRT string); cpu-fallback→`yolo26n.pt`/`onnxruntime`→`cpu`. Wired in `cli.py` serve to YOLO/YOLOE/Depth workers. `tests/test_profile_application.py` green. |
| 3 | ONNX and/or TensorRT export recipes exist with on-device engine build notes | ✓ VERIFIED | `docs/export/*` (README, yolo26, yoloe, depth, jetson-packaging) + `scripts/export/export_yolo.py` with KNOWN_WEIGHTS basename allowlist. On-device / never-copy-engine language present. Zero `.engine` artifacts in tree. Tests `test_export_docs.py`, `test_export_script_cli.py` green; `--help` works without GPU. |
| 4 | Headless mode serves perception API without the UI | ✓ VERIFIED | `create_app(serve_ui=False)` + `sentry serve --no-ui` → `serve_ui=not no_ui`. `routes_preview.root_preview` returns JSON 404 when UI disabled; `/v1` and `/api` remain. `tests/test_headless_serve.py` + `tests/test_cli_serve.py` green. |
| 5 | Stubs/scaffolds exist for ROS2 bridge, multi-cam schema tests, and voice plugin no-op | ✓ VERIFIED | `Ros2PerceptionBridge` raises NotImplementedError on start/emit, no rclpy, not auto-registered. `VoiceNullSink` (`voice-null`) builtins + entry point; emit discards. Multi-cam: `tests/test_camera_id_multi.py` cam0/cam1 identity + empty id rejected. `tests/test_extensions_stubs.py` green. |
| 6 | Safety/privacy disclaimers and non-autonomy positioning are finalized in docs | ✓ VERIFIED | `docs/safety-and-privacy.md`: perception-only, no cmd_vel, free-space not interlock, localhost default, `allow_cloud: false`, non-localhost auth risk. README Safety section links. `tests/test_safety_docs.py` green. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sentry_ai/config/profile_runtime.py` | ProfileRuntime + device policy | ✓ VERIFIED | 105 lines; pure helpers; tensorrt honesty |
| `src/sentry_ai/config/profiles/{desktop-gpu,jetson,cpu-fallback}.yaml` | Tier/backend defaults | ✓ VERIFIED | s/n/n detector; torch/tensorrt/onnxruntime; allow_cloud false |
| `src/sentry_ai/models/cache.py` | tier_to_open_vocab_weight | ✓ VERIFIED | n→yoloe-26n-seg; s/m→yoloe-26s-seg |
| `src/sentry_ai/models/depth/mapping.py` | Small-only depth tier | ✓ VERIFIED | Base/Large raise ValueError |
| `src/sentry_ai/backend/protocols.py` | Non-raising probe_device | ✓ VERIFIED | CUDA optional; cpu-fallback available=True |
| `src/sentry_ai/cli.py` | Profile apply + --no-ui + banner | ✓ VERIFIED | Wired; honesty logs for tensorrt/onnxruntime |
| `src/sentry_ai/api/app.py` | serve_ui flag | ✓ VERIFIED | app.state.serve_ui |
| `src/sentry_ai/api/routes_preview.py` | Gate GET / when headless | ✓ VERIFIED | JSON 404 + v1 pointer |
| `docs/export/*` + `scripts/export/*` | Export recipes + CLI | ✓ VERIFIED | Substantive; offline path only |
| `docs/desktop-gpu.md` | Primary maker E2E | ✓ VERIFIED | Full pipeline steps |
| `docs/safety-and-privacy.md` | Non-autonomy + privacy | ✓ VERIFIED | Finalized language |
| `src/sentry_ai/extensions/ros2/bridge.py` | NotImplemented stub | ✓ VERIFIED | Importable; no rclpy |
| `src/sentry_ai/plugins/builtins.py` VoiceNullSink | Voice no-op sink | ✓ VERIFIED | + pyproject entry point |
| Phase 7 test modules | Contract coverage | ✓ VERIFIED | All present and green |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `cli.py` serve | `profile_runtime(cfg)` | worker construction | ✓ WIRED | `rt.detector_weights` / `rt.open_vocab_weights` / `rt.depth_model_id` / `rt.device` |
| preferred_backend tensorrt | live PyTorch device | `device_for_backend` + banner | ✓ WIRED | device=`cuda:0`; honesty note; never `"tensorrt"` device string |
| `cli.py --no-ui` | `create_app(serve_ui=False)` | `serve_ui=not no_ui` | ✓ WIRED | typer Option `--no-ui` |
| `root_preview` | `app.state.serve_ui` | 404 JSON when false | ✓ WIRED | routes_preview.py:313–321 |
| `export_yolo.py` | Ultralytics `model.export` | format onnx\|engine | ✓ WIRED | run_export; tests never call export |
| `export_yolo.py` | KNOWN_WEIGHTS | basename allowlist | ✓ WIRED | path traversal rejected |
| VoiceNullSink | registry + entry points | `voice-null` | ✓ WIRED | builtins, register_builtins, pyproject |
| README | desktop / export / safety docs | markdown links | ✓ WIRED | Primary path + Export + Safety sections |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| ProfileRuntime | detector/OV/depth weights + device | load_config(profile YAML) → tier maps | Yes — profile YAML tiers | ✓ FLOWING |
| serve workers | weights + device kwargs | profile_runtime(cfg) | Yes — not hardcoded empty | ✓ FLOWING |
| Headless GET / | serve_ui flag | create_app / CLI no_ui | Yes — boolean gate | ✓ FLOWING |
| Export CLI | weights basename | argv → validate_weights | Yes — allowlist (export itself offline/opt-in) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 7 test suite | `uv run pytest tests/test_profile_application.py tests/test_headless_serve.py tests/test_export_docs.py tests/test_export_script_cli.py tests/test_camera_id_multi.py tests/test_extensions_stubs.py tests/test_desktop_docs.py tests/test_safety_docs.py tests/test_cli_serve.py tests/test_backend_protocols.py -q` | **82 passed, 1 skipped** | ✓ PASS |
| Profile resolution live | `profile_runtime(load_config(...))` for 3 profiles | Correct weights/backends/devices | ✓ PASS |
| Export CLI help | `uv run python scripts/export/export_yolo.py --help` | argparse; onnx\|engine | ✓ PASS |
| serve --help --no-ui | `uv run sentry serve --help` | `--no-ui` documented | ✓ PASS |
| ROS2 stub | start/emit → NotImplementedError | Correct; no rclpy | ✓ PASS |
| VoiceNullSink | emit no-op + registry list | `voice-null` present; ros2 not auto-registered | ✓ PASS |
| No prebuilt engines | `find . -name '*.engine'` | 0 files | ✓ PASS |
| Default profile | `load_config()` | `cpu-fallback`, `allow_cloud=False` | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| N/A | No phase-declared `scripts/*/tests/probe-*.sh` | — | SKIP (not applicable) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| EDGE-01 | 07-03 | Documented desktop GPU development path runs full pipeline | ✓ SATISFIED | docs/desktop-gpu.md + README + tests |
| EDGE-02 | 07-01 | Runtime profiles desktop / Jetson / CPU lite | ✓ SATISFIED | YAML + profile_runtime + serve wiring + tests |
| EDGE-03 | 07-02 | ONNX/TensorRT export recipes for edge | ✓ SATISFIED | docs/export + scripts/export + tests |
| EDGE-04 | 07-03 | Multi-cam camera_id tests, ROS2 stub, voice no-op | ✓ SATISFIED | extensions + VoiceNullSink + tests |
| EDGE-05 | 07-01 | Headless perception API without web UI | ✓ SATISFIED | serve_ui / --no-ui + tests |

No orphaned Phase 7 requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TBD/FIXME/XXX/TODO debt markers in phase-touched code/docs | — | Clean |
| — | — | No empty stub handlers for headless/profile paths | — | Clean |

### Anti-Claims Check (must remain true)

| Claim forbidden | Status | Evidence |
|-----------------|--------|----------|
| Silent live TensorRT inference | ✓ CLEAN | jetson preferred_backend=tensorrt maps to cuda device + honesty log; docs say live path PyTorch |
| Prebuilt `.engine` in repo/wheel | ✓ CLEAN | 0 `.engine` files; docs forbid shipping |
| Full ROS2 product | ✓ CLEAN | NotImplemented stub; README "not production"; no rclpy dep |
| Unmeasured Pi dual-model FPS claim | ✓ CLEAN | jetson-packaging + yolo26 docs: "spatial awareness lite / best-effort"; "no unmeasured dual-model realtime FPS claim" |
| Robot control / cmd_vel product fields | ✓ CLEAN | safety + ROS2 README exclude cmd_vel/motors |

### Human Verification Required

None required for phase close. Success criteria are documentation contracts, profile wiring, export recipes, headless API, and stubs — all programmatically verified.

Optional maker smoke (out of band, not blocking):

1. Real CUDA desktop: `uv sync --extra detect --extra depth` then `sentry serve --profile desktop-gpu --source usb --device 0`
2. Real Jetson on-device: build engine via export recipe; measure FPS locally

### Gaps Summary

**None.** All six roadmap success criteria and EDGE-01..05 are verified in code and docs. Phase goal achieved.

### Disconfirmation Notes

- **Partial-req check:** EDGE-01 wording "path runs" is satisfied by documented runnable commands + profile wiring that selects desktop tiers; real GPU is not a CI gate and is not required by roadmap SC wording ("documented end-to-end").
- **Test honesty:** Doc tests are keyword/content asserts; manual read of docs confirms substantive E2E guidance, not keyword stuffing.
- **Default serve remains cpu-fallback** (no silent CUDA auto-switch) — intentional; desktop is opt-in via `--profile desktop-gpu`.

---

## Overall Recommendation

**Close Phase 7.** Multi-target deployment is real (profiles drive serve), export is honest recipes-only, headless API works, extension stubs are importable without overclaiming, and safety/privacy language is finalized.

_Verified: 2026-08-08T17:24:40Z_  
_Verifier: Claude (gsd-verifier)_

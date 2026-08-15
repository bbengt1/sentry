# Sentry AI

## What This Is

Sentry AI is an open-source, camera-only perception stack for maker robotics — vision-based spatial awareness and object recognition without LiDAR or radar. It runs local open-source models, exposes a realtime Live Preview with overlays and developer controls, and ships a versioned perception stream (depth, detections, free-space / obstacles, optional open-vocab) that robots consume via REST/WebSocket. Multi-target runtime profiles (desktop GPU, Jetson-class, CPU/lite), headless API mode, and extension stubs (ROS2, multi-cam `camera_id`, voice no-op) are included for post-v1 growth. Makers can apply an honest monocular metric scale via a Live Preview calibration wizard; free-space meters appear only when calibrated. After that first consent, an opt-in online path can refine the same scale without another Apply — draft, rejected, and fingerprint-mismatched depth never claim meters.

## Core Value

Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.

## Current State

**Shipped: v1.0 Camera-only perception MVP** (2026-08-09) + **v0.2 Edge Runtime** (2026-08-10) + **v0.3 Metric Depth Calibration UX** (2026-08-14)

### v1.0 (MVP)

- Installable `sentry-ai` / CLI `sentry` with one-command local start
- USB / file / synthetic / RTSP capture → keep-latest FrameBus → model workers
- Fixed-class YOLO26 + monocular DAV2 Small depth + free-space/obstacles
- Open-vocab YOLOE (default off); Live Preview + `/v1` perception stream
- Profiles: `desktop-gpu`, `jetson`, `cpu-fallback`; headless `--no-ui`

### v0.2 (Edge Runtime)

- **Live ONNX Runtime** fixed-class YOLO when preferred + allowlisted `.onnx` + `onnx` extra
- **Live TensorRT** fixed-class YOLO when preferred + on-device `.engine` + system/JetPack TensorRT
- Factory `build_detection_worker` with honest `backend_requested` / `backend_live` / `backend_reason`
- Soft-default sticky fallback + opt-in strict fail-closed (`fallback_to_torch` / `SENTRY_FALLBACK_TO_TORCH`)
- Depth + open-vocab remain PyTorch; dual-model measure-on-device docs
- Operator hub `docs/edge-serve.md`; AGPL lineage for derived ORT/TRT artifacts
- Jetson-free GitHub Actions + packaging hygiene
- ~9.3k LOC Python under `src/`; 10 plans across phases 8–12

**Audit at close:** passed (20/20 requirements) — see `milestones/v0.2-MILESTONE-AUDIT.md`.

### v0.3 (Metric Depth Calibration UX)

- Live Preview calibration wizard (known distance / optional height) — sample, fit, Apply / Cancel / Clear
- `CalibrationState.apply_map` after `DepthAnythingWorker.process` and before `PerceptionStore.set_depth`
- Honest `depth_kind=metric_calibrated` + `unit="m"` only when applied and valid
- Free-space `units="m"` iff calibrated (absolute 1.5/3.0 m cuts); ordinal otherwise
- Per-`camera_id` YAML persist; fingerprint refuse; re-apply on `sentry serve`
- Operator hub `docs/calibration.md`; synthetic CI inventory; package stays 0.1.0
- 6 phases / 12 plans (13–18)

**Audit at close:** passed (19/19 requirements) — see `milestones/v0.3-MILESTONE-AUDIT.md`.

## Requirements

### Validated

- ✓ Camera-only spatial awareness (monocular depth + free-space/obstacles) — v1.0
- ✓ Off-the-shelf cameras (USB, network/IP, file, synthetic) — v1.0
- ✓ Local development workflow with live camera or synthetic sources — v1.0
- ✓ Realtime web Live Preview with video + overlays — v1.0
- ✓ Interactive developer controls (stages, thresholds, telemetry) — v1.0
- ✓ Local open-source models only on the core path — v1.0
- ✓ Fixed-class detection + optional open-vocabulary queries — v1.0
- ✓ Perception stream API for robots (no motor commands) — v1.0
- ✓ Single-camera pipeline with multi-cam `camera_id` extension hooks — v1.0
- ✓ Multi-target runtime: desktop GPU + Jetson/CPU profiles + export recipes — v1.0
- ✓ Extensible architecture stubs (ROS2 bridge, voice no-op, plugins) — v1.0
- ✓ Live ONNX Runtime path for fixed-class YOLO (profile-selected) — v0.2
- ✓ Live TensorRT path for fixed-class YOLO on NVIDIA / Jetson-class — v0.2
- ✓ Profiles wire preferred_backend to real loaders (not advisory-only) — v0.2
- ✓ Honest sticky soft/strict fallback when ORT/TRT artifact/dep missing — v0.2
- ✓ Edge docs: export → onnx/engine → serve hub + Jetson packaging honesty — v0.2
- ✓ CI-safe tests without Jetson hardware; GHA Jetson-free locks — v0.2
- ✓ Metric depth calibration UX via Live Preview wizard (known distance / height) — v0.3
- ✓ Persist and re-apply per-camera calibration at serve (fingerprint-gated YAML) — v0.3
- ✓ Honest `depth_kind` / unit labeling: relative by default; metric only when calibrated — v0.3
- ✓ Free-space / obstacle near-field distances use metric scale when calibrated — v0.3
- ✓ Clear uncalibrated honesty in UI, snapshot, and `/v1` (never label relative as meters) — v0.3
- ✓ Docs for calibration flow; automated tests without physical hardware — v0.3

### Active

- [ ] Opt-in online re-calibration after first consented metric scale (default off)
- [ ] First `metric_calibrated` still requires explicit Apply or matching persist `try_reapply`
- [ ] Online sampler stays draft-only; WIZ-04 holds until apply()/apply_params of a passed fit
- [ ] Gated auto-commit via apply_params (online + already applied + fit ok + residual + fingerprints_match)
- [ ] Cancel/Clear unchanged; disable-online ≠ Clear; auto-commit session-only by default
- [ ] Status distinguishes online_off / online_draft / auto_committed / rejected; docs + synthetic CI

### Out of Scope

- LiDAR / radar / ultrasonic as required sensors — camera-only product thesis
- Full robot control / motion planning — consumers own control
- Dense SLAM / full 3D mapping — depth + obstacles only in core product
- Multi-camera fusion (runtime) — single active source; schema hooks only *(revisit as Active if prioritized)*
- Cloud-only or proprietary model dependency — local OSS required
- Voice / scene chat as primary UI — stubs only in v1.0
- Commercial fleet SaaS / mandatory cloud camera upload
- FSD / autonomous vehicle claims — hobby monocular ≠ vehicle-grade
- Prebuilt multi-SKU TensorRT engines in the wheel/repo — on-device build only
- Continuous open-vocab + TRT + DAV2 as first-class dual-model claim

## Context

**Problem:** Maker robotics often depends on expensive depth sensors. There was no approachable OSS camera-only stack with off-the-shelf cameras, local models, interactive dev UI, and a clean robot API.

**Users:** Maker / hobbyist roboticists, students, small teams.

**Shipped stack:** Python 3.11, FastAPI, Pydantic 2, OpenCV capture (incl. Continuity uniqueID on macOS), Ultralytics YOLO26/YOLOE, HF Depth Anything V2 Small, static Live Preview with calibration wizard, profile-driven serve with live torch/ORT/TRT fixed-class detection, honest monocular metric scale via DepthLoop `apply_map`, free-space meters iff calibrated, per-camera YAML persist.

**Known residual tech debt (non-blocking):** Nyquist VALIDATION.md frontmatter hygiene (`wave_0_complete: false`); residual live-load honesty after construct claim; hardware ORT/TRT E2E is operator checklist (see v0.2 audit); phases 14–18 SUMMARY-only (see v0.3 audit).

## Constraints

- **Sensors**: Cameras only for spatial awareness — no LiDAR/radar requirement
- **Models**: Local open-source models required; cloud optional only as non-default extension
- **Cameras**: USB UVC, RTSP/network, file/synthetic
- **Runtime**: Multi-target — desktop GPU primary path; Jetson/CPU profiles + export recipes
- **Interface**: Web Live Preview for developers; headless API for robots
- **Architecture**: Plugin / extension-friendly
- **License**: Apache-2.0 application code; third-party model licenses documented
- **Privacy**: On-device default; localhost bind; no mandatory upload

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Camera-only perception (no LiDAR/radar) | Core product thesis | ✓ Good — v1.0 |
| Spatial v1 = depth + obstacles, not full SLAM | Ship useful signal without mapping complexity | ✓ Good — v1.0 |
| Single camera first | v1 complexity; multi-cam hooks only | ✓ Good — v1.0 |
| Static Live Preview (not full React rewrite) | Ship overlays/controls faster | ✓ Good — v1.0 |
| Live overlays + controls (not chat-first) | Developer tooling first | ✓ Good — v1.0 |
| Fixed-class + open-vocab detection | Reliability + flexible queries | ✓ Good — v1.0 |
| Perception stream only (no robot control) | Clean safety boundary | ✓ Good — v1.0 |
| Multi-target: desktop + edge profiles | Dev ergonomics + deploy path | ✓ Good — v1.0 recipes; **v0.2 live ORT/TRT** |
| Local OSS models only for core path | Offline, no vendor lock-in | ✓ Good — v1.0 |
| Extensible plugin architecture | Voice/ROS2/multi-cam without rewrite | ✓ Good — stubs shipped |
| Depth honesty via `depth_kind` | Never sell relative as meters | ✓ Good — v1.0; **v0.3 metric_calibrated** |
| CUDA request falls back to MPS/CPU | Maker machines without CUDA | ✓ Good — post-v1 fix included |
| Factory sole author of backend_live | Prevent status lies | ✓ Good — v0.2 |
| Live ORT via Ultralytics YOLO(*.onnx) | Match Detection contract without custom decoder | ✓ Good — v0.2 |
| Live TRT via system TensorRT (no pip pin) | JetPack reality; multi-SKU engines unsafe | ✓ Good — v0.2 |
| Soft-default sticky fallback + opt-in strict | Maker ergonomics vs fail-closed deploy | ✓ Good — v0.2 |
| Depth/OV stay torch this milestone | Dual-model VRAM + scope control | ✓ Good — v0.2 |
| Zero new pip deps for calibration | Extend NumPy + existing stack | ✓ Good — v0.3 |
| DepthLoop sole `apply_map` site | Single truth; no double-scale | ✓ Good — v0.3 |
| `metric_calibrated` + `m` only when applied+valid | Honesty first | ✓ Good — v0.3 |
| Free-space meters iff calibrated (1.5/3.0 m cuts) | Never label-only ordinal flip | ✓ Good — v0.3 |
| Cancel = clear_draft; Clear deletes YAML | Wizard vs persist semantics | ✓ Good — v0.3 |
| STACK YAML persist + fingerprint refuse | Restart-safe without silent mismatch | ✓ Good — v0.3 |
| Synthetic CI only (no room / Jetson / CUDA) | Hardware-free default GHA | ✓ Good — v0.3 |
| Do not bump pyproject 0.1.0 | Archive is planning-only | ✓ Good — v0.3 |
| Consent-once gated auto-commit (not silent first scale) | First meters still need Apply / persist `try_reapply` | Locked — v0.4 |
| Online mode default off | Opt-in; disable-online ≠ Clear | Locked — v0.4 |
| Auto-commit via `apply_params` only when already applied + fit ok + residual + fingerprints_match | Same reject gates; DepthLoop sole `apply_map` | Locked — v0.4 |
| Sticky scale; throttle / N-sample window | No per-frame unguarded refit | Locked — v0.4 |
| Auto-commit session-only by default | YAML only on explicit save / persist:true / documented opt-in | Locked — v0.4 |

## Current Milestone: v0.4 Online Re-calibration (CAL-F03)

**Goal:** After a maker has consented to metric scale (wizard Apply or matching persist re-apply), Sentry can continuously refine that scale online without another Apply click — without ever labeling draft, rejected, or fingerprint-mismatched depth as meters.

**Target features:**
- Opt-in online mode (default off)
- First `metric_calibrated` still requires explicit Apply or matching persist `try_reapply`
- Online sampler writes draft only (WIZ-04 holds until apply()/apply_params of a passed fit)
- Reuse v0.3 fit/reject gates; `ok=False` never becomes applied
- Gated auto-commit via `apply_params` when online on AND already applied AND fit ok AND residual gate AND fingerprints_match
- DepthLoop remains sole `apply_map`; reset free-space smoother on auto-commit like Apply
- Sticky scale — throttle / N-sample window; no per-frame unguarded refit
- Cancel = draft only; Clear = applied + YAML; disable-online ≠ Clear
- Auto-commit is session-only by default (YAML only on explicit save / persist:true / documented opt-in)
- Status distinguishes `online_off` / `online_draft` / `auto_committed` / `rejected` from `depth.kind` and persist status
- Docs + synthetic CI; zero new deps

**Out of this milestone (deferred):**
- Full chessboard / photogrammetry intrinsic suite (CAL-F01)
- Required ArUco/AprilTag marker kit (CAL-F02)
- Stereo / multi-view metric depth (CAL-F04)
- Production ROS2 metric TF / frame package (PLAT-F01)
- Multi-camera fusion with shared metric world frame (PLAT-F02)
- Live ORT/TRT for depth models (PLAT-F03)

---
*Last updated: 2026-08-15 after starting v0.4 milestone*

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

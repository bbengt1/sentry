# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Operator calibration guide (`docs/calibration.md`): Live Preview wizard, STACK YAML persist, honesty triad (v0.3 / OPS-02)

### Changed

- Document live fixed-class ORT/TRT serve conditions (preferred + artifact + dep)
- Root/desktop/export hub honesty: retire “export-only / still PyTorch live” language
- Add `docs/edge-serve.md` numbered export → place artifact → `sentry serve` path
- AGPL lineage for YOLO-derived `.onnx` / `.engine` in `THIRD_PARTY_MODELS` (see EDGE-DOC-02)
- Hub honesty: free-space `units="m"` only when `metric_calibrated` + 1.5/3.0 m cuts; persist path is `$SENTRY_MODEL_CACHE/calibration/{safe_id}.yaml`

### Known limitations

- Real engine load remains on-device / manual; default CI is mock-only

## [0.1.0] — 2026-08-09

First public release of the Sentry AI camera-only perception stack (feature
milestone “v1.0” in planning terms; package version **0.1.0**).

### Added

- Installable package `sentry-ai` with CLI `sentry` (`health`, `cameras`, `smoke`, `serve`)
- Camera sources: synthetic, USB (OpenCV), file, RTSP (best-effort)
- Keep-latest `FrameBus` + `CaptureLoop` with reconnect status
- Live Preview: MJPEG overlays, status telemetry, stage toggles, thresholds
- Fixed-class detection (YOLO26) via optional `detect` extra
- Open-vocabulary detection (YOLOE) on-demand / continuous lower rate
- Monocular depth (Depth Anything V2 Small) via optional `depth` extra
- Free-space / obstacle Spatial Post from depth (CPU, ordinal nearness)
- Unified `PerceptionFrame` assembler; `GET /v1/snapshot` and `WS /v1/stream`
- Control plane: `GET/PATCH /api/pipeline/config`, detection/depth/open-vocab configs
- Runtime profiles: `desktop-gpu`, `jetson`, `cpu-fallback`
- Headless serve (`--no-ui`) for API-only consumers
- ONNX/TensorRT **export recipes** and `scripts/export/export_yolo.py`
- Extension stubs: multi-cam `camera_id` tests, ROS2 bridge scaffold, voice no-op sink
- Docs: desktop GPU path, camera sources, safety/privacy, architecture, API, CLI
- Model license documentation (`THIRD_PARTY_MODELS.md`)

### Safety / honesty

- Perception-only API boundary (no motor/control fields)
- Relative depth never labeled as meters
- Free-space is not a safety interlock; consumers must honor stale/TTL
- Default bind `127.0.0.1`; LAN bind is opt-in without authentication
- CUDA device policy falls back to MPS/CPU when CUDA unavailable

### Known limitations

- Live inference is PyTorch; TensorRT/ONNX are export paths, not silent live backends
- Single active camera (multi-cam fusion deferred)
- ROS2 / voice are stubs only
- Residual operator UAT for physical USB/RTSP and real-weight visuals (CI is mock-safe)

[0.1.0]: https://github.com/bbengt1/sentry/releases/tag/v0.1.0

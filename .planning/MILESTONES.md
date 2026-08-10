# Milestones

## v0.2 Edge Runtime (Shipped: 2026-08-10)

**Phases completed:** 5 phases, 10 plans, 26 tasks  
**Audit:** passed (20/20 requirements; no critical gaps) — [v0.2-MILESTONE-AUDIT.md](milestones/v0.2-MILESTONE-AUDIT.md)  
**Known deferred items at close:** Nyquist VALIDATION.md frontmatter hygiene; residual live-load honesty edge case; hardware ORT/TRT E2E remains operator checklist (see audit tech_debt)

**Stats:** ~9.3k LOC Python (`src/`); timeline 2026-08-09 → 2026-08-10

**Key accomplishments:**

- Serve-time `build_detection_worker` factory with allowlisted artifact paths and honest `backend_requested` / `backend_live` / `backend_reason`
- Live fixed-class YOLO via **ONNX Runtime** when preferred + `.onnx` + `onnx` extra (Detection contract parity under mocks)
- Live fixed-class YOLO via **TensorRT** when preferred + on-device `.engine` + system/JetPack TensorRT (no pip pin, no multi-SKU engines in wheel)
- Soft-default sticky fallback + opt-in strict fail-closed (`fallback_to_torch` / `SENTRY_FALLBACK_TO_TORCH`); reason logged once
- Depth and open-vocab stay PyTorch; dual-model measure-on-device docs; continuous OV+TRT+DAV2 not first-class
- Operator hub `docs/edge-serve.md` (export → place → serve) + AGPL lineage for derived `.onnx`/`.engine`
- Jetson-free GitHub Actions locks + packaging hygiene (`*.engine`/`*.onnx` gitignored)

---

## v1.0 Camera-only perception MVP (Shipped: 2026-08-09)

**Phases completed:** 7 phases, 18 plans, 52 tasks  
**Audit:** tech_debt (46/46 requirements; no critical gaps) — [v1.0-MILESTONE-AUDIT.md](milestones/v1.0-MILESTONE-AUDIT.md)  
**Known deferred items at close:** 3 residual operator UAT verification notes (phases 02–04 `human_needed`) + non-critical integration polish (see STATE.md Deferred Items)

**Stats:** ~7.4k LOC Python (`src/`); timeline 2026-08-07 → 2026-08-09

**Key accomplishments:**

- Installable `sentry-ai` package with Typer CLI health/smoke skeleton, Wave 0 pytest stubs, and CI — FOUND-01 foundation for all later plans.
- Pydantic v2 Frame/PerceptionFrame contracts with DepthKind honesty validators, three runtime profile YAMLs, and MODEL-01 local-only defaults.
- Hybrid plugin registry with synthetic/noop/null builtins, InferenceBackend/NullBackend stubs, THIRD_PARTY_MODELS.md Apache-default licenses, and full `sentry smoke` PerceptionFrame validation.
- Runtime ImageFrame + OpenCV/synthetic sources delivering CAM-01/02/03 at the adapter layer without numpy on Pydantic Frame
- Depth-1 keep-latest FrameBus with drop/FPS metrics plus daemon CaptureLoop reconnect spine so FastAPI only subscribes (CAM-05/CAM-06)
- Localhost FastAPI MJPEG Live Preview with status pill, RTSP OpenCV plugin, and `sentry serve` defaulting to 127.0.0.1
- YOLO26 ModelWorker + DetectionLoop + PerceptionStore with Sentry-owned model cache and CI-safe mocks — DET-01/DET-02/MODEL-02 at the pipeline layer.
- Server-side OpenCV overlays on MJPEG, GET /api/snapshot PerceptionFrame parity, runtime conf PATCH, status telemetry, Live Preview controls, and sentry serve DetectionLoop wiring — DET-03/DET-04 closed.
- Injectable DepthAnythingWorker + DepthLoop publish keep-latest DepthProduct into PerceptionStore with honest DepthKind/unit; HF cache under SENTRY_MODEL_CACHE; CI never downloads weights.
- Snapshot DepthPayload + completeness, server-side TURBO MJPEG blend, honest relative/metric labels, depth latency telemetry, and DepthLoop wired into sentry serve.
- Near-field percentile-band free-space from synthetic monocular depth with morphology+EMA smoothing, FreeSpaceProduct on PerceptionStore, FreeSpaceLoop daemon, and pure draw_free_space overlay helper — CI-safe without DAV2/HF.
- Expanded FreeSpacePayload with ObstacleCue wire shape, single assemble_perception_frame merge (completeness + TTL/stale ages/stats), and /api/snapshot refactored to that assembler only.
- Shipped versioned perception API (`GET /v1/snapshot`, `WS /v1/stream` ~10 Hz keep-latest), MJPEG free-space overlay from the same PerceptionStore, FreeSpaceLoop always-on in serve, and STALE/incomplete Live Preview honesty with API-05 denylist coverage.
- Thread-safe stage enable/disable + free-space near/mid cutoffs via GET/PATCH `/api/pipeline/config`, loop enable gates that skip compute without teardown, and Live Preview stage toggles with stage FPS telemetry.
- Open-vocabulary YOLOE path with separate store product, assemble merge + source tags, dual-color overlays, and Live Preview prompt UX — default off, never blocking fixed-class.
- Runtime profiles drive detector/OV/depth tiers and honest device policy at serve; headless `--no-ui` serves perception APIs without Live Preview HTML
- ONNX/TensorRT export recipes and Jetson packaging notes as docs + a safe Ultralytics CLI wrapper — no live TRT runtime, no prebuilt engines, no Jetson in CI
- Multi-cam camera_id identity tests, importable ROS2 NotImplemented bridge (no rclpy), VoiceNullSink no-op, plus desktop GPU primary-path and safety/privacy release docs

---

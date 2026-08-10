# Phase 9: Live ORT Fixed-Class YOLO - Context

**Gathered:** 2026-08-09  
**Status:** Ready for planning  
**Source:** ROADMAP + REQUIREMENTS + Phase 8 shipped factory (YOLO plan-phase)

<domain>
## Phase Boundary

Makers can run **fixed-class YOLO live via ONNX Runtime** when the profile prefers `onnxruntime` and a valid `.onnx` artifact is present — with the **same Detection wire contract** as PyTorch.

**In scope:**
- Live ORT path when preferred=onnxruntime + `.onnx` present + onnxruntime available (ORT-01)
- Same Detection contract: class, conf, bbox_xyxy, source=fixed (ORT-02)
- Optional `onnx` extra documented; CI does not require GPU ORT (ORT-03)
- Golden/parity tests with mocks/fixtures without Jetson (ORT-04)
- Factory: replace soft-stub for ORT with real live path when conditions met
- Honest fallback: if artifact/deps missing → keep Phase 8 soft-stub (torch + reason), not silent ORT claim
- `backend_live=onnxruntime` only when actually running ORT

**Out of scope:**
- Live TensorRT (Phase 10)
- Sticky fallback policy overhaul beyond current soft reasons (Phase 11)
- Live ORT for depth / YOLOE
- Custom ORT InferenceSession + hand-written YOLO26 decoder (prefer Ultralytics-native)
- Jetson-specific GPU ORT wheels as required CI
- Dual-model FPS claims

</domain>

<decisions>
## Implementation Decisions

### Locked from product / research
- Ultralytics-native: `YOLO("*.onnx")` + existing `predict` + `results_to_detections` preferred over custom ORT
- Optional `onnx` extra: `onnxruntime>=1.20,<1.29` (prefer 1.28.x)
- No `tensorrt` pip extra this phase
- Factory remains sole author of `backend_live`
- Phase 8 spine freeze continues: DetectionLoop / bus / store / `/v1` unchanged except worker impl
- Artifact resolution via existing `resolve_detector_artifact` + env `SENTRY_DETECTOR_ONNX`

### From Phase 8 shipped
- `WorkerBuild` + `build_detection_worker(rt)`
- Soft reasons: `ort_loader_not_implemented`, `path_rejected`, etc.
- Status/banner honesty fields already present

### Claude's Discretion
- Whether live ORT reuses `YoloDetectionWorker` with onnx weights path or a thin wrapper class
- How conf/device map for ORT (cpu default for cpu-fallback profile)
- Whether missing onnxruntime ImportError soft-falls to torch with reason `ort_dep_missing`
- Exact golden fixture strategy (inject fake YOLO model that claims onnx backend)

</decisions>

<canonical_refs>
## Canonical References

- `.planning/PROJECT.md` — v0.2 Edge Runtime
- `.planning/REQUIREMENTS.md` — ORT-01..04
- `.planning/ROADMAP.md` — Phase 9
- `.planning/research/STACK.md`, `ARCHITECTURE.md`, `SUMMARY.md`
- `.planning/phases/08-backend-selection-honesty/08-01-SUMMARY.md`, `08-VERIFICATION.md`
- `src/sentry_ai/models/detection/factory.py`
- `src/sentry_ai/models/detection/yolo_worker.py`
- `src/sentry_ai/models/detection/mapping.py`
- `src/sentry_ai/config/artifact_paths.py`
- `scripts/export/export_yolo.py`, `docs/export/`
- `pyproject.toml` extras

</canonical_refs>

<specifics>
## Plans (roadmap)

1. **09-01** — Live Ultralytics-native ORT worker path + `onnx` extra  
2. **09-02** — Detection parity / golden tests (CPU ORT or mocks)

Success: `preferred_backend=onnxruntime` + valid `.onnx` + onnxruntime installed → `backend_live=onnxruntime` and detections flow through DetectionLoop; parity tests green without Jetson.

</specifics>

<deferred>
## Deferred

- Live TRT `.engine` (Phase 10)
- Sticky thrash-free fallback modes (Phase 11)
- onnxruntime-gpu as separate exclusive extra (docs only ok)
- YOLOE ORT

</deferred>

---

*Phase: 09-live-ort-fixed-class-yolo*  
*Context gathered: 2026-08-09 via YOLO plan-phase*

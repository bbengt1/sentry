# Requirements: Sentry AI — v0.2 Edge Runtime

**Defined:** 2026-08-09  
**Milestone:** v0.2 Edge Runtime  
**Core value:** Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.

**Milestone goal:** Fixed-class YOLO can run **live** on ONNX Runtime and TensorRT (profile-selected) on desktop and Jetson-class NVIDIA — not export recipes alone. Depth and open-vocab stay PyTorch this milestone.

## v0.2 Requirements

### Backend selection & honesty

- [x] **BACK-01**: Runtime profile `preferred_backend` selects the fixed-class detection **loader** (torch / onnxruntime / tensorrt), not device-policy logs alone
- [x] **BACK-02**: Status / serve banner expose both `backend_requested` and `backend_live` (no silent backend lies)
- [ ] **BACK-03**: When preferred ORT/TRT artifact or dependency is missing, behavior is **documented and sticky** (fail-closed or explicit torch fallback with reason logged once — never thrash every frame)
- [x] **BACK-04**: Artifact paths for `.onnx` / `.engine` resolve from config/env/cache with a safe allowlist (no arbitrary path traversal)

### Live ONNX Runtime (fixed-class YOLO)

- [x] **ORT-01**: Fixed-class YOLO can run live via ONNX Runtime when profile prefers `onnxruntime` and a valid `.onnx` artifact is present
- [ ] **ORT-02**: ORT path produces the same `Detection` wire contract (class, conf, bbox_xyxy, source=fixed) as the PyTorch path
- [x] **ORT-03**: Optional `onnx` (or equivalent) extra documents install; CI does not require GPU ORT
- [ ] **ORT-04**: Golden/parity tests (mock session or fixture) prove postprocess mapping without Jetson hardware

### Live TensorRT (fixed-class YOLO)

- [ ] **TRT-01**: Fixed-class YOLO can run live via TensorRT when profile prefers `tensorrt` and a valid on-device `.engine` is present
- [ ] **TRT-02**: Docs require **on-device** engine build; project does not ship multi-SKU prebuilt engines in the wheel
- [ ] **TRT-03**: Jetson-class packaging notes cover JetPack/system TensorRT (no generic `tensorrt` pip pin as required app dep)
- [ ] **TRT-04**: TRT path maps results into the same `Detection` contract; conf still adjustable at runtime when supported

### Integration (existing spine)

- [x] **EDGE-RT-01**: `DetectionLoop` / FrameBus / PerceptionStore / `/v1` remain the perception spine — no bus redesign
- [x] **EDGE-RT-02**: `sentry serve` constructs detection worker via a factory from `profile_runtime` (torch worker preserved for `.pt`)
- [x] **EDGE-RT-03**: Desktop GPU path remains first-class with torch default; jetson/cpu-fallback profiles can select ORT/TRT honestly
- [ ] **EDGE-RT-04**: Depth and open-vocab continue on existing PyTorch paths this milestone (no live ORT/TRT for them)

### Docs, CI, safety

- [ ] **EDGE-DOC-01**: Jetson/desktop edge serve docs cover export → engine/onnx → `sentry serve --profile … --no-ui` (or with UI)
- [ ] **EDGE-DOC-02**: AGPL Ultralytics remains documented for ORT/TRT artifacts derived from YOLO weights
- [ ] **EDGE-CI-01**: Unit tests cover backend selection, missing-artifact honesty, and factory wiring without NVIDIA Jetson in CI
- [ ] **EDGE-CI-02**: No required Jetson or TensorRT GPU in GitHub Actions

## Future Requirements (deferred)

- Live ORT/TRT for depth / YOLOE  
- Metric depth + calibration UX  
- Production ROS2 package  
- Multi-camera fusion  
- Pi dual-model published FPS as first-class claim  
- OpenVINO first-class backend  

## Out of Scope (v0.2)

| Item | Reason |
|------|--------|
| Live ORT/TRT depth or open-vocab | Scope lock — YOLO fixed-class only |
| Prebuilt `.engine` in repo/wheel | SKU non-portability |
| Full InferenceBackend rewrite of free-space/UI | Detection worker factory is enough |
| Robot control / FSD claims | Product thesis unchanged |
| Mandatory cloud inference | Local OSS only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BACK-01 | Phase 8 | Complete |
| BACK-02 | Phase 8 | Complete |
| BACK-03 | Phase 11 | Pending |
| BACK-04 | Phase 8 | Complete |
| ORT-01 | Phase 9 | Complete |
| ORT-02 | Phase 9 | Pending |
| ORT-03 | Phase 9 | Complete |
| ORT-04 | Phase 9 | Pending |
| TRT-01 | Phase 10 | Pending |
| TRT-02 | Phase 10 | Pending |
| TRT-03 | Phase 10 | Pending |
| TRT-04 | Phase 10 | Pending |
| EDGE-RT-01 | Phase 8 | Complete |
| EDGE-RT-02 | Phase 8 | Complete |
| EDGE-RT-03 | Phase 8 | Complete |
| EDGE-RT-04 | Phase 11 | Pending |
| EDGE-DOC-01 | Phase 12 | Pending |
| EDGE-DOC-02 | Phase 12 | Pending |
| EDGE-CI-01 | Phase 12 | Pending |
| EDGE-CI-02 | Phase 12 | Pending |

---
*Requirements defined 2026-08-09 for milestone v0.2 Edge Runtime*  
*Traceability mapped 2026-08-09 — phases 8–12*

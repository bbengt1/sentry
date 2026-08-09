# Project Research Summary

**Project:** Sentry AI  
**Domain:** Live edge inference (ORT + TensorRT) for fixed-class YOLO on an existing camera-only perception stack  
**Milestone:** v0.2 Edge Runtime  
**Researched:** 2026-08-09  
**Confidence:** HIGH (code-verified plug-in surface + package pins); MEDIUM (JetPack/ORT wheel matrix, YOLO26 custom-decode effort if ever needed)

## Executive Summary

v0.2 turns Sentry’s **export-recipe honesty** into **live edge backends** for fixed-class YOLO only. v1.0 already ships FrameBus → DetectionLoop → Ultralytics PyTorch worker → PerceptionStore, plus profiles that *name* `tensorrt` / `onnxruntime` but still load `.pt`. Experts in this space (Ultralytics AutoBackend, Isaac ROS encode→infer→decode, Jetson on-device engines) converge on the same product move: **swap the detector loader at construction time**, keep the loop/API frozen, and make **preferred vs live backend** impossible to lie about.

**Recommended approach:** Keep Ultralytics `YOLO(weights).predict()` as the live ORT/TRT path (`YOLO("*.onnx")` / `YOLO("*.engine")` via AutoBackend). Add an `onnx` extra (`onnxruntime>=1.20,<1.29`); **never** add a project `tensorrt` pip extra (system/JetPack only). Introduce a serve-time factory (`build_detection_worker`) + artifact path resolution + sticky fallback so `preferred_backend` selects real loaders. Depth (DAV2) and open-vocab (YOLOE) stay PyTorch this milestone. Desktop GPU remains torch-default; Jetson is first-class for on-device TRT; Pi/CPU is best-effort ORT with no dual-model FPS claims.

**Key risks and mitigations:** (1) **Silent backend lies** — report `backend_requested` vs `backend_live` + reason; sticky resolve once at worker start. (2) **Engine SKU non-portability** — on-device build only; no multi-SKU `.engine` in git/wheel/releases. (3) **JetPack matrix soup** — document verify-on-device; no generic PyPI `onnxruntime-gpu` on Jetson. (4) **Postprocess drift** — prefer Ultralytics predict over custom ORT decode in v0.2. (5) **Dual-model VRAM** (TRT YOLO + torch depth) — isolate loaders first, then measure; open-vocab stays off. (6) **CI without GPU** — mocks + selection/fallback contract tests; no Jetson in GHA. (7) **AGPL not laundered by export** — document `.onnx`/`.engine` lineage same as `.pt`.

Full dimension docs: [STACK.md](./STACK.md) · [FEATURES.md](./FEATURES.md) · [ARCHITECTURE.md](./ARCHITECTURE.md) · [PITFALLS.md](./PITFALLS.md)

---

## Key Findings

### Recommended Stack (additions only)

Condensed from [STACK.md](./STACK.md). Core v1.0 stack (Python 3.11, FastAPI, Ultralytics detect extra, DAV2 depth) **unchanged**.

| Addition | Pin / rule | Role |
|----------|------------|------|
| **`onnx` extra** | `onnxruntime>=1.20,<1.29` (prefer 1.28.x) | Live CPU ORT for `preferred_backend=onnxruntime` |
| **`onnxruntime-gpu`** | Same band; **manual/desktop only** | Optional CUDA EP; not co-extra with CPU ORT; **not** for Jetson PyPI |
| **System TensorRT** | JetPack / host install | Deserialize Ultralytics `.engine`; **no** `tensorrt` in `pyproject` extras |
| **Ultralytics AutoBackend** | via existing `detect` extra (≥8.4.33,<9) | `*.onnx` → ONNXBackend; `*.engine` → TensorRTBackend |
| **Artifacts** | `yolo26{n,s}.onnx` / `.engine` on device | Export offline via `scripts/export/export_yolo.py` |

**Opinionated stack decision (roadmap-binding):**  
**Live path = Ultralytics-native** (`YOLO("model.onnx|engine")` + existing `results_to_detections`). Do **not** build a parallel custom `InferenceSession` + YOLO26 head decoder in v0.2 unless Ultralytics path is proven blocked. Custom `OrtBackend`/`TrtBackend` under `InferenceBackend` remains a **future slim-edge** option; Architecture’s encode→infer→decode split still informs factory boundaries and tests.

**Do not add:** `tensorrt` / `tensorrt-cu*` extras, `torch-tensorrt`, OpenVINO live, Triton as required runtime, live ORT/TRT for depth or YOLOE, prebuilt multi-SKU engines in the wheel.

**Install matrix (makers):**

```bash
# CI / CPU ORT
uv sync --extra dev --extra detect --extra onnx

# Desktop torch (unchanged primary)
uv sync --extra dev --extra detect --extra depth

# Jetson TRT: detect + JetPack system TRT; engines built on board
```

### Expected Features

Condensed from [FEATURES.md](./FEATURES.md).

**Must have (table stakes):**

- **Profile-selected live backend** — `preferred_backend` drives real loaders (`torch` | `onnxruntime` | `tensorrt`), not export hints
- **Live fixed-class YOLO on ORT** — load `.onnx`, same `Detection` schema
- **Live fixed-class YOLO on TensorRT** — on-device `.engine`; NVIDIA desktop + Jetson first-class
- **Same Detection / overlays / `/v1`** — robots and Live Preview backend-agnostic
- **Honest missing-artifact & missing-deps behavior** — never silent torch under a TRT/ORT label
- **Torch remains desktop default** — `desktop-gpu` stays `preferred_backend: torch`
- **Depth stays PyTorch; open-vocab stays PyTorch on-demand** — scope lock
- **FrameBus keep-latest preserved** — no queue redesign; slower edge = higher drops, expected
- **CI without Jetson** — mock loaders; selection + fallback matrix tests
- **Jetson docs: build engine → serve** — close EDGE-03 export→live loop
- **Backend identity in telemetry** — `backend_live` (and requested) visible to operators

**Should have (differentiators):**

- One serve path, multiple backends (profile switch, not pipeline rewrite)
- Profiles as real deployment units (`jetson` / `cpu-fallback` executable)
- Export → live continuity (same artifacts from `export_yolo.py`)
- Mockable selection for contributors without NVIDIA hardware
- Operator-visible backend in stream/status metadata

**Defer (v0.3+ / never as core this milestone):**

| Defer | Why |
|-------|-----|
| Live ORT/TRT for depth (DAV2) | Separate export + correctness project |
| Live ORT/TRT for YOLOE | Dual continuous models unmeasured; export experimental |
| Prebuilt multi-SKU engines in releases | Non-portable |
| OpenVINO / NCNN / CoreML live | Extra surface; enum-only today |
| Auto-export / engine build at serve start | Multi-minute hang; non-deterministic |
| Pi dual-model published FPS tables | Unmeasured liability |
| Drop Ultralytics on edge in week one | Postprocess drift + schedule risk |

**Honest fallback matrix (product policy seed):**

| Requested | Missing | Default behavior |
|-----------|---------|------------------|
| `onnxruntime` / `tensorrt` | artifact or runtime | Hard-fail when strict; soft mode: loud torch fallback + `live_backend=torch` + reason |
| `tensorrt` | CUDA | Hard-fail (no CPU TRT fiction) |
| Mid-frame infer error | — | Existing loop: empty dets + `error`; **do not** re-resolve backend per frame |

### Architecture Plug-in

Condensed from [ARCHITECTURE.md](./ARCHITECTURE.md).

**Thesis:** Plug ORT/TRT under **ModelWorker** at **serve construction**. Do **not** touch DetectionLoop, FrameBus, PerceptionStore, `/v1`, or Live Preview merge.

```
ProfileRuntime.preferred_backend
        │
        ▼
build_detection_worker(rt)          ← NEW factory (only wiring change in cli.serve)
        │
        ├─ torch/cpu  → YoloDetectionWorker(.pt)          [existing]
        ├─ onnxruntime → YOLO("*.onnx") path via factory  [v0.2]
        └─ tensorrt    → YOLO("*.engine") path via factory [v0.2]
                │
                ▼
        DetectionLoop (UNCHANGED) → PerceptionStore → /v1 + overlays
```

**Major components:**

1. **`build_detection_worker`** — backend selection, artifact resolve, sticky fallback decision, returns duck-typed ModelWorker  
2. **Artifact path resolution** — explicit config/env → cache `{stem}.onnx|.engine` → CWD allowlist → miss → policy  
3. **`preferred_backend` vs `live_backend`** — intent vs what actually loaded; banner + status must show both when they differ  
4. **YoloDetectionWorker** — remains default desktop torch path  
5. **Export scripts** — offline producers only; serve never `model.export` on hot path  
6. **InferenceBackend protocol** — keep for mocks/tests; optional native Ort/Trt later; **not** required for Ultralytics-native v0.2 path  

**Frozen checklist:** FrameBus keep-latest · DetectionLoop · PerceptionStore · assemble/`/v1` · depth/OV/free-space workers · perception-only boundary · localhost default.

**imgsz contract:** export imgsz must match serve preprocess (default 640); mismatch = silent wrong boxes.

### Critical Pitfalls (watch-outs)

Condensed from [PITFALLS.md](./PITFALLS.md). Top risks for roadmap/PRs:

1. **Silent backend lies** — Status shows `tensorrt` while torch runs. **Avoid:** `backend_requested` / `backend_live` / `fallback_reason`; sticky resolve once; integration tests without artifacts.  
2. **Engine SKU non-portability** — Copying `.engine` desktop→Jetson or cross-Orin. **Avoid:** on-device build only; machine-local cache fingerprint; refuse multi-SKU release assets.  
3. **JetPack matrix blindness** — Generic PyPI `onnxruntime-gpu` / pip `tensorrt` on Jetson. **Avoid:** system TRT; Jetson Zoo / JP-matched ORT wheels in docs only (not lockfile).  
4. **Fallback thrash** — Per-frame retry ORT/TRT→torch. **Avoid:** sticky degraded state; one resolve per process (or explicit reconfigure).  
5. **Postprocess drift** — Custom ORT decode ≠ Ultralytics letterbox/head. **Avoid:** Ultralytics-native load first; golden parity if custom path ever lands.  
6. **Dual-model memory** — TRT YOLO + torch DAV2 OOM on Orin Nano-class. **Avoid:** isolate backends first; jetson defaults (n + Small + OV off); measure before claims.  
7. **CI fake confidence** — GPU-required tests or untested loaders. **Avoid:** mock selection/fallback in GHA; hardware checklist outside merge gate.  
8. **FPS overclaim** — Ultralytics bench ≠ Sentry e2e dual-model. **Avoid:** measure-on-device language; latency fields over hero FPS tables.  
9. **AGPL laundering** — “We only ship ONNX so AGPL is gone.” **Avoid:** extend THIRD_PARTY_MODELS for exported artifacts; keep detect optional.  
10. **Inline engine build on serve** — First-frame multi-minute hang. **Avoid:** export CLI separate; serve loads existing engines only.

---

## Implications for Roadmap

Phases continue from **v1.0 Phases 1–7** (shipped). v0.2 = **Phases 8–12** (five phases).

### Phase 8: Backend Selection & Honesty Contracts
**Rationale:** Blocks every other edge plan — v1 residual is “preferred_backend is cosplay.” Structure before loaders.  
**Delivers:** `build_detection_worker` factory wired in `cli.serve`; artifact path candidates on `ProfileRuntime`; `preferred_backend` vs `live_backend` (+ reason) in banner/status; torch-only path still works; v1 “not live” strings prepared for replacement.  
**Addresses:** Profile-selected backend skeleton; backend identity telemetry seed; CI contract tests for selection map.  
**Avoids:** Silent backend lies; per-frame resolve thrash; device string `"tensorrt"` to Ultralytics.  
**REQ seeds:** `BACKEND-01`, `BACKEND-02`, `BACKEND-03`, `EDGE-RT-01`  
**Research flag:** Standard patterns — skip deep research; code sites known (`cli.serve`, `profile_runtime`).

### Phase 9: Live ORT Fixed-Class YOLO
**Rationale:** Portable intermediate; CI-friendly (`onnx` extra + CPU EP); proves export→live before TRT hardware matrix.  
**Delivers:** Live load of `.onnx` via Ultralytics AutoBackend; `cpu-fallback` profile actually runs ORT when artifact+extra present; same `Detection` schema; honest fail/fallback when package or onnx missing; unit/mocks without GPU.  
**Uses:** `onnxruntime` extra; Ultralytics ONNXBackend; existing `results_to_detections`.  
**Implements:** Factory branch for `onnxruntime`; artifact resolve for `.onnx`.  
**Avoids:** Custom postprocess drift; silent CPU EP when GPU claimed (provider assert if GPU ORT documented); Jetson PyPI GPU wheel advice.  
**REQ seeds:** `EDGE-RT-02`, `EDGE-RT-03`, `BACKEND-04`  
**Research flag:** **Light research** if YOLO26 ONNX I/O or Ultralytics provider selection surprises appear — spike one exported `yolo26n.onnx` early.

### Phase 10: Live TensorRT Fixed-Class YOLO
**Rationale:** Milestone claim for Jetson first-class; depends on factory + honesty from Phase 8; shares Detection contract with ORT.  
**Delivers:** Live `.engine` load (system TRT); `jetson` (+ optional desktop TRT) profile real path; on-device engine lifecycle docs/script path only; no serve-time build by default; fingerprint/cache guidance.  
**Uses:** System/JetPack TensorRT; Ultralytics TensorRTBackend; on-device `export_yolo.py --format engine`.  
**Avoids:** Multi-SKU engines in repo; pip `tensorrt` extra; inline first-frame build; engine copy as supported deploy.  
**REQ seeds:** `EDGE-RT-04`, `EDGE-RT-05`, `EDGE-RT-06`  
**Research flag:** **Needs research-phase** for JetPack/TRT binding notes and desktop vs Jetson install matrix (SKU-specific; verify-on-device language).

### Phase 11: Sticky Fallback, Dual-Model Guardrails & Status Surface
**Rationale:** Soft vs strict modes and dual-model VRAM only make sense once both loaders exist; thrash and OOM are field killers.  
**Delivers:** Documented fallback matrix (`fallback_to_torch` soft default vs strict edge); sticky degraded state; status/API fields for live backend + reason; dual-model guidance (detect TRT + depth torch); no OV continuous with TRT+DAV2; device triple logging (`CUDA_VISIBLE_DEVICES` / requested / visible).  
**Avoids:** Fallback thrash; dual-model OOM surprise; split-brain GPU indices; FPS marketing tables.  
**REQ seeds:** `BACKEND-05`, `BACKEND-06`, `EDGE-RT-07`  
**Research flag:** Standard once loaders exist; optional VRAM measure checklist on real Orin — manual, not GHA.

### Phase 12: Edge Packaging Docs, CI Hardening & Milestone Polish
**Rationale:** Table stakes “Jetson first-class” is incomplete without export→serve narrative; CI mocks must gate merge.  
**Delivers:** Updated `docs/export/jetson-packaging.md` + `yolo26-onnx-tensorrt.md` (live path, not recipes-only); CLI honesty strings fully replaced; CI selection/fallback matrix green without Jetson; AGPL/`THIRD_PARTY_MODELS` for `.onnx`/`.engine`; hardware validation checklist (manual); no dual-model FPS guarantees.  
**Avoids:** Stale “still PyTorch” banners; AGPL silence; hero FPS; GPU-required default pytest.  
**REQ seeds:** `EDGE-RT-08`, `EDGE-RT-09`, `BACKEND-07`  
**Research flag:** Skip — documentation and test hardening on known surfaces.

### Phase Ordering Rationale

- **Honesty/factory first** — every loader depends on preferred vs live truth (PITFALLS #5).  
- **ORT before TRT** — portable, lockfile-friendly, proves Detection parity without Jetson (FEATURES + STACK).  
- **TRT next** — hardware/docs matrix; reuses factory + Detection contract.  
- **Fallback + dual-model after both loaders** — policy needs real failure modes; VRAM only after single-backend isolation.  
- **Docs/CI last (but mocks from Phase 9 onward)** — contract tests ship with first loader; packaging narrative closes milestone.  
- **Never on critical path:** DetectionLoop rewrite, depth/YOLOE edge backends, OpenVINO, ROS2, multi-cam fusion.

### Research Flags

| Phase | Flag | Why |
|-------|------|-----|
| 8 | Standard | Known construction site; selection pure wiring |
| 9 | Light spike | One ONNX golden path; provider honesty |
| 10 | **Research-phase recommended** | JetPack/TRT/engine fingerprint; on-device lifecycle |
| 11 | Standard + manual measure | Policy code + optional Orin VRAM checklist |
| 12 | Standard | Docs/tests |

---

## REQ-ID Seeds (for requirements / roadmap)

Use these as stable IDs when writing REQUIREMENTS.md / ROADMAP acceptance. Families: **EDGE-RT** (edge runtime capability), **BACKEND** (selection, honesty, packaging).

### BACKEND family — selection, honesty, status

| ID | Seed requirement |
|----|------------------|
| **BACKEND-01** | Serve constructs fixed-class detector via a factory driven by `ProfileRuntime.preferred_backend` (not hard-coded `YoloDetectionWorker` only). |
| **BACKEND-02** | Runtime exposes both `backend_requested` and `backend_live` (and `fallback_reason` when they differ) in CLI banner and operator-visible status/telemetry. |
| **BACKEND-03** | Artifact resolution order: explicit config/env → model cache `{stem}.onnx\|.engine` → allowlisted CWD → miss (never invent paths). |
| **BACKEND-04** | Missing ORT package or `.onnx` when `preferred_backend=onnxruntime` yields hard-fail **or** documented loud torch fallback — never silent. |
| **BACKEND-05** | Backend resolve is sticky for process lifetime (or explicit reconfigure); no per-frame fallback thrash. |
| **BACKEND-06** | Soft (`fallback_to_torch: true`) vs strict (`false`) modes documented; jetson-class may default stricter for field honesty. |
| **BACKEND-07** | CI contract tests cover selection map + missing-artifact matrix without Jetson, system TRT, or weight download in default pytest. |

### EDGE-RT family — live inference capability

| ID | Seed requirement |
|----|------------------|
| **EDGE-RT-01** | `desktop-gpu` remains live torch (`.pt`) by default; ORT/TRT are opt-in via profile/config. |
| **EDGE-RT-02** | Live ONNX Runtime path for **fixed-class YOLO only** produces schema-identical `list[Detection]` (bbox xyxy, conf, class_id/name). |
| **EDGE-RT-03** | `cpu-fallback` profile with ORT deps + `.onnx` artifact runs live ORT (not torch-only honesty note). |
| **EDGE-RT-04** | Live TensorRT path for fixed-class YOLO loads on-device `.engine` via system TRT (no project `tensorrt` pip extra). |
| **EDGE-RT-05** | `jetson` profile with engine + system TRT runs live TensorRT; missing engine/deps are honest (fail or loud fallback). |
| **EDGE-RT-06** | Engines are built on target device only; product docs forbid cross-SKU/desktop→Jetson engine copy; no multi-SKU engines in git/wheel. |
| **EDGE-RT-07** | Depth remains PyTorch/HF and open-vocab remains PyTorch on-demand; no live ORT/TRT for those stages this milestone. |
| **EDGE-RT-08** | Docs: Jetson on-device engine build → `sentry serve --profile jetson` measured path; no dual-model FPS guarantees. |
| **EDGE-RT-09** | Live Preview boxes and `/v1` detections remain single-truth for the same frame product rules regardless of backend. |

**Non-goals as negative seeds (do not assign as ship requirements):** live depth ORT/TRT; live YOLOE ORT/TRT; OpenVINO first-class; auto-build engine on serve; Pi dual-model FPS tables; DetectionLoop/FrameBus redesign.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | PyPI ORT 1.28 + Ultralytics AutoBackend verified; Jetson wheel URLs MEDIUM (verify on board) |
| Features | **HIGH** | Scope locked by PROJECT.md + code; packaging friction MEDIUM |
| Architecture | **HIGH** | DetectionLoop duck-typing and single serve wiring site code-verified; native vs Ultralytics path opinionated above |
| Pitfalls | **HIGH** | Honesty, SKU engines, CI, AGPL patterns match v1 decisions + export docs |

**Overall confidence:** **HIGH** for roadmap structure and phase order; **MEDIUM** for exact JetPack cells and any future custom YOLO26 decode.

### Gaps to Address

| Gap | When / how |
|-----|------------|
| Soft vs strict default for jetson profile | Product decision in Phase 8/11 planning — recommend soft for makers, strict opt-in or profile flag for field |
| Artifact discovery final config keys (`models.detector_onnx` / env names) | Phase 8 plan — align with `configure_model_cache` |
| Desktop GPU ORT first-class vs CPU-ORT only | Prefer CPU ORT in `onnx` extra; document GPU ORT as manual (STACK) |
| Ultralytics-native vs custom InferenceBackend long-term | **v0.2 = Ultralytics-native**; revisit only if edge binary size/license forces slim path |
| Minimum Jetson SKU for “first-class” language | Docs honesty (Orin Nano vs older) — Phase 10/12; measure-on-device only |
| YOLO26 ONNX tensor names if custom path forced | Phase 9 spike; only if Ultralytics load fails parity |
| Dual-model VRAM budgets | Phase 11 manual checklist per SKU — not merge-blocking numbers |

### Resolved research tension

| Tension | Resolution for roadmap |
|---------|------------------------|
| STACK: Ultralytics-native ORT/TRT vs ARCHITECTURE: custom OrtBackend/TrtBackend | **Ship Ultralytics-native in v0.2**; factory + honesty + artifact paths are the architecture plug-in. Keep `InferenceBackend` for mocks; native backends deferred. |
| FEATURES: hard-fail default vs ARCHITECTURE: soft fallback default | **Soft default for maker UX** (`fallback_to_torch: true`) with **loud** live/requested mismatch; strict mode available for edge deploy. |

---

## Sources

### Primary (HIGH confidence)

- `.planning/PROJECT.md` — v0.2 Edge Runtime scope lock  
- `src/sentry_ai/models/detection/loop.py` — backend-agnostic DetectionLoop  
- `src/sentry_ai/models/detection/yolo_worker.py` — torch live path + conf contract  
- `src/sentry_ai/cli.py` — serve wiring + v1 honesty logs  
- `src/sentry_ai/config/profile_runtime.py` — preferred_backend device policy today  
- `src/sentry_ai/backend/protocols.py` — InferenceBackend stub  
- `docs/export/yolo26-onnx-tensorrt.md`, `docs/export/jetson-packaging.md` — on-device engines, no pip tensorrt  
- `THIRD_PARTY_MODELS.md` — AGPL YOLO lineage  
- PyPI: `onnxruntime` / `onnxruntime-gpu` 1.28.0 (2026-08-09)  
- Ultralytics AutoBackend (`onnx` / `engine` map) + ONNX/TensorRT integration docs  
- Research dimension files: [STACK.md](./STACK.md), [FEATURES.md](./FEATURES.md), [ARCHITECTURE.md](./ARCHITECTURE.md), [PITFALLS.md](./PITFALLS.md)

### Secondary (MEDIUM confidence)

- Ultralytics Jetson guide — JetPack 5/6/7 ORT wheel tables (URLs drift; verify on device)  
- NVIDIA TensorRT engine portability rules  
- Isaac ROS DNN encode→infer→decode pattern (architecture analogy)

### Tertiary (LOW confidence / validate later)

- Exact Orin Nano dual-model VRAM budgets — measure per SKU  
- Counsel interpretation of AGPL for exported graphs — document risk, not DIY legal advice  
- Ultralytics AutoBackend stability across minor bumps — re-benchmark on pin changes  

---

*Research completed: 2026-08-09*  
*Milestone: v0.2 Edge Runtime*  
*Ready for roadmap: yes*  
*Suggested phases: 8–12 (Backend honesty → Live ORT → Live TRT → Fallback/dual-model → Docs/CI)*

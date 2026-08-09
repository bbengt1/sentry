# Feature Landscape: v0.2 Edge Runtime

**Domain:** Live edge inference for fixed-class YOLO (ONNX Runtime + TensorRT) on an existing camera-only perception stack  
**Milestone:** Sentry AI v0.2 Edge Runtime  
**Researched:** 2026-08-09  
**Confidence:** HIGH for product scope (PROJECT.md + codebase); MEDIUM for ORT/TRT packaging friction on Jetson SKUs  

## Scope Lock (do not expand)

| In scope | Out of scope this milestone |
|----------|----------------------------|
| Live **ONNX Runtime** path for **fixed-class YOLO only** | Live ORT/TRT for depth (DAV2 stays PyTorch/HF) |
| Live **TensorRT** path for **fixed-class YOLO only** (NVIDIA desktop + Jetson-class) | Live ORT/TRT for open-vocab YOLOE (stays PyTorch on-demand) |
| Profiles wire `preferred_backend` to **real loaders** (not export-only hints) | Pi-class published dual-model FPS as first-class claim |
| Honest fallbacks when engine/model/deps missing | Metric depth calibration UX |
| Desktop GPU + Jetson-class **first-class**; Pi **best-effort** | Production ROS2 package; multi-cam fusion |
| CI-safe tests (mock ORT/TRT; no Jetson in GHA) | Prebuilt multi-SKU `.engine` artifacts in repo/wheel |

**Shipped baseline (v1.0):** FrameBus → DetectionLoop → YoloDetectionWorker (Ultralytics PyTorch) → PerceptionStore; profiles apply detector/depth tiers + *device policy only*; export recipes exist under `docs/export/` + `scripts/export/`.

---

## Table Stakes

Features makers and edge deployers expect once Sentry claims “live ORT/TRT,” not “export recipes only.” Missing any of these makes the milestone feel incomplete or dishonest.

| Feature | Why Expected | Complexity | Notes / Sentry dependency |
|---------|--------------|------------|---------------------------|
| **Profile-selected live backend** | `preferred_backend` already exists on profiles; users expect `jetson` → TensorRT, `cpu-fallback` → ORT to *run*, not just log honesty notes | Med | Wire via `profile_runtime` → serve construction (`cli.py`); stop treating ORT/TRT as export-only |
| **Live YOLO fixed-class on ORT** | Portable edge/CPU path after ONNX export; baseline for non-TRT targets | Med–High | New loader behind fixed-class worker surface; `DetectionLoop` stays unchanged (worker protocol) |
| **Live YOLO fixed-class on TensorRT** | Jetson packaging docs already teach on-device engines; without live load, jetson profile is cosplay | High | On-device `.engine` only; no cross-SKU copy; system TRT (no pip `tensorrt` extra) |
| **Same Detection schema / overlays** | Robots and Live Preview must not care which backend produced boxes | Low–Med | Keep `results_to_detections` / equivalent → `list[Detection]`; overlays + `/v1` unchanged |
| **Honest missing-artifact behavior** | Silent PyTorch fallback when user asked for TRT is worse than a clear error | Med | Explicit policy: hard-fail preferred path *or* documented torch fallback with loud log + status field — never silent |
| **Honest missing-dependency behavior** | ORT/TRT wheels/system libs often absent on maker machines | Med | Clear ImportError / startup message with install/export next step |
| **Torch remains default desktop path** | Dev ergonomics; weights iteration; no engine rebuild every experiment | Low | `desktop-gpu` stays `preferred_backend: torch`; ORT/TRT opt-in via profile/config |
| **Depth stays PyTorch this milestone** | Scope lock; dual-export for DAV2 is separate hard problem | — | Depth worker + loop untouched for backend selection |
| **Open-vocab stays PyTorch on-demand** | Dual continuous models on edge is unmeasured; YOLOE export experimental | — | `YoloeOpenVocabWorker` / OpenVocabLoop unchanged |
| **FrameBus keep-latest semantics preserved** | Edge backends that block longer must not grow queues | Low | Workers still only `get_latest()` via `DetectionLoop`; no backpressure on capture |
| **CI without Jetson / system TRT** | GHA cannot assume NVIDIA edge hardware | Med | Mock InferenceBackend / injected models; unit tests for selection + fallback matrix |
| **Jetson docs: build engine → serve** | Table stakes for “first-class Jetson” after recipes-only v1 | Med | Update `docs/export/jetson-packaging.md` + `yolo26-onnx-tensorrt.md` from export-only to live path |
| **Backend identity visible in telemetry** | Operators need to know what actually ran (torch vs ort vs trt) | Low | Extend detection product / stage metrics (`model_name` already set; add backend tag) |
| **CUDA→MPS/CPU honesty retained** | Maker machines without CUDA still work on torch path | Low | Existing `resolve_device`; do not invent fake `tensorrt` torch devices |

### Table-stakes quality bar (non-negotiable)

- **Contract stability:** ORT/TRT produce the same `Detection` fields (bbox xyxy image coords, conf, class_id/name) as Ultralytics path.
- **No dual truth:** Live Preview boxes == `/v1` detections for the same `frame_id` product snapshot rules as today.
- **Profile honesty:** If profile says `tensorrt` and no engine/deps, operator sees why — not a quiet torch run.
- **On-device TRT engines:** Build on the target GPU/JetPack; never ship multi-SKU engines in git/wheel.
- **Perception-only boundary:** Backend swap does not add control/planning surface.

---

## Differentiators

Features that turn “another YOLO export tutorial” into a product-shaped edge runtime on Sentry’s existing stack.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **One serve path, multiple backends** | Makers switch profile, not rewrite capture/API/UI | Med | Selection lives in construction + worker load; `DetectionLoop` / FrameBus / API stay backend-agnostic |
| **Profiles as real deployment units** | `desktop-gpu` / `jetson` / `cpu-fallback` become executable runtime choices, not YAML folklore | Med | `ProfileRuntime.preferred_backend` drives loader factory; tiers still choose weights |
| **Honest fallback matrix** | Trust: document when torch fallback is allowed vs hard-fail | Med | Differentiates from silent “export target” lies in v1.0 |
| **Export → live continuity** | Same `scripts/export/export_yolo.py` artifacts load at serve time | Med | Close the loop from EDGE-03 recipes to actual inference |
| **Desktop + Jetson first-class packaging story** | Dev on laptop GPU; deploy Jetson with measured path (no fake FPS) | Med–High | Pi stays “spatial awareness lite / best-effort” language |
| **Mockable backend protocol for CI** | Contributors validate selection logic without NVIDIA hardware | Low–Med | Extend `InferenceBackend` / NullBackend patterns already in `backend/` |
| **Stage isolation** | Only fixed-class YOLO gains edge backends; depth/OV remain stable | Low (discipline) | Reduces blast radius; clear “what got faster” story |
| **Operator-visible backend in stream metadata** | Robots can log/audit which runtime produced detections | Low | Useful for field debugging thermal/FPS regressions |

### Differentiator priority for v0.2 story

1. Live ORT + live TRT for fixed-class YOLO (the milestone claim)  
2. Profiles select real loaders with honest fallbacks  
3. Jetson on-device engine → `sentry serve --profile jetson` measured path  
4. CI-safe mocks; no hardware required for merge  
5. Telemetry/backend identity so operators trust the path  

---

## Anti-Features

Features to **explicitly not build** in v0.2 (or ever as core without a new milestone).

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Live ORT/TRT for depth** | DAV2 export + preprocess parity is a separate project; milestone scope is YOLO fixed-class | Keep HF/PyTorch depth worker |
| **Live ORT/TRT for YOLOE / open-vocab** | Heavier dual-model edge path; export still experimental | PyTorch on-demand only |
| **Prebuilt multi-SKU TensorRT engines in repo/releases** | Engines bind to GPU arch + JetPack/TRT version; broken copies look like product bugs | Document on-device build; optional user-local cache paths |
| **pip `tensorrt` project extra as required path** | Jetson uses system/JetPack TRT; pip matrix is a support nightmare | System TRT + docs; optional desktop notes only |
| **Silent preferred_backend ignore** | v1.0 honesty notes already train users to distrust profiles | Either load the backend or fail/fallback loudly |
| **Pi dual-model realtime FPS claims** | Unmeasured; thermal/CPU variance; product liability for “realtime” | Best-effort language; measure-on-device only |
| **OpenVINO first-class live path** | Enum exists; not milestone target | Leave advisory / future |
| **NCNN/MNN/CoreML live paths** | Extra surface without maker demand for this milestone | Defer |
| **Changing FrameBus / DetectionLoop architecture** | Keep-latest + worker protocol already correct for slower backends | Swap worker implementation only |
| **Queue-based detection backlog** | Latency explosion on edge | Keep DetectionLoop skip-if-same-frame_id |
| **Robot control / safety interlock from “faster detect”** | Perception-only boundary | Unchanged API contract |
| **Guaranteed sustained FPS tables without measurement** | Marketing lie | “Measure on device” docs only |
| **Mandatory Ultralytics runtime for ORT/TRT path** | If ORT session can run exported YOLO graph, don’t require full torch stack on edge — *if* preprocess/postprocess is owned | Prefer thin ORT/TRT loaders; torch remains default desktop |
| **Auto-export at serve start** | Slow, non-deterministic, needs GPU/TRT on first boot | Explicit export script + path config |
| **Cross-device engine copy as supported deploy** | Known failure mode | Document as unsupported |

---

## Complexity Matrix

| Feature | Complexity | Risk | Rationale |
|---------|------------|------|-----------|
| Backend selection from `profile_runtime` | Low–Med | Config edge cases | Pure wiring if loaders exist |
| ORT session load + YOLO preprocess/postprocess | Med–High | Box decode parity vs Ultralytics; NMS-free YOLO26 head differences | Highest correctness risk for “same Detection” |
| TensorRT engine load + infer | High | JetPack/TRT version skew; binding shapes; FP16 | Hardware matrix pain |
| Honest fallback policy | Med | Product decision: fail-closed vs torch fallback | Must be explicit in CLI + docs |
| Artifact path resolution (`.onnx` / `.engine`) | Med | Cache dirs, allowlists, cwd surprises | Mirror weight allowlist discipline from export script |
| DetectionLoop integration | Low | — | Loop already worker-agnostic |
| FrameBus interaction | Low | Slow infer → higher overwrite drops | Expected; metrics already exist |
| Overlay / `/v1` parity | Low | Mapper bugs only | Reuse mapping layer |
| Jetson packaging docs | Med | Stale JetPack notes | “As of / verify on device” language |
| CI mocks | Med | Over-mocking hides real load bugs | Contract tests + optional manual edge checklist |
| Desktop ORT-GPU wheel | Med–High | `onnxruntime-gpu` vs CUDA version hell | Prefer CPU ORT for portability; GPU ORT optional later |
| Pi best-effort ORT | Med | May be too slow with depth concurrent | Stage toggles already exist |

---

## Dependencies on Existing Sentry Components

Features must compose with shipped architecture — not fork a second pipeline.

```
CaptureLoop
    → FrameBus (keep-latest ImageFrame)
        → DetectionLoop
            → Fixed-class worker (ModelWorker protocol)
                 ├─ YoloDetectionWorker          [v1.0 PyTorch Ultralytics]
                 ├─ OrtYoloDetectionWorker       [v0.2 NEW]
                 └─ TrtYoloDetectionWorker       [v0.2 NEW]
            → PerceptionStore.set_detections(...)
        → DepthLoop / worker                     [unchanged PyTorch]
        → OpenVocabLoop / worker                 [unchanged PyTorch on-demand]
        → FreeSpaceLoop                          [unchanged]
    → API assemble PerceptionFrame + Live Preview overlays
```

| Component | Role in v0.2 | Change expected? |
|-----------|--------------|------------------|
| **FrameBus** | Sole frame source for detection; drop metrics under slower edge infer | No API change; expect higher `frames_dropped` when backend is slower |
| **DetectionLoop** | Thread: bus → `worker.process` → store; enable gate; error → empty dets + error string | Prefer **no** structural change; inject different worker |
| **YoloDetectionWorker** | Current fixed-class PyTorch path; conf get/set; weights + device | Keep as torch backend; optionally share conf/protocol helpers |
| **profile_runtime** | Resolves tiers, `preferred_backend`, device policy | **Yes** — map backend to loader choice + artifact paths, not only torch device string |
| **InferenceBackend protocol** | `load` / `infer` / `close` + NullBackend | **Yes** — real ORT/TRT implementations or worker-internal sessions that honor the same idea |
| **results_to_detections / mapping** | Schema boundary | Reuse or dual-path into same `Detection` list |
| **plugins registry (`yolo-fixed`)** | Builtin worker registration | Register backend variants or factory by backend name |
| **Export scripts/docs** | Produce `.onnx` / `.engine` | Become **inputs** to live loaders, not dead-end recipes |
| **Profiles YAML** | `desktop-gpu` torch, `jetson` tensorrt, `cpu-fallback` onnxruntime | Semantics change from “export hint” → “live preference” |
| **CLI honesty logs** | Currently warn that TRT/ORT are not live | Replace with load result / fallback messaging |
| **Depth / OV / free-space** | Out of backend scope | No feature work |

### Feature → component dependency graph

```
Profile YAML preferred_backend
    → profile_runtime()
        → backend factory / worker construction (serve)
            → OrtYolo* | TrtYolo* | YoloDetectionWorker
                → DetectionLoop (unchanged)
                    → FrameBus.get_latest()
                    → PerceptionStore.set_detections()
                        → /v1 + Live Preview

export_yolo.py (.onnx / .engine on device)
    → artifact path config / discovery
        → Ort / Trt worker load()
```

**Critical path for milestone completeness:**

1. Backend factory from `profile_runtime.preferred_backend`  
2. ORT live infer → `list[Detection]`  
3. TRT live infer → `list[Detection]` (NVIDIA path)  
4. Honest missing model/deps policy  
5. Wire into serve + DetectionLoop (no camera ownership in workers)  
6. Docs: Jetson on-device engine + serve  
7. CI mocks for selection/fallback  

---

## Feature Dependencies (ordering)

```
Export recipes (shipped v1.0)
    → Artifact path convention (.onnx / .engine)
        → ORT loader for fixed-class YOLO
        → TRT loader for fixed-class YOLO
            → profile_runtime backend selection
                → serve construction chooses worker
                    → DetectionLoop runs worker
                        → same PerceptionStore / API / overlays
            → honest fallback / error policy
            → telemetry: backend identity
            → Jetson packaging docs (live)
            → CI mocks

Depth PyTorch path ── independent (no dep on ORT/TRT)
Open-vocab PyTorch ── independent (no dep on ORT/TRT)
```

**Do not block on:** OpenVINO, YOLOE export hardening, metric depth, ROS2, multi-cam.

---

## MVP Recommendation (v0.2)

### Prioritize (must ship)

1. **Profile → real fixed-class backend selection** (`torch` | `onnxruntime` | `tensorrt`) via `profile_runtime` + serve wiring  
2. **Live ORT inference** for YOLO fixed-class producing schema-identical detections  
3. **Live TensorRT inference** for YOLO fixed-class on NVIDIA/Jetson with on-device engines  
4. **Honest fallbacks** — documented matrix for missing engine, missing ORT/TRT, wrong device  
5. **DetectionLoop-compatible workers** (no FrameBus redesign)  
6. **CI mocks** for loader selection + fallback without hardware  
7. **Docs:** Jetson engine build → `sentry serve --profile jetson`; desktop torch default unchanged  
8. **Backend identity** in detection telemetry / logs  

### Explicit platform bar

| Target | Status | Language |
|--------|--------|----------|
| Desktop GPU | First-class | Default `torch`; optional ORT/TRT for lab |
| Jetson-class | First-class | Live TRT preferred; measure on device; no FPS guarantees |
| Raspberry Pi / generic CPU | Best-effort | ORT + nano tier; “spatial awareness lite”; no dual-model FPS claim |

### Defer (explicit)

| Feature | Why defer |
|---------|-----------|
| Live ORT/TRT depth | Separate export + correctness project |
| Live ORT/TRT open-vocab | Continuous dual-model + experimental export |
| Pi published FPS tables | Unmeasured; anti-claim |
| OpenVINO live | Enum only; not milestone |
| Auto-build engines at serve | Slow/non-deterministic first boot |
| Prebuilt engines in Releases | SKU binding |
| Changing free-space / depth contracts | Orthogonal |

---

## Honest Fallback Matrix (product policy)

Recommend this matrix for roadmap/plan authors (opinionated):

| Requested backend | Missing piece | Recommended behavior |
|-------------------|---------------|----------------------|
| `torch` | ultralytics/torch | Hard-fail serve with install extra message |
| `onnxruntime` | `onnxruntime` package | Hard-fail *or* opt-in `--fallback-torch` with **loud** warning (default: hard-fail when backend explicitly requested) |
| `onnxruntime` | `.onnx` artifact | Hard-fail with export command pointer |
| `tensorrt` | system TRT / bindings | Hard-fail with Jetson packaging pointer (do not pretend TRT ran) |
| `tensorrt` | `.engine` artifact | Hard-fail with on-device export command |
| `tensorrt` | CUDA unavailable | Hard-fail (TRT requires NVIDIA); do not invent CPU TRT |
| Any | Infer runtime error mid-frame | Existing DetectionLoop behavior: empty dets + `error` string; keep thread alive |

**Anti-pattern:** profile `preferred_backend: tensorrt` while always running Ultralytics PyTorch with only a log line (v1.0 status). That is the gap this milestone closes.

---

## Competitive / Ecosystem Context (edge inference only)

| Capability | Ultralytics alone | Isaac ROS DNN | DepthAI | **Sentry v0.2 target** |
|------------|:-----------------:|:-------------:|:-------:|:----------------------:|
| Export ONNX/TRT recipes | ✓ | ✓ | proprietary | ✓ (shipped v1.0) |
| Live multi-backend in one product | DIY | ✓ | device pipeline | **✓ fixed-class YOLO** |
| Profile-driven desktop→Jetson | DIY | platform graphs | HW-locked | **✓** |
| Same robot API after backend swap | DIY | ROS msgs | SDK | **✓ `/v1` unchanged** |
| Honest missing-engine UX | weak | varies | N/A | **✓ required** |
| Live depth on TRT | DIY | common | HW | **✗ deferred** |

Sentry’s edge differentiator is **not** inventing TensorRT — it is binding live ORT/TRT into the existing FrameBus/DetectionLoop/API product with profile honesty.

---

## Implications for Roadmap

Suggested feature slices (for phase planning; not a full roadmap):

1. **Backend contracts + selection** — extend `profile_runtime` / factory; DetectionLoop-compatible worker interface; telemetry backend tag  
2. **Live ORT fixed-class** — load `.onnx`, infer, map to `Detection`; cpu-fallback profile  
3. **Live TRT fixed-class** — load on-device `.engine`; jetson (+ optional desktop) profile  
4. **Honesty + docs + CI** — fallback matrix, Jetson serve path, mocks, replace v1.0 “not live” CLI notes  

**Ordering rationale:** selection + shared Detection contract first; ORT before TRT (portable, CI-friendlier); TRT needs hardware docs but can share preprocess/postprocess with ORT if designed carefully; depth/OV never on the critical path.

**Research flags for later phase work:**

- YOLO26 ORT postprocess parity (NMS-free head) — likely needs deeper research  
- Jetson ORT wheel source (Jetson Zoo vs PyPI) — SKU-specific  
- Whether Ultralytics can load `.engine`/`.onnx` directly vs custom sessions — stack decision, not feature expansion  

---

## Sources

| Source | Use | Confidence |
|--------|-----|------------|
| `.planning/PROJECT.md` Current Milestone v0.2 | Scope lock, in/out features | HIGH |
| `src/sentry_ai/models/detection/yolo_worker.py` | Current fixed-class live path | HIGH |
| `src/sentry_ai/models/detection/loop.py` | Worker-agnostic loop contract | HIGH |
| `src/sentry_ai/bus/frame_bus.py` | Keep-latest semantics | HIGH |
| `src/sentry_ai/config/profile_runtime.py` | preferred_backend still device-policy only | HIGH |
| `src/sentry_ai/backend/protocols.py` | InferenceBackend stub surface | HIGH |
| `docs/export/yolo26-onnx-tensorrt.md` | Export-only honesty; deferred live backends | HIGH |
| `docs/export/jetson-packaging.md` | Jetson first-class packaging constraints | HIGH |
| Profile YAMLs (`desktop-gpu`, `jetson`, `cpu-fallback`) | Backend preferences per target | HIGH |

---

## Open Questions (phase research, not scope expansion)

1. **Fail-closed vs torch fallback default** when ORT/TRT requested but unavailable — product UX choice.  
2. **Artifact discovery:** sidecar next to weights, config path, or cache dir convention?  
3. **ORT GPU on desktop:** first-class or CPU-ORT only for portability?  
4. **Ultralytics-as-loader vs raw ORT/TRT sessions** for YOLO26 head decode — stack decision with correctness impact.  
5. **Minimum Jetson SKU** for “first-class” language (Orin Nano vs older) — docs honesty only.

---

*Research dimension: Features only for v0.2 Edge Runtime. Stack, architecture, and pitfalls belong in sibling research files.*

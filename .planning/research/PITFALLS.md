# Domain Pitfalls: Live ORT / TensorRT YOLO on Ultralytics PyTorch Stack

**Domain:** Edge inference backends for fixed-class YOLO (ONNX Runtime + TensorRT)  
**Project:** Sentry AI — milestone **v0.2 Edge Runtime**  
**Researched:** 2026-08-09  
**Overall confidence:** HIGH (SKU/JetPack/AGPL/honesty patterns verified against Sentry v1.0 code + export docs); MEDIUM (exact JetPack↔ORT wheel matrix drifts by SKU — always verify on device)

v1.0 ships **export recipes only**: `preferred_backend: tensorrt | onnxruntime` is device policy + honesty logs, live detection is still Ultralytics **PyTorch**. v0.2 makes ORT/TRT **real loaders**. The failure modes below are the ones that turn that upgrade into silent lies, OOM thrash, or unsupportable CI.

**Scope of this doc:** Fixed-class YOLO edge backends only. Depth stays PyTorch/HF this milestone; YOLOE stays PyTorch/on-demand. Do not invent dual-backend depth.

---

## Critical Pitfalls

### 1. Engine SKU non-portability (copying `.engine` across boxes)

**What goes wrong:**  
A TensorRT `.engine` built on a desktop RTX, Orin NX, or AGX is treated as a deployable artifact. Operators copy it to another Jetson SKU or another JetPack install. Load fails with opaque TRT errors, or worse, **appears** to load and produces wrong/slow results because SM arch / TRT version do not match.

**Why it happens:**  
Engines are compiled for a **GPU compute capability + TensorRT major/minor + (often) CUDA** triple. They are not ONNX. Desktop→Jetson and Orin Nano→Orin AGX copies are the classic maker mistake. v1 docs already forbid prebuilt multi-SKU engines in the repo/wheel — live TRT makes the temptation stronger (ship engines on Releases “for convenience”).

**Consequences:**
- “Works on my desktop, broken on Jetson” support black hole
- Silent accuracy/perf regressions if a mismatched engine partially runs
- Git LFS / release bloat of non-portable binaries

**Prevention:**
- **On-device build only** for production engines (same board + JetPack + TRT as serve)
- Refuse to ship `.engine` in git, wheel, or multi-SKU GitHub Releases
- Cache engines under a **machine-local** path keyed by fingerprint, e.g.  
  `{gpu_name}:{sm_arch}:{trt_version}:{weights}:{imgsz}:{precision}`  
  Invalidate on any key change
- CLI/docs: `sentry export … --format engine` must print “build on target; do not copy”
- Optional startup check: refuse load when engine metadata fingerprint ≠ host probe

**Detection:**
- Load errors mentioning incompatible platform / deserialization
- Engine file timestamps older than last JetPack upgrade
- Same `.engine` path reused across profile switches without rebuild

**Phase ownership:** **TRT engine lifecycle / Jetson packaging** (early TRT plan — before any “prebuilt engines” feature discussion).

**Confidence:** HIGH  
**Sources:** [Sentry jetson-packaging.md](../../docs/export/jetson-packaging.md), [yolo26-onnx-tensorrt.md](../../docs/export/yolo26-onnx-tensorrt.md), NVIDIA TensorRT developer guide (engines are platform-specific)

---

### 2. JetPack matrix blindness (torch / ORT / TRT / CUDA version soup)

**What goes wrong:**  
Team pins `onnxruntime-gpu` from generic PyPI, or a desktop CUDA torch wheel, on a Jetson. Install “succeeds,” import fails, CUDA contexts disagree, or TRT Python bindings from JetPack disagree with the engine builder used by Ultralytics. JetPack 5 vs 6, L4T, and Python 3.8/3.10/3.11 differences are ignored until field deploy.

**Why it happens:**  
PyPI GPU wheels target x86_64 CUDA toolkits. Jetson needs **JetPack-matched** wheels (NVIDIA forums / Jetson Zoo / JP container images). Ultralytics export for `engine` uses **system TensorRT**, not a project `tensorrt` extra — correct for Jetson, easy to “fix” by pip-installing random TRT.

**Consequences:**
- Days lost to ABI / CUDA symbol errors
- Engines built with one TRT version unloadable after `apt` JetPack point release
- Docs that say “just pip install onnxruntime-gpu” actively harm Jetson users

**Prevention:**
- Document a **verify-on-device** matrix table (not a fake universal pin):

  | Component | Rule |
  |-----------|------|
  | TensorRT | JetPack-bundled only; **no** project `tensorrt` pip extra |
  | ORT on Jetson | JetPack-/L4T-matched wheel or container — **not** generic `onnxruntime-gpu` from PyPI |
  | ORT on desktop CUDA | `onnxruntime-gpu` matched to host CUDA major |
  | ORT on CPU/CI | `onnxruntime` CPU wheel only |
  | PyTorch | Keep as default desktop path; Jetson torch from NVIDIA/JP guidance when dual-model depth stays torch |

- Rebuild engines after **any** JetPack / TRT upgrade
- `probe_device` / health should report: CUDA available, TRT version string (if present), ORT version, **not** just `preferred_backend`
- Prefer documented container (JP base image) over “host Python roulette” for Jetson CI-like bring-up

**Detection:**
- `ImportError` / `libcublas` / `libnvinfer` version mismatches at load
- Engine build works, runtime load fails after OS update
- `onnxruntime-gpu` installs but `get_device()` shows CPU only

**Phase ownership:** **Jetson packaging + stack pins** (docs plan parallel to first live TRT/ORT loaders). Revisit whenever JetPack major changes.

**Confidence:** HIGH for “don’t use generic PyPI GPU wheels on Jetson”; MEDIUM for exact version cells (SKU-specific — verify on device).

**Sources:** [Sentry jetson-packaging.md](../../docs/export/jetson-packaging.md), [STACK.md inference backends](./STACK.md), NVIDIA Jetson Zoo / JetPack release notes

---

### 3. CI without GPU becomes fake confidence (or blocks the pipeline)

**What goes wrong:**  
Either (a) GitHub Actions tries to import TRT / run real engines and the job is red forever, or (b) CI only tests the PyTorch path while ORT/TRT loaders ship untested and break on first Jetson boot.

**Why it happens:**  
v1 correctly forbids Jetson in CI (`export` tests = argparse + allowlist only). Live backends need **more** tests without hardware — easy to either over-require GPU or under-mock the selection graph.

**Consequences:**
- Flaky or impossible CI
- Regressions in backend selection, fingerprint, and fallback never caught
- Contributors without NVIDIA cannot develop

**Prevention:**
- **Layered test strategy:**

  | Layer | What runs in GHA | What does not |
  |-------|------------------|---------------|
  | Unit | Backend selection, path resolution, fingerprint keys, error messages | Real CUDA |
  | Mock loaders | Fake ORT/TRT sessions inject detections | Weight download, `model.export` |
  | Contract | `preferred_backend` → actual loader class mapping | Hardware FPS |
  | Optional nightly / manual | On-device Jetson/desktop GPU smoke | Required for merge |

- Keep default `sentry serve --profile cpu-fallback` CI-safe
- Never download YOLO weights or call Ultralytics `export` in default pytest
- Gate real ORT CPU smoke (optional extra) behind explicit marker, not default job
- Document “hardware validation checklist” for release, separate from unit green

**Detection:**
- CI job needs `nvidia-smi` or fails on `import tensorrt`
- 100% coverage on loaders that only run under `@pytest.mark.gpu`
- No test asserts “when engine missing → explicit status”

**Phase ownership:** **CI / test harness** plan **alongside** first ORT loader (not deferred to “polish”). Mock backends are part of the feature, not afterthought.

**Confidence:** HIGH (matches v1 EDGE-03 decisions and PROJECT.md “CI-safe tests without Jetson”).

---

### 4. AGPL still applies when the runtime is ORT/TRT

**What goes wrong:**  
Team believes “we only ship ONNX/engine, not Ultralytics Python, so AGPL goes away.” Commercial forks redistribute YOLO26-derived graphs without AGPL obligations review. Or the reverse: refuse any YOLO path and block the milestone unnecessarily without documenting the actual obligation surface.

**Why it happens:**  
Export changes the **runtime loader**, not the **weight/training lineage**. Ultralytics YOLO26 / YOLOE remain **AGPL-3.0** in Sentry’s third-party table. Custom ORT postprocess code is Apache-2.0 app code; the model artifact is still AGPL-sensitive for many counsel interpretations when derived from AGPL tooling/weights.

**Consequences:**
- Legal surprise late in a commercial robot product
- Incomplete `THIRD_PARTY_MODELS.md` after new export artifacts (`.onnx`, `.engine`) appear on disk
- False marketing: “commercially friendly edge stack” while default detector is still AGPL weights

**Prevention:**
- Keep AGPL YOLO behind optional `detect` extra; never imply Apache-2.0 covers detector weights
- Extend `THIRD_PARTY_MODELS.md` for **exported artifacts** (same license lineage as source `.pt`)
- Status/UI: continue non-default commercial caution language when fixed-class YOLO is loaded (any backend)
- Do not treat ORT/TRT as a license laundering step
- If a commercially licensed detector is required later, that is a **different model plugin**, not a silent swap of YOLO weights

**Detection:**
- Docs claim “edge path is license-clean” without AGPL callout
- Releases bundle `yolo26n.onnx` without license notes
- `defaults_commercially_friendly: true` on profiles that still pull AGPL detectors (profile flag vs weight license confusion)

**Phase ownership:** **Docs / policy** at milestone start; verify again when export artifacts are first **loaded** (not only exported).

**Confidence:** HIGH for “document and do not launder”; legal interpretation of AGPL for exported graphs is counsel-dependent (flag as product risk, not DIY legal advice).

**Sources:** [THIRD_PARTY_MODELS.md](../../THIRD_PARTY_MODELS.md), Ultralytics LICENSE (AGPL-3.0)

---

### 5. Silent backend lies (`preferred_backend` ≠ live loader)

**What goes wrong:**  
Profile says `tensorrt` or `onnxruntime`, health/UI shows that string, but inference still runs PyTorch (v1 behavior) **or** silently falls back to torch/CPU when engine/onnx is missing. Operators believe they measured TRT FPS. Bug reports cite “TRT is slow” when TRT never ran.

**Why it happens:**  
v1 honesty logs exist in CLI (`preferred_backend=tensorrt → live path is still PyTorch`) because loaders were deferred. v0.2 must **delete the lie**, not remove the logs. Half-migrated code paths (policy maps device to `cuda:0` while `BackendName.TENSORRT` is displayed) are the danger zone.

**Consequences:**
- False performance claims
- Impossible field debugging
- Robots trust a “production edge backend” that is actually eager PyTorch + HF depth OOM

**Prevention:**
- Single source of truth: **actual loader identity** reported in status/telemetry  
  e.g. `detection.backend_live: torch | onnxruntime | tensorrt` separate from `detection.backend_requested`
- Fail closed or fail loud:
  - **Strict mode (jetson profile default candidate):** missing engine → clear error / degraded stage off, not silent torch
  - **Dev mode:** explicit opt-in `fallback_to_torch: true` with warning + UI badge
- Never return a fake torch device string `"tensorrt"` (v1 `device_for_backend` already avoids this — keep that invariant)
- Integration test: request ORT/TRT without artifacts → assert status fields, not only logs
- Live Preview footer: show **live** backend, not profile name alone

**Detection:**
- `preferred_backend=tensorrt` but process RSS/GPU modules show only `libtorch`
- Logs lack engine path / ORT provider list
- FPS “improves” after deleting the `.engine` (fallback thrash — see below)

**Phase ownership:** **Backend selection & honesty contracts** — **first** v0.2 phase before ORT/TRT feature work. Blocks every other edge plan.

**Confidence:** HIGH  
**Sources:** [profile_runtime.py](../../src/sentry_ai/config/profile_runtime.py), [cli honesty notes](../../src/sentry_ai/cli.py), PROJECT.md Active requirements

---

### 6. Dual-model memory collision (YOLO ORT/TRT + DAV2 PyTorch)

**What goes wrong:**  
Detection moves to TRT/ORT “to free GPU,” but depth remains HF PyTorch DAV2 Small on the same GPU. Peak VRAM = TRT workspace + torch CUDA caching allocator + two sets of weights + capture/MJPEG. Jetson Orin Nano class OOMs, throttles, or one stage starves. Enabling open-vocab YOLOE on top is a third resident model.

**Why it happens:**  
v0.2 scope is YOLO-only edge backends; depth stays torch. Makers assume “TensorRT = always enough headroom.” TRT builder workspace and torch cache do not share a single polite budget. Continuous dual-model was already unmeasured on Jetson in v1 docs.

**Consequences:**
- Random `CUDA out of memory` mid-session
- Detection “works alone,” full pipeline dies
- Thermal throttle masquerading as “slow backend”

**Prevention:**
- Default **jetson** profile: detector `n`, depth Small, open-vocab **off** (already); keep that under live TRT
- Document **resident set** expectations: detect backend + depth torch may **exceed** detect-only TRT blog numbers
- Load order: fail early with a clear “dual-model VRAM” message rather than looping OOM
- Provide knobs: disable depth, lower `imgsz`, FP16 only, limit TRT workspace, single-stream
- Do **not** co-load YOLOE continuous with TRT YOLO + DAV2 in this milestone
- Optional: sequential GPU time-slicing (detect then depth) before claiming concurrent dual-model

**Detection:**
- OOM only when free-space/depth enabled
- `nvidia-smi` shows both TRT and python torch processes fighting one GPU
- Latency spikes correlate with depth+detect both “ready”

**Phase ownership:** **Dual-model scheduling / Jetson validation** after single-model ORT and TRT paths work in isolation. Do not combine until each path is honest alone.

**Confidence:** HIGH for risk; MEDIUM for exact MB budgets (measure per SKU).

**Sources:** [jetson-packaging.md](../../docs/export/jetson-packaging.md), [desktop-gpu.md](../../docs/desktop-gpu.md) (no dual-model FPS guarantees)

---

### 7. Fallback thrash (oscillating loaders / retry storms)

**What goes wrong:**  
Missing engine → fallback to torch → next frame retries TRT → fails → fallback again. Or ORT CUDA provider fails init every N frames and silently uses CPU. Or profile reload / UI toggle re-instantiates backends without releasing GPU memory.

**Why it happens:**  
Eager “be helpful” fallback without **sticky degraded state**. Combined with keep-latest loops that call `_ensure_model` patterns, transient errors become permanent flapping. Multi-thread detect + depth + free-space increase race windows on load locks.

**Consequences:**
- Multi-second stalls every few frames
- Telemetry FPS oscillates; robots see intermittent stale detections
- GPU memory fragmentation from repeated load/unload

**Prevention:**
- **Sticky backend decision** at worker start (or explicit reconfigure):  
  `requested → resolve once → live backend`  
  On failure: enter `degraded` with reason; do not re-resolve every frame
- Reconfigure only on explicit config change (profile, weights path, force_reload)
- Cap retries (e.g. one rebuild attempt per process) with cooldown
- Distinguish error classes:
  - Missing artifact → degraded / strict fail (no thrash)
  - Transient infer error → drop frame, keep backend
  - Fatal CUDA error → stop stage, surface status
- Tests: inject fail-on-load once; assert single attempt + stable `backend_live`

**Detection:**
- Log spam: “falling back to torch” every frame
- Alternating latency 5 ms / 80 ms patterns
- Rising GPU mem without new features enabled

**Phase ownership:** **Honest fallback policy** plan immediately after first real loader (same phase as silent-lie prevention). Shared by ORT and TRT.

**Confidence:** HIGH

---

### 8. `CUDA_VISIBLE_DEVICES` / device index confusion

**What goes wrong:**  
Profile `device_id: "0"` plus env `CUDA_VISIBLE_DEVICES=1` (or empty) means process-local GPU 0 is a different physical device — or none. ORT `CUDAExecutionProvider` device_id, TRT builder GPU, and torch `cuda:0` disagree. Multi-GPU desktops “randomly” use the wrong card; Jetson with MIG/containers sees empty CUDA.

**Why it happens:**  
v1 `resolve_device` normalizes bare `"0"` → `cuda:0` via **torch** visibility. ORT/TRT each have their own device index semantics. Ultralytics export `--device 0` is yet another entry point. Nested containers rewrite visibility without updating profile YAML.

**Consequences:**
- Engine built on GPU A, runtime binds GPU B
- “CUDA unavailable” while another process sees the GPU
- Hard-to-reproduce maker setups (laptop + eGPU, multi-RTX)

**Prevention:**
- Resolve **one** physical device at startup; pass the same index into torch / ORT / TRT
- Log the triple: env `CUDA_VISIBLE_DEVICES`, requested id, runtime-visible device name
- Prefer `device_id: "0"` meaning “first **visible** GPU” and document that explicitly
- In containers, set visibility before process start; do not change mid-run
- Health endpoint: `torch.cuda.get_device_name(0)` (if any) + ORT provider options
- Never assume desktop `cuda:0` engine path is valid on Jetson without rebuild (ties to pitfall 1)

**Detection:**
- Export and serve use different GPU ids in logs
- `CUDA_VISIBLE_DEVICES=` empty → all CUDA paths fall back while nvidia-smi shows cards
- ORT reports CPU EP while torch uses CUDA (split brain)

**Phase ownership:** **Device policy / probe** in backend selection phase; extend `resolve_device` / `probe_device` rather than forking per-loader ad hoc logic.

**Confidence:** HIGH

**Sources:** [device.py](../../src/sentry_ai/models/device.py), [profile_runtime.py](../../src/sentry_ai/config/profile_runtime.py)

---

### 9. Ultralytics export vs custom ORT session (postprocess drift)

**What goes wrong:**  
Export via `YOLO.export(format="onnx"|"engine")` is correct, but live path reimplements preprocess/postprocess in raw ORT/TRT and **drifts** from Ultralytics: wrong letterbox, BGR/RGB, normalization, conf/iou, NMS-free head handling (YOLO26), class id mapping, or `imgsz` mismatch vs engine build. Boxes look “almost right” — shifted, scaled, or low-recall.

**Why it happens:**  
Temptation to drop Ultralytics dependency on edge for license/size reasons and hand-roll `onnxruntime.InferenceSession`. YOLO26 end-to-end / NMS-free details are easy to get wrong. Mixing Ultralytics-exported graph with a YOLOv8-era postprocess blog post is common.

**Consequences:**
- Silent accuracy regression vs PyTorch path
- Golden-frame tests fail only on edge profile
- Makers blame “TensorRT quantization” when the bug is letterbox pad

**Prevention:**
- **Preferred path for v0.2:** load exported artifacts **through Ultralytics** where possible (`YOLO("model.onnx")` / `YOLO("model.engine")`) so preprocess/postprocess stay aligned — custom ORT only if measured need
- If custom ORT/TRT is required:
  - Pin export flags (`imgsz`, `simplify`, half/fp16) in one module shared by export script + loader
  - Golden test: same image → PyTorch vs ORT/TRT boxes within tolerance (mockable with fixture tensors)
  - Do not copy third-party NMS code for YOLO26 without verifying head type
- Export script remain basename-allowlisted; loader accepts only known export layouts
- Document: engine `imgsz` must match serve `imgsz` (rebuild on change)

**Detection:**
- IoU mismatch vs torch on fixed synthetic frames
- Boxes systematically shifted by pad margins
- Score distributions differ wildly at same `conf`

**Phase ownership:** **ORT loader** first (portable intermediate); **TRT loader** reuses the same preprocess/postprocess contract. Golden parity tests owned by the first custom path that bypasses Ultralytics predict.

**Confidence:** HIGH for drift risk; MEDIUM for “always use Ultralytics YOLO(engine)” as long-term architecture (API may change — verify on pinned ultralytics version).

**Sources:** [export_yolo.py](../../scripts/export/export_yolo.py), [yolo26-onnx-tensorrt.md](../../docs/export/yolo26-onnx-tensorrt.md), Ultralytics export docs

---

### 10. FPS overclaim (blog numbers ≠ dual-model sustained)

**What goes wrong:**  
README, UI, or release notes publish “YOLO26n TensorRT 200+ FPS on Orin” (or Ultralytics bench numbers) as if that were **Sentry end-to-end**: capture + detect + DAV2 depth + free-space + MJPEG + `/v1` stream. Operators design robot control loops around that fiction.

**Why it happens:**  
Vendor benches are often detect-only, power-unlocked, ideal thermal, fixed resolution, no depth, no Python GIL/API overhead. v1 already refused dual-model FPS tables; live TRT increases marketing pressure to “finally publish numbers.”

**Consequences:**
- Unsafe control-loop assumptions
- Support burden (“your FPS claims are lies”)
- Scope creep to chase bench FPS instead of honest latency budgets

**Prevention:**
- **Never** publish guaranteed FPS for dual-model stacks without on-device measurement protocol
- If numbers appear, label axes explicitly:

  | Metric | Meaning |
  |--------|---------|
  | `detect_infer_ms` | Backend only |
  | `detect_e2e_ms` | Bus→worker→store |
  | `pipeline_e2e_ms` | Capture→all stages→PerceptionFrame |
  | `sustained_fps` | Thermal-throttled minutes, not peak |

- Prefer **latency + stale flags** in API (already PerceptionFrame-oriented) over headline FPS
- Jetson docs: “measure on device”; link methodology, not a single hero number
- UI telemetry: show measured moving average, not profile marketing FPS

**Detection:**
- README tables without methodology
- Confusing `detect_infer_ms` with camera FPS
- Claims carried over from Ultralytics blog without Sentry pipeline context

**Phase ownership:** **Docs + telemetry honesty** continuous; block release notes review. Measurement optional plan **after** loaders work — never gate loader merge on inventing FPS tables.

**Confidence:** HIGH  
**Sources:** [desktop-gpu.md](../../docs/desktop-gpu.md), [jetson-packaging.md](../../docs/export/jetson-packaging.md), PROJECT.md (no fake FPS guarantees)

---

## Moderate Pitfalls

### 11. Building engines inside `serve` on first frame

**What goes wrong:**  
Missing `.engine` triggers inline TRT build on first predict — multi-minute hang, thermal spike, watchdog kills, looks like deadlock.

**Prevention:**  
Separate **export/build** CLI from **serve**. Serve only loads existing engines (or explicit `--build-engine` opt-in with timeout + progress logs).

**Phase ownership:** TRT lifecycle.

### 12. Precision / calib mismatch (FP32 export, FP16 engine, INT8 without calibration)

**What goes wrong:**  
INT8 or aggressive FP16 without validation tanks recall; blame “ORT bug.”

**Prevention:**  
Default FP16 on Jetson with golden parity; INT8 only after calibration story (defer INT8 from v0.2 core if needed).

**Phase ownership:** TRT export settings; parity tests.

### 13. Provider priority mistakes (ORT CUDA EP listed but fails → CPU without banner)

**What goes wrong:**  
`InferenceSession` succeeds on CPU EP; profile still says GPU edge.

**Prevention:**  
Assert expected providers after session create; expose `session.get_providers()` in status; fail or badge on unexpected CPU.

**Phase ownership:** ORT loader + honesty contracts.

### 14. Threading + non-thread-safe sessions

**What goes wrong:**  
ORT/TRT sessions shared across detect loop + ad hoc API infer without locks; rare corruption or driver crashes.

**Prevention:**  
One infer mutex per session (v1 YOLO worker already serializes via loop design — keep it); no multi-threaded session run unless documented.

**Phase ownership:** Worker integration.

### 15. Profile default still `cpu-fallback` while docs push jetson TRT

**What goes wrong:**  
Makers run default serve, never hit ORT/TRT, conclude “edge doesn’t work.”

**Prevention:**  
Docs: explicit `--profile jetson` / `desktop-gpu` + artifact paths; do not auto-switch default profile in CI-hostile ways (v1 decision: keep cpu-fallback default).

**Phase ownership:** Docs + CLI UX.

---

## Minor Pitfalls

| Pitfall | Prevention | Phase |
|---------|------------|-------|
| Leaving v1 honesty log text after live TRT ships (“still PyTorch”) | Update CLI strings when loader is real; golden-test help text | Honesty contracts |
| Caching ONNX next to `.pt` without cache root policy | Use `SENTRY_MODEL_CACHE` layout for onnx/engine subdirs | Cache / packaging |
| Forgetting `imgsz` in engine fingerprint | Include imgsz + precision in cache key | TRT lifecycle |
| YOLOE export “works” so continuous OV on Jetson is enabled | Keep OV off/on-demand; out of v0.2 live edge dual-model | Scope control |
| Measuring FPS on synthetic static frames only | Include USB capture + depth for any published e2e number | Docs / validation |

---

## Phase-Specific Warnings (v0.2 roadmap mapping)

Suggested ownership when roadmap phases are cut (names indicative):

| Phase topic | Likely pitfall | Mitigation |
|-------------|----------------|------------|
| **Backend selection & honesty** | Silent backend lies; sticky vs per-frame resolve | `backend_requested` vs `backend_live`; strict vs opt-in fallback |
| **Live ORT (fixed-class YOLO)** | Custom postprocess drift; provider CPU silent; Jetson wheel matrix | Prefer Ultralytics ORT path or golden parity; provider asserts; JP-matched wheels |
| **Live TRT (NVIDIA/Jetson)** | Engine SKU copy; inline build on serve; workspace OOM | On-device build; fingerprint cache; no serve-time build by default |
| **Honest fallback** | Fallback thrash; torch shadow path | Sticky degraded state; explicit `fallback_to_torch` |
| **Dual-model / memory** | TRT YOLO + torch DAV2 OOM | Isolate then combine; OV off; measure resident VRAM |
| **CI without GPU** | Untested loaders or GPU-required CI | Mocks + contract tests; hardware checklist outside GHA |
| **Jetson packaging docs** | JetPack soup; FPS overclaim; AGPL omission | Verify-on-device matrix; no hero FPS; license table for artifacts |
| **Device policy** | `CUDA_VISIBLE_DEVICES` split brain | Single resolution + logged triple |

**Ordering rationale (avoid rewrite):**  
1) Honesty contracts → 2) ORT with mocks/CI → 3) TRT on-device lifecycle → 4) sticky fallback → 5) dual-model memory validation → 6) docs matrix / FPS discipline throughout.

---

## Anti-Patterns Checklist (PR review)

- [ ] Shipping `.engine` in repo or multi-SKU release assets  
- [ ] `pip install tensorrt` / generic `onnxruntime-gpu` recommended for Jetson  
- [ ] Status shows `tensorrt` while loader is torch  
- [ ] Per-frame fallback without sticky state  
- [ ] Custom ORT postprocess without torch golden compare  
- [ ] Dual-model FPS table without methodology  
- [ ] AGPL silence after adding `.onnx` distribution  
- [ ] Default pytest requires GPU, Jetson, or weight download  
- [ ] Serve blocks on first-frame engine build  
- [ ] Ignoring `CUDA_VISIBLE_DEVICES` in device logs  

---

## What This Milestone Should Explicitly Not “Fix” via Shortcuts

| Shortcut | Why it is a pitfall amplifier |
|----------|-------------------------------|
| Prebuilt engines for “all Jetsons” | SKU non-portability at scale |
| Drop Ultralytics entirely in week one | Postprocess drift + longer schedule |
| Live ORT/TRT for depth + YOLOE same milestone | Dual/triple-model memory and scope explosion |
| Publish Ultralytics bench FPS as Sentry FPS | Control-loop overclaim |
| Treat export as license clean | AGPL still in play |

---

## Sources

| Source | Confidence | Use |
|--------|------------|-----|
| [docs/export/yolo26-onnx-tensorrt.md](../../docs/export/yolo26-onnx-tensorrt.md) | HIGH | On-device engine rules, no prebuilt engines |
| [docs/export/jetson-packaging.md](../../docs/export/jetson-packaging.md) | HIGH | Jetson profile honesty, CI without Jetson |
| [docs/desktop-gpu.md](../../docs/desktop-gpu.md) | HIGH | Primary path; no dual-model FPS guarantee |
| [THIRD_PARTY_MODELS.md](../../THIRD_PARTY_MODELS.md) | HIGH | AGPL YOLO/YOLOE |
| [src/sentry_ai/config/profile_runtime.py](../../src/sentry_ai/config/profile_runtime.py) | HIGH | v1 preferred_backend → device policy (not live TRT) |
| [src/sentry_ai/cli.py](../../src/sentry_ai/cli.py) honesty logs | HIGH | Current silent-lie prevention baseline |
| [src/sentry_ai/models/device.py](../../src/sentry_ai/models/device.py) | HIGH | CUDA request fallback patterns |
| [.planning/PROJECT.md](../PROJECT.md) v0.2 goals | HIGH | Live ORT/TRT scope, CI, depth stays torch |
| [.planning/research/STACK.md](./STACK.md) | HIGH | ORT/TRT backend matrix guidance |
| NVIDIA TensorRT docs (engine portability) | HIGH | SKU/arch binding |
| Ultralytics export / Jetson guides | MEDIUM–HIGH | Export API; bench numbers are **not** Sentry e2e |

---

*PITFALLS for v0.2 Edge Runtime — live ORT/TRT fixed-class YOLO on existing Ultralytics PyTorch stack. Supersedes v1.0 monocular-product PITFALLS research for roadmap input; depth metric/FSD pitfalls remain valid product constraints but are not the focus of this milestone.*

# Phase 9: Live ORT Fixed-Class YOLO - Research

**Researched:** 2026-08-09  
**Domain:** Live Ultralytics-native ONNX Runtime path for fixed-class YOLO (factory soft-stub → real loader)  
**Confidence:** HIGH (code-verified Phase 8 factory + Ultralytics ONNXBackend in installed 8.4.116; package pins re-checked on PyPI)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Ultralytics-native: `YOLO("*.onnx")` + existing `predict` + `results_to_detections` preferred over custom ORT
- Optional `onnx` extra: `onnxruntime>=1.20,<1.29` (prefer 1.28.x)
- No `tensorrt` pip extra this phase
- Factory remains sole author of `backend_live`
- Phase 8 spine freeze continues: DetectionLoop / bus / store / `/v1` unchanged except worker impl
- Artifact resolution via existing `resolve_detector_artifact` + env `SENTRY_DETECTOR_ONNX`

### Claude's Discretion
- Whether live ORT reuses `YoloDetectionWorker` with onnx weights path or a thin wrapper class
- How conf/device map for ORT (cpu default for cpu-fallback profile)
- Whether missing onnxruntime ImportError soft-falls to torch with reason `ort_dep_missing`
- Exact golden fixture strategy (inject fake YOLO model that claims onnx backend)

### Deferred Ideas (OUT OF SCOPE)
- Live TRT `.engine` (Phase 10)
- Sticky thrash-free fallback modes (Phase 11)
- onnxruntime-gpu as separate exclusive extra (docs only ok)
- YOLOE ORT
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ORT-01 | Fixed-class YOLO can run live via ONNX Runtime when profile prefers `onnxruntime` and a valid `.onnx` artifact is present | Factory ORT branch: resolve `.onnx` → probe `onnxruntime` → `YoloDetectionWorker(weights=str(onnx_path))` → `backend_live=onnxruntime` |
| ORT-02 | ORT path produces the same `Detection` wire contract (class, conf, bbox_xyxy, source=fixed) as the PyTorch path | Same worker `predict` + `results_to_detections`; Detection defaults `source="fixed"`; no schema change |
| ORT-03 | Optional `onnx` (or equivalent) extra documents install; CI does not require GPU ORT | `pyproject.toml` `onnx` extra pins CPU `onnxruntime`; docs update; CI tests use mocks / optional CPU marker |
| ORT-04 | Golden/parity tests (mock session or fixture) prove postprocess mapping without Jetson hardware | Inject fake YOLO model on ORT factory path; assert Detection fields + conf; no real GPU ORT / Jetson |
</phase_requirements>

## Summary

Phase 8 shipped the serve-time factory with honest soft-stubs: `preferred_backend=onnxruntime` always returned `backend_live=torch` and reason `ort_loader_not_implemented` (or `path_rejected`). Artifact resolution and status/banner honesty already exist. Phase 9 flips the ORT branch from soft-stub to a **live Ultralytics-native path**: when preferred is `onnxruntime`, a valid allowlisted `.onnx` exists, and `onnxruntime` is importable, construct the fixed-class worker with the `.onnx` weights path so Ultralytics AutoBackend loads `ONNXBackend` (`YOLO("yolo26n.onnx")` → `predict` → existing `results_to_detections`). Only then may `backend_live` be `onnxruntime`.

Missing artifact or missing dependency must **not** claim live ORT. Soft-fallback remains torch with stable reason codes (`ort_artifact_missing`, `ort_dep_missing`, `path_rejected`). The perception spine stays frozen. No custom `InferenceSession` + YOLO26 decoder. No TensorRT work. CI stays free of GPU ORT / Jetson by mocking the load path and reusing Detection mapping golden fixtures.

**Primary recommendation:** Reuse `YoloDetectionWorker` with `weights=<resolved .onnx path>`; probe `importlib.util.find_spec("onnxruntime")` (or try/import) **before** constructing the ORT worker; set `backend_live="onnxruntime"` only on that success path; add `onnx` extra + docs; replace Phase 8 `ort_loader_not_implemented` with the new missing-artifact/dep reasons; prove ORT-02/04 with injected fake models and factory matrix tests (no real `.onnx` load required in default CI).

### Top recommendations for planner

1. **09-01 — Live factory ORT branch + `onnx` extra + docs**  
   - Implement live ORT in `factory.py` only (spine frozen).  
   - Reuse `YoloDetectionWorker(weights=str(onnx_path), conf=…, device=rt.device)`.  
   - Reason vocabulary: drop `ort_loader_not_implemented` for the ORT branch; use `ort_artifact_missing` | `ort_dep_missing` | `path_rejected`.  
   - Pin `onnx = ["onnxruntime>=1.20,<1.29"]` in `pyproject.toml`.  
   - Update `docs/export/yolo26-onnx-tensorrt.md` (and honesty lines in `docs/architecture.md` / `docs/configuration.md`) so they no longer say ORT is export-only.

2. **09-02 — Parity / golden tests without Jetson**  
   - Factory matrix: live ORT success (mocked artifact + mocked dep + optional model inject); each soft-fallback reason; TRT still soft-stub.  
   - Process/conf parity: same FakeModel path as `test_detection_worker.py` on a worker built via factory ORT success path.  
   - Mapping already covers wire contract; assert `source=="fixed"`.  
   - Optional opt-in `@pytest.mark.export`-style or skip-if-no-ort real CPU load — **not** required for merge gate.

3. **Honesty invariants (both plans)**  
   - `backend_live=="onnxruntime"` **iff** worker weights are the resolved `.onnx` path (not `.pt` under an ORT label).  
   - Factory remains sole author of `backend_*`; status/UI pass-through unchanged.  
   - Never import `onnxruntime` / `tensorrt` at factory module top-level.

4. **Do not** hand-roll ORT session decode, add `tensorrt` extra, touch DetectionLoop, or claim live ORT when artifact/deps missing.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| ORT live loader selection | API / Backend (factory at serve construct) | — | One-shot sticky resolve; never per-frame |
| `.onnx` artifact resolve | API / Backend (`artifact_paths`) | Filesystem / cache | Phase 8 allowlist; env `SENTRY_DETECTOR_ONNX` |
| Ultralytics `YOLO("*.onnx")` load + predict | API / Backend (`YoloDetectionWorker`) | Ultralytics ONNXBackend → ORT | Native path; preprocess/NMS/Results owned by Ultralytics |
| Detection wire mapping | API / Backend (`mapping.results_to_detections`) | — | Shared torch/ORT; pure transform |
| Runtime conf adjust | API / Backend (worker `set_conf`/`get_conf`) | API routes (existing) | Conf is worker state passed into `predict`; backend-agnostic |
| `backend_live` honesty | API / Backend (factory sole author) | CLI banner + `/api/status` + Live Preview | Pass-through only (Phase 8) |
| Detection scheduling | API / Backend (DetectionLoop) | — | **Frozen** |
| FrameBus / PerceptionStore / `/v1` | API / Backend | — | **Frozen** |
| Depth / open-vocab | API / Backend | — | **Out of scope** — stay torch |
| Optional `onnx` packaging | Packaging (`pyproject.toml`) | Docs | CPU wheel for CI/makers; no GPU ORT required |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | ≥3.11 | Runtime | [VERIFIED: pyproject.toml] |
| `ultralytics-opencv-headless` (detect extra) | ≥8.4.33,<9 (env **8.4.116**) | `YOLO("*.onnx")` + `predict` + AutoBackend | [VERIFIED: pyproject + installed package + `nn/backends/onnx.py`] |
| `onnxruntime` | **≥1.20,<1.29** (prefer **1.28.x**; PyPI latest **1.28.0**) | Live CPU ORT under Ultralytics ONNXBackend | [VERIFIED: PyPI 2026-08-09; Ultralytics `check_requirements` wants onnxruntime; STACK.md] |
| Existing factory / artifact_paths / yolo_worker / mapping | Phase 8 + Phase 3 | Selection, paths, process, Detection map | [VERIFIED: codebase] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | ≥8 | Factory / parity unit tests | Existing `dev` extra |
| `importlib.util` (stdlib) | — | Probe `onnxruntime` without importing factory-level ORT | Soft-fallback `ort_dep_missing` |
| Optional `onnxruntime-gpu` | same band 1.20–1.28 | Desktop CUDA EP | **Docs only** this phase — not co-extra with CPU ORT [CITED: STACK.md + ORT install practice] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Reuse `YoloDetectionWorker` with `.onnx` weights | New `OrtYoloDetectionWorker` class | Wrapper adds surface for zero API difference; Ultralytics already switches backend by suffix [VERIFIED: AutoBackend `_BACKEND_MAP["onnx"]`] |
| Ultralytics-native path | Custom `onnxruntime.InferenceSession` + decoder | Breaks letterbox/metadata/Results; CONTEXT forbids; high drift risk [CITED: STACK.md / PITFALLS] |
| Soft torch fallback on miss | Hard-fail serve | Breaks “torch still works” for cpu-fallback without artifact; sticky policy is Phase 11 |
| Claim live at first successful `process` only | Claim live at factory when path+dep ok | Lazy load matches torch; factory-time claim is honest **intent+path** as long as weights are `.onnx` and dep probed; load errors stay loop-level empty dets |

**Installation:**

```bash
# CI / makers wanting live ORT (CPU)
uv sync --extra dev --extra detect --extra onnx

# Desktop torch primary (unchanged)
uv sync --extra dev --extra detect --extra depth
```

**Version verification (2026-08-09):**

| Package | Verified version | Source |
|---------|------------------|--------|
| `onnxruntime` | 1.28.0 (`requires_python>=3.11`) | [VERIFIED: PyPI JSON] |
| `onnxruntime-gpu` | 1.28.0 | [VERIFIED: PyPI JSON] — not in project extra |
| `ultralytics` (via detect) | 8.4.116 in workspace `.venv` | [VERIFIED: `uv run` import] |

## Package Legitimacy Audit

> Phase 9 installs one new optional dependency: `onnxruntime` via the `onnx` extra.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `onnxruntime` | PyPI | mature (Microsoft ORT; multi-year) | high (ecosystem standard) | github.com/microsoft/onnxruntime | **unavailable** this session | Approved for pin — tag install as registry-verified; planner may add `checkpoint:human-verify` if policy requires slopcheck |
| `onnxruntime-gpu` | PyPI | mature | high | same | unavailable | **Not installed** via project extra; docs-only |
| `tensorrt` | — | — | — | — | n/a | **OMITTED** (locked) |

**Packages removed due to slopcheck [SLOP] verdict:** none  
**Packages flagged as suspicious [SUS]:** none  

*slopcheck could not be installed/run in this environment. Package name and version were confirmed via PyPI + Ultralytics source (authoritative for this stack). Planner: optional human-verify before first lockfile commit if org policy requires slopcheck green.*

**Pin to emit:**

```toml
[project.optional-dependencies]
onnx = [
  "onnxruntime>=1.20,<1.29",
]
```

Do **not** add `onnxruntime-gpu`, `tensorrt*`, or co-install GPU+CPU ORT extras.

## Architecture Patterns

### System Architecture Diagram

```
ProfileRuntime.preferred_backend == "onnxruntime"
        │
        ▼
build_detection_worker(rt, conf, model=?)
        │
        ├─ resolve_detector_artifact(.onnx) ── ValueError ──► soft torch + path_rejected
        │         │
        │         None ──► soft torch + ort_artifact_missing
        │         │
        │         Path(.onnx)
        │         │
        ├─ probe onnxruntime importable?
        │         │
        │         no ──► soft torch + ort_dep_missing
        │         │
        │         yes
        │         ▼
        │   YoloDetectionWorker(weights=str(onnx_path), conf, device=rt.device [, model])
        │   backend_requested=onnxruntime
        │   backend_live=onnxruntime
        │   backend_reason=None
        │
        ▼
DetectionLoop (UNCHANGED) ── worker.process(frame)
        │                         │
        │                         ▼
        │              YOLO AutoBackend format=onnx → ONNXBackend
        │              session.run / IO binding
        │              Ultralytics Results
        │                         │
        │                         ▼
        │              results_to_detections → list[Detection]
        │              (class_name, confidence, bbox_xyxy, source=fixed)
        ▼
PerceptionStore → /v1 + Live Preview overlays
        │
        └── Status/banner: backend_requested / backend_live / backend_reason (Phase 8 pass-through)
```

### Recommended Project Structure

```
src/sentry_ai/
├── models/detection/
│   ├── factory.py          # ORT branch becomes live (edit)
│   ├── yolo_worker.py      # reuse as-is (weights path drives backend)
│   ├── mapping.py          # reuse as-is
│   └── loop.py             # FROZEN
├── config/
│   └── artifact_paths.py   # reuse as-is
docs/export/
└── yolo26-onnx-tensorrt.md # live ORT section (edit)
pyproject.toml              # onnx extra (edit)
tests/
├── test_detection_factory.py   # extend matrix (edit)
├── test_ort_parity.py          # NEW golden/parity (optional name)
└── test_export_docs.py         # assert live ORT docs keywords (extend)
```

### Pattern 1: Factory live ORT branch (prescriptive)

**What:** Replace soft-stub-only ORT branch with condition chain; soft-fallback preserves Phase 8 honesty.

**When to use:** Always for `requested == "onnxruntime"`.

**Example:**

```python
# Source: Phase 8 factory.py + Ultralytics engine/model.py Model("yolo26n.onnx")
# Prescriptive Phase 9 shape (not committed code)

def _onnxruntime_available() -> bool:
    import importlib.util
    return importlib.util.find_spec("onnxruntime") is not None


def build_detection_worker(rt, *, conf=0.25, model=None) -> WorkerBuild:
    requested = normalize_backend(rt.preferred_backend)

    if requested in {"torch", "cpu"}:
        return WorkerBuild(
            worker=_torch_worker(rt, conf=conf, model=model),
            backend_requested=requested,
            backend_live="torch",
            backend_reason=None,
        )

    if requested == "onnxruntime":
        path, reject = _try_resolve_artifact(rt, preferred="onnxruntime")
        if reject:
            return WorkerBuild(
                worker=_torch_worker(rt, conf=conf, model=model),
                backend_requested="onnxruntime",
                backend_live="torch",
                backend_reason=reject,  # path_rejected
            )
        if path is None:
            return WorkerBuild(
                worker=_torch_worker(rt, conf=conf, model=model),
                backend_requested="onnxruntime",
                backend_live="torch",
                backend_reason="ort_artifact_missing",
            )
        if not _onnxruntime_available():
            return WorkerBuild(
                worker=_torch_worker(rt, conf=conf, model=model),
                backend_requested="onnxruntime",
                backend_live="torch",
                backend_reason="ort_dep_missing",
            )
        # LIVE ORT — weights are the .onnx path; Ultralytics selects ONNXBackend
        worker = YoloDetectionWorker(
            weights=str(path),
            conf=conf,
            device=rt.device,  # cpu-fallback → "cpu" via device_for_backend
            model=model,
        )
        return WorkerBuild(
            worker=worker,
            backend_requested="onnxruntime",
            backend_live="onnxruntime",
            backend_reason=None,
        )

    # tensorrt: still Phase 8 soft-stub (Phase 10)
    ...
```

**Discretion recommendation:** Reuse `YoloDetectionWorker` (no thin wrapper). [ASSUMED product taste — API-identical; less code.]

### Pattern 2: conf / device mapping for ORT

**What:** Keep existing conf duck-type and profile device policy.

| Input | Behavior |
|-------|----------|
| `conf` construct arg | Same `YoloDetectionWorker._validate_conf` |
| `set_conf` / `get_conf` | Thread-safe; applied on next `predict(conf=…)` — works for ORT because conf is a predict kwarg, not baked into the session [VERIFIED: yolo_worker.py + Ultralytics predict API] |
| `rt.device` for cpu-fallback | `device_for_backend("onnxruntime", …)` → `"cpu"` [VERIFIED: profile_runtime.py] |
| Ultralytics EP selection | ONNXBackend: CUDA EP if cuda device + provider, else CoreML on MPS, else CPU [VERIFIED: `nn/backends/onnx.py`] |

### Pattern 3: Golden / parity without Jetson

**What:** Prove Detection contract and factory honesty without loading a real graph.

| Fixture strategy | Use |
|------------------|-----|
| Inject `FakeModel` (existing `test_detection_worker.py` pattern) via `model=` on factory ORT success path | Process → Detection fields + conf on next frame |
| Monkeypatch `_try_resolve_artifact` or place real empty? **No** — use tmp_path allowlisted `yolo26n.onnx` **file** only for path resolve tests; do **not** call real YOLO load in default CI | Artifact presence |
| Monkeypatch `_onnxruntime_available` → True/False | Dep probe without installing ORT in all CI jobs |
| Existing `results_to_detections` unit tests | Postprocess golden (ORT-04 core) |
| Optional: `@pytest.mark.skipif(not ort_installed)` real `YOLO(tiny.onnx)` | Manual/opt-in only; not merge-gate |

### Anti-Patterns to Avoid

- **`backend_live=onnxruntime` while weights still `.pt`:** Silent lie — the Phase 8 failure mode. Only set live ORT when worker weights are the resolved `.onnx`.
- **Module-level `import onnxruntime` in factory:** Breaks “no ORT required to import factory” and CI without the extra [VERIFIED: Phase 8 test `test_factory_module_does_not_import_ort_trt`].
- **Custom ORT session + hand-written YOLO26 head decode:** CONTEXT out of scope; postprocess drift [CITED: STACK / PITFALLS].
- **Relying on Ultralytics `check_requirements` auto-install:** Side-effect installs; probe dep yourself and soft-fall with `ort_dep_missing`.
- **Hard-fail serve when preferred ORT but no artifact:** Soft torch fallback continues until Phase 11 sticky policy.
- **Per-frame re-resolve backend:** Sticky at construct only.
- **Requiring GPU ORT / Jetson in CI:** Violates ORT-03 / EDGE-CI-02.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ONNX inference session + EP selection | Custom `InferenceSession` wrapper | Ultralytics `ONNXBackend` via `YOLO("*.onnx")` | CUDA/CoreML/CPU providers, IO binding, metadata already handled [VERIFIED: onnx.py] |
| YOLO26 letterbox / NMS / end2end decode | Custom postprocess | `model.predict` Results API | Drift vs export graph [CITED: PITFALLS] |
| Results → Detection | Duplicate mapper | `results_to_detections` | Already pure + tested [VERIFIED: mapping.py] |
| Artifact path security | Ad-hoc path join | `resolve_detector_artifact` | Allowlist + root confinement [VERIFIED: artifact_paths.py] |
| Backend identity on status | Recompute in routes | Factory → app.state pass-through | Phase 8 honesty invariant |
| Conf threshold storage | Per-backend conf channels | Existing `set_conf`/`get_conf` | Runtime conf already works on worker |

**Key insight:** Phase 9 is a **factory branch activation** + packaging/docs, not a new inference stack. The Ultralytics suffix dispatch is the product.

## Common Pitfalls

### Pitfall 1: Claiming live ORT under torch weights
**What goes wrong:** Factory sets `backend_live=onnxruntime` but constructs `YoloDetectionWorker(weights=rt.detector_weights)` (`.pt`).  
**Why it happens:** Copy-paste from soft-stub path; only flip the live string.  
**How to avoid:** Live branch **must** pass `weights=str(onnx_path)`; unit assert `worker._weights.endswith(".onnx")` when live=onnxruntime.  
**Warning signs:** Status shows ORT while logs say “Loading YOLO weights=yolo26n.pt”.

### Pitfall 2: Leaving `ort_loader_not_implemented` forever
**What goes wrong:** Even with artifact+deps, still soft-stubs; ORT-01 fails.  
**Why it happens:** Phase 8 tests asserted never-live ORT; implementers leave early return.  
**How to avoid:** Rewrite factory tests: success path **must** live=onnxruntime; remove/narrow `test_backend_live_never_ort_or_trt` for profiles that can go live (or parametrize only jetson/desktop without artifact).  
**Warning signs:** cpu-fallback with fixture `.onnx` still reason=`ort_loader_not_implemented`.

### Pitfall 3: Fake `.onnx` file triggers real YOLO load in CI
**What goes wrong:** Tests create empty/truncated `.onnx`; factory claims live; first `process` raises InvalidProtobuf.  
**Why it happens:** Path existence ≠ valid model.  
**How to avoid:** Default CI injects `model=FakeModel` so `_ensure_model` never hits Ultralytics; real load is opt-in.  
**Warning signs:** CI needs network/ORT and flakes on protobuf errors.

### Pitfall 4: Ultralytics auto-install of onnxruntime
**What goes wrong:** First predict tries `check_requirements` install mid-serve.  
**Why it happens:** ONNXBackend.load_model calls `check_requirements(("onnx", "onnxruntime"…))` [VERIFIED: onnx.py L65].  
**How to avoid:** Factory probes dep before claiming live ORT; document `uv sync --extra onnx`.  
**Warning signs:** Surprise pip activity at first frame.

### Pitfall 5: Docs still say “ORT is export target only”
**What goes wrong:** Operators never install `onnx` extra; always fall back.  
**How to avoid:** Update yolo26 export doc + architecture/configuration honesty paragraphs in the same phase as the factory flip.  
**Warning signs:** `test_export_docs` still asserts pytorch-only live language without live-ORT exception.

### Pitfall 6: Breaking factory import purity test
**What goes wrong:** `import onnxruntime` at top of factory fails Phase 8 source test and CI without extra.  
**How to avoid:** Lazy probe helper only inside ORT branch; keep source-assert test (allow string `"onnxruntime"` in reason codes / find_spec, forbid `import onnxruntime` / `from onnxruntime`).

### Pitfall 7: conf “doesn't work on ORT”
**What goes wrong:** Assumed conf is graph-baked.  
**Why it happens:** Confusion with export-time end2end NMS.  
**How to avoid:** Conf is predict-time filter via Ultralytics Results path; existing set_conf tests apply to ORT worker identically.  
**Warning signs:** None if worker reused; only if custom session skips conf kwarg.

## Code Examples

### Ultralytics-native ORT load (canonical)

```python
# Source: Ultralytics engine/model.py examples + STACK.md
# [VERIFIED: installed ultralytics 8.4.116 docstring Model("yolo26n.onnx")]
from ultralytics import YOLO

model = YOLO("yolo26n.onnx")  # AutoBackend format=onnx → ONNXBackend
results = model.predict(
    source=image_bgr,
    conf=0.25,
    imgsz=640,
    device="cpu",
    verbose=False,
    save=False,
)
```

### Existing worker path (no code change required for predict)

```python
# Source: src/sentry_ai/models/detection/yolo_worker.py
model = YOLO(self._weights)  # if self._weights ends with .onnx → ORT backend
results = model.predict(
    source=image_bgr,
    conf=conf,
    imgsz=DEFAULT_IMGSZ,
    device=device,
    verbose=False,
    save=False,
)
return results_to_detections(results[0])
```

### Detection contract (ORT-02)

```python
# Source: src/sentry_ai/schemas/perception.py + mapping.py
# Detection(class_name, confidence, bbox_xyxy, source="fixed" default)
# results_to_detections does not set source → remains "fixed" for fixed-class path
# [VERIFIED: uv run mapping dump → source='fixed']
```

### Soft-fallback reason codes (Phase 9 vocabulary)

| Code | When | backend_live |
|------|------|--------------|
| `path_rejected` | Explicit/env path fails allowlist (existing) | torch |
| `ort_artifact_missing` | Resolve returns `None` (no existing `.onnx`) | torch |
| `ort_dep_missing` | `onnxruntime` not importable | torch |
| `None` | Live ORT success | **onnxruntime** |
| `trt_loader_not_implemented` | tensorrt preferred (unchanged Phase 10) | torch |
| `unsupported_backend` | openvino/unknown | torch |

**Retired for ORT success path:** `ort_loader_not_implemented` (Phase 8 placeholder). Keep string out of live path; may remain only in historical tests until rewritten.

### Factory test sketch (ORT-04 / honesty)

```python
# Prescriptive — planner should flesh into tests/test_detection_factory.py or test_ort_parity.py

def test_ort_live_when_artifact_and_dep(tmp_path, monkeypatch):
    # allowlisted yolo26n.onnx under cwd/cache; monkeypatch available=True
    # build = build_detection_worker(rt_cpu_fallback, model=FakeModel())
    # assert build.backend_live == "onnxruntime"
    # assert build.backend_reason is None
    # assert str(build.worker._weights).endswith(".onnx")

def test_ort_soft_fallback_dep_missing(...):
    # artifact present, available=False
    # assert live=="torch", reason=="ort_dep_missing"

def test_ort_soft_fallback_artifact_missing(...):
    # no file, available=True
    # assert reason=="ort_artifact_missing"

def test_ort_process_parity_and_conf(...):
    # factory ORT live + FakeModel; process frame; assert Detection fields + source fixed
    # set_conf(0.5); process; assert predict conf=0.5
```

## State of the Art

| Old Approach (Phase 8 / v1) | Current Approach (Phase 9) | When Changed | Impact |
|----------------------------|----------------------------|--------------|--------|
| preferred=onnxruntime → torch + `ort_loader_not_implemented` | preferred=onnxruntime + `.onnx` + dep → live ORT | Phase 9 | Real edge CPU path |
| Docs: “ORT is export target” | Docs: live ORT via Ultralytics + `onnx` extra | Phase 9 | Operator install path |
| `backend_live` never ort/trt | `backend_live` may be onnxruntime when truly live | Phase 9 | Honesty tests must allow success case |
| No `onnx` extra | `onnxruntime>=1.20,<1.29` optional extra | Phase 9 | CI can opt-in CPU ORT |

**Deprecated/outdated:**
- Phase 8 invariant “`backend_live` never onnxruntime” as a global rule — replace with “never claim ORT while running torch weights”.
- Export doc claim that live detection is **only** PyTorch for fixed-class (still true for TRT until Phase 10; false for ORT after Phase 9).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Reusing `YoloDetectionWorker` is preferred over a thin ORT wrapper | Pattern 1 / Discretion | Minor class split later; low product risk |
| A2 | Factory-time `backend_live=onnxruntime` after path+dep probe is “actually loading onnx” enough (lazy Ultralytics load on first process) | Honesty | If product requires eager validate, add construct-time warm-up / load |
| A3 | Soft-fallback reasons `ort_artifact_missing` / `ort_dep_missing` are the stable names CONTEXT suggested | Reason codes | Phase 11 sticky policy may rename; pick once and document |
| A4 | Default CI does **not** install `onnx` extra; mocks cover ORT-04 | Validation | If CI installs onnx extra, real CPU tests become possible but not required |
| A5 | imgsz=640 export matches serve DEFAULT_IMGSZ=640 | Contract | Mismatched export → silent wrong boxes (existing export discipline) |

**If this table is empty:** n/a — several discretion items remain [ASSUMED].

## Open Questions

1. **Eager vs lazy ORT load at factory**  
   - What we know: Torch worker lazy-loads in `_ensure_model`; warm-up is best-effort.  
   - What's unclear: Whether operators want construct-time failure if `.onnx` is corrupt.  
   - Recommendation: Stay lazy + dep probe (A2); corrupt file → DetectionLoop error string on first frames (existing resilience). Phase 11 can add strict mode.

2. **Should `model=` injection force live ORT without real file?**  
   - What we know: Tests need injection without downloads.  
   - What's unclear: Production never passes `model=`.  
   - Recommendation: Require real resolved path for live claim; allow `model=` only as predict backend once path+dep pass (tests create empty allowlisted file **or** monkeypatch resolve). Prefer monkeypatch resolve → Path for cleanliness.

3. **cpu-fallback profile comment still says “ORT is export target”**  
   - Update profile YAML comment + docs in 09-01 so makers aren't misled.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Runtime | ✓ | 3.11.15 | — |
| uv | Install/sync | ✓ | 0.11.23 | — |
| pytest | Tests | ✓ | 9.1.1 | — |
| ultralytics (detect) | YOLO path | ✓ (uv env) | 8.4.116 | Required for live ORT |
| onnxruntime | Live ORT | ✗ (current workspace) | — | Soft `ort_dep_missing`; install via `--extra onnx` |
| GPU ORT / Jetson | — | ✗ | — | Not required (ORT-03) |
| Real `yolo26n.onnx` artifact | Live load | ✗ in repo (expected) | — | Export offline; tests mock |

**Missing dependencies with no fallback:** none for implementing Phase 9 (soft-fallback designed in).  

**Missing dependencies with fallback:** `onnxruntime` → soft torch + `ort_dep_missing` until `uv sync --extra onnx`.

## Validation Architecture

> `workflow.nyquist_validation` is **true** in `.planning/config.json` — full strategy in `09-VALIDATION.md`.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥8 (workspace 9.1.1) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_detection_factory.py tests/test_detection_worker.py tests/test_detection_mapping.py tests/test_ort_parity.py -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| ORT-01 | preferred ORT + artifact + dep → live onnxruntime | unit | `uv run pytest tests/test_detection_factory.py -k ort -q` | ⚠️ extend existing |
| ORT-01 | missing artifact/dep → torch + reason | unit | same | ⚠️ extend |
| ORT-02 | Detection fields + source=fixed | unit | `uv run pytest tests/test_detection_mapping.py tests/test_ort_parity.py -q` | ⚠️ mapping ✅; parity Wave 0 |
| ORT-03 | `onnx` extra in pyproject; no GPU ORT required | unit/static | `uv run pytest tests/test_export_docs.py tests/test_pyproject_onnx_extra.py -q` | ❌ Wave 0 |
| ORT-04 | Golden parity mock without Jetson | unit | `uv run pytest tests/test_ort_parity.py -q` | ❌ Wave 0 |
| conf | set_conf applies on ORT worker path | unit | `uv run pytest tests/test_detection_worker.py tests/test_ort_parity.py -k conf -q` | ⚠️ extend |

### Sampling Rate
- **Per task commit:** quick ORT-focused pytest  
- **Per wave merge:** `uv run pytest -q` + `uv run ruff check src tests`  
- **Phase gate:** Full suite green; no Jetson/GPU required

### Wave 0 Gaps
- [ ] Extend `tests/test_detection_factory.py` — live ORT success + new reason codes; retire global never-ORT live assert
- [ ] Add `tests/test_ort_parity.py` — process + conf + source=fixed via factory ORT path + FakeModel
- [ ] Extend docs tests for live ORT + `onnx` extra install language
- [ ] Optional static assert `pyproject.toml` contains onnx extra pin

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | Local perception serve; unchanged |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Artifact path allowlist (`resolve_detector_artifact`); conf range [0,1]; no arbitrary model path |
| V6 Cryptography | no | — |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `SENTRY_DETECTOR_ONNX` | Tampering | Existing allowlist roots + stem/suffix checks [VERIFIED: artifact_paths.py] |
| Status spoofing live ORT while torch runs | Spoofing | Factory sole author; unit tests assert weights suffix matches live |
| Supply-chain ORT package | Tampering | Pin band from PyPI; optional human-verify; no postinstall custom scripts expected for onnxruntime |
| Malicious/corrupt `.onnx` | Denial / Tampering | Ultralytics load errors; loop catches process exceptions; soft-fallback if dep missing |
| Unexpected auto-install side effects | Elevation / Integrity | Probe dep in factory; document explicit extra install |

## Project Constraints (from CLAUDE.md)

No project-root `CLAUDE.md` / `AGENTS.md` found in workspace. Parent user skill note (`graphify`) is unrelated to this phase. Follow existing Sentry conventions from Phase 8:

- TDD: test → feat commits  
- No DetectionLoop / bus / store / `/v1` redesign  
- Factory sole author of `backend_live`  
- No `tensorrt` pip extra  
- AGPL Ultralytics lineage remains documented for exported artifacts (full EDGE-DOC-02 in Phase 12; mention in export doc update is enough here)

## Sources

### Primary (HIGH confidence)
- `src/sentry_ai/models/detection/factory.py` — Phase 8 soft-stub ORT branch  
- `src/sentry_ai/models/detection/yolo_worker.py` — `YOLO(weights).predict` + conf  
- `src/sentry_ai/models/detection/mapping.py` + `schemas/perception.py` — Detection contract  
- `src/sentry_ai/config/artifact_paths.py` — `.onnx` resolve  
- `.venv/.../ultralytics/nn/backends/onnx.py` — ONNXBackend providers + InferenceSession  
- `.venv/.../ultralytics/nn/autobackend.py` — `"onnx": ONNXBackend`  
- `.venv/.../ultralytics/engine/model.py` — `Model("yolo26n.onnx")` examples  
- PyPI `onnxruntime==1.28.0` metadata (2026-08-09)  
- `.planning/research/STACK.md`, `ARCHITECTURE.md`, `SUMMARY.md`, `PITFALLS.md`  
- `.planning/phases/08-*/08-*-SUMMARY.md`, `08-RESEARCH.md`  
- `09-CONTEXT.md`, `REQUIREMENTS.md` ORT-01..04, `ROADMAP.md` Phase 9  

### Secondary (MEDIUM confidence)
- Project research install matrix for `onnxruntime-gpu` desktop-only guidance  
- Profile YAML comments still describing ORT as export-only (must update)

### Tertiary (LOW confidence)
- Exact operator preference for eager corrupt-`.onnx` detection at serve start (A2)

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — pins re-verified PyPI + Ultralytics source in workspace  
- Architecture: **HIGH** — factory plug-in already shipped; ORT path is weights-suffix activation  
- Pitfalls: **HIGH** — honesty/postprocess/CI patterns proven in Phase 8 research + code  

**Research date:** 2026-08-09  
**Valid until:** ~2026-09-09 (30 days; re-check onnxruntime minor if Ultralytics jumps)

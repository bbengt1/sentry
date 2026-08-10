# Phase 9: Live ORT Fixed-Class YOLO - Pattern Map

**Mapped:** 2026-08-09  
**Files analyzed:** 9  
**Analogs found:** 9 / 9  

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sentry_ai/models/detection/factory.py` | service (factory) | request-response / branch | same file (Phase 8 soft-stub) | exact |
| `src/sentry_ai/models/detection/yolo_worker.py` | service (worker) | transform (frame→detections) | same file (`model=` inject + `YOLO(weights)`) | exact |
| `src/sentry_ai/models/detection/mapping.py` | utility | transform | same file (`results_to_detections`) | exact |
| `pyproject.toml` `[project.optional-dependencies]` | config | N/A | `detect` / `depth` extras block | exact |
| `docs/export/yolo26-onnx-tensorrt.md` | config/docs | N/A | same file (Phase 7 honesty tables) | exact |
| `docs/export/README.md` | config/docs | N/A | same file (live vs offline prose) | exact |
| `tests/test_detection_factory.py` | test | request-response | same file (profile matrix + soft stubs) | exact |
| `tests/test_detection_mapping.py` / parity golden | test | transform | `tests/test_detection_mapping.py` + `tests/test_detection_worker.py` | exact |
| `tests/test_export_docs.py` | test | N/A (keyword) | same file (EDGE-03 keyword asserts) | exact |

**Plans covered:** 09-01 (live path + extra + docs), 09-02 (parity / golden / factory matrix).

---

## Pattern Assignments

### `src/sentry_ai/models/detection/factory.py` (service, branch selection)

**Analog:** `src/sentry_ai/models/detection/factory.py` (Phase 8 shipped)  
**Plan:** 09-01 primary — replace ORT soft-stub with real live loader branch.

**Imports / no module-level ORT** (lines 1–27):
```python
"""Serve-time fixed-class detection worker factory (BACK-01, EDGE-RT-02).

Branches on ``ProfileRuntime.preferred_backend``. Torch path is fully live via
``YoloDetectionWorker``. ORT/TRT branches are soft-stubs in Phase 8: they still
construct a torch worker and report ``backend_live=torch`` with a stable reason
code — never claim live ORT/TRT.

Does not import ``onnxruntime`` or ``tensorrt`` at module level.
"""
from sentry_ai.config.artifact_paths import resolve_detector_artifact
from sentry_ai.config.profile_runtime import ProfileRuntime
from sentry_ai.models.cache import configure_model_cache
from sentry_ai.models.detection.yolo_worker import YoloDetectionWorker
```

**WorkerBuild contract** (lines 30–37) — keep unchanged; only `backend_live` / `backend_reason` values change for success path:
```python
@dataclass(frozen=True)
class WorkerBuild:
    """Detection worker plus honest preferred-vs-live backend identity."""

    worker: Any  # ModelWorker duck-type
    backend_requested: str
    backend_live: str
    backend_reason: str | None = None
```

**Torch worker helper + `model=` injection** (lines 56–66) — reuse for ORT by swapping `weights` to resolved `.onnx` path:
```python
def _torch_worker(
    rt: ProfileRuntime,
    *,
    conf: float,
    model: Any | None,
) -> YoloDetectionWorker:
    return YoloDetectionWorker(
        weights=rt.detector_weights,
        conf=conf,
        device=rt.device,
        model=model,
    )
```

**Artifact resolution already wired** (lines 69–106) — live ORT branch must consume `_path` instead of discarding it:
```python
def _try_resolve_artifact(
    rt: ProfileRuntime,
    *,
    preferred: str,
) -> tuple[Path | None, str | None]:
    ...
    if preferred == "onnxruntime":
        env_value = os.environ.get("SENTRY_DETECTOR_ONNX")
    ...
    try:
        path = resolve_detector_artifact(
            preferred_backend=preferred,
            detector_weights=rt.detector_weights,
            env_value=env_value,
            weights_dir=weights_dir,
            cwd=Path.cwd(),
            artifact_root=artifact_root,
        )
        return path, None
    except ValueError:
        return None, "path_rejected"
```

**Phase 8 soft-stub to replace** (lines 131–139) — this is the exact branch 09-01 rewrites:
```python
if requested == "onnxruntime":
    _path, reject = _try_resolve_artifact(rt, preferred="onnxruntime")
    reason = reject or "ort_loader_not_implemented"
    return WorkerBuild(
        worker=worker,
        backend_requested="onnxruntime",
        backend_live="torch",
        backend_reason=reason,
    )
```

**Recommended live-branch shape (copy structure, not soft-stub outcomes):**
```python
if requested == "onnxruntime":
    path, reject = _try_resolve_artifact(rt, preferred="onnxruntime")
    if reject:
        # path_rejected → keep torch soft-stub
        return WorkerBuild(
            worker=_torch_worker(rt, conf=conf, model=model),
            backend_requested="onnxruntime",
            backend_live="torch",
            backend_reason=reject,
        )
    if path is None:
        # missing artifact → soft-stub (new or keep reason; prefer stable code)
        return WorkerBuild(
            worker=_torch_worker(rt, conf=conf, model=model),
            backend_requested="onnxruntime",
            backend_live="torch",
            backend_reason="ort_artifact_missing",  # or keep ort_loader_not_implemented if no artifact
        )
    # Optional dep probe WITHOUT module-level import onnxruntime
    # (mirror yolo_worker ImportError → extra message; factory soft-falls)
    try:
        import importlib.util
        if importlib.util.find_spec("onnxruntime") is None:
            raise ImportError("onnxruntime not installed")
    except ImportError:
        return WorkerBuild(
            worker=_torch_worker(rt, conf=conf, model=model),
            backend_requested="onnxruntime",
            backend_live="torch",
            backend_reason="ort_dep_missing",
        )
    # Live ORT: Ultralytics-native YOLO("*.onnx") via same worker class
    ort_worker = YoloDetectionWorker(
        weights=str(path),  # resolved .onnx, not .pt
        conf=conf,
        device=rt.device,  # device_for_backend already forces "cpu" for onnxruntime
        model=model,       # tests inject FakeModel claiming onnx path
    )
    return WorkerBuild(
        worker=ort_worker,
        backend_requested="onnxruntime",
        backend_live="onnxruntime",  # ONLY when actually taking this path
        backend_reason=None,
    )
```

**Honesty invariants (do not break):**
- Factory remains sole author of `backend_live` (Phase 8 summary).
- Never set `backend_live="onnxruntime"` unless artifact present + dep available + worker constructed with onnx weights (or injected model under live branch).
- TRT branch stays Phase 8 soft-stub (`trt_loader_not_implemented`).
- Still no `import onnxruntime` / `import tensorrt` at module top (test `test_factory_module_does_not_import_ort_trt` must keep passing; `find_spec` / lazy probe only inside branch).

**Related analog — `resolve_detector_artifact`:**  
`src/sentry_ai/config/artifact_paths.py` lines 128–202 (resolution order: explicit → env → weights_dir → cwd). Factory already calls this; do not reimplement path logic.

**Related analog — device policy:**  
`src/sentry_ai/config/profile_runtime.py` lines 63–64: `onnxruntime` → `"cpu"`. Live ORT worker inherits `rt.device` which is already cpu for cpu-fallback.

---

### `src/sentry_ai/models/detection/yolo_worker.py` (service, frame→detections)

**Analog:** same file — prefer **reuse** with onnx `weights=` over a new class (CONTEXT Claude's Discretion).  
**Plan:** 09-01.

**Constructor + `model=` injection** (lines 33–46):
```python
def __init__(
    self,
    weights: str = DEFAULT_WEIGHTS,
    conf: float = DEFAULT_CONF,
    device: str | None = None,
    model: Any | None = None,
) -> None:
    self._weights = weights
    self._device_arg = device
    self._device: str | None = None
    self._model = model
    self._conf_lock = threading.Lock()
    self._conf = self._validate_conf(conf)
    self._load_lock = threading.Lock()
```

**Conf duck-typing / validation** (lines 50–65) — ORT path must keep identical conf API (ORT-02 runtime adjustability foundation):
```python
@staticmethod
def _validate_conf(conf: float) -> float:
    value = float(conf)
    if value < 0.0 or value > 1.0:
        raise ValueError(f"conf must be in [0, 1], got {conf!r}")
    return value

def set_conf(self, conf: float) -> None:
    value = self._validate_conf(conf)
    with self._conf_lock:
        self._conf = value

def get_conf(self) -> float:
    with self._conf_lock:
        return self._conf
```

**Ultralytics load path** (lines 69–107) — already format-agnostic: `YOLO(self._weights)` works for `.pt` and `.onnx` when onnxruntime is installed:
```python
def _ensure_model(self) -> Any:
    if self._model is not None:
        return self._model
    with self._load_lock:
        if self._model is not None:
            return self._model
        configure_model_cache()
        try:
            from ultralytics import YOLO  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "ultralytics is required for YoloDetectionWorker. "
                "Install the detect extra: uv sync --extra detect"
            ) from exc
        self._device = resolve_device(self._device_arg)
        logger.info(
            "Loading YOLO weights=%s device=%s",
            self._weights,
            self._device,
        )
        model = YOLO(self._weights)
        ...
```

**Process → mapping** (lines 111–137) — frozen DetectionLoop contract; ORT must still call `results_to_detections`:
```python
results = model.predict(
    source=image_bgr,
    conf=conf,
    imgsz=DEFAULT_IMGSZ,
    device=device,
    verbose=False,
    save=False,
)
if not results:
    return []
return results_to_detections(results[0])
```

**Optional change (only if needed):** document that `_weights` may be `.onnx`; optional log tag when suffix is `.onnx`. Avoid custom ORT `InferenceSession` (CONTEXT: prefer Ultralytics-native).

**Optional-dep message analog** (depth worker ImportError → extra name):  
`src/sentry_ai/models/depth/worker.py` ~99+ and `tests/test_depth_worker.py` lines 199–216 (`match="extra depth|--extra depth"`). If YOLO load fails because onnxruntime missing *inside* worker (not factory probe), message should mention `onnx` extra similarly.

---

### `src/sentry_ai/models/detection/mapping.py` (utility, transform)

**Analog:** same file — **do not rewrite** for ORT; parity tests prove reuse.  
**Plan:** 09-02 (ORT-02 / ORT-04).

**Public API** (lines 55–110):
```python
def results_to_detections(result: Any) -> list[Detection]:
    """Convert one Ultralytics Results-like object to ``list[Detection]``.

    Empty or missing boxes yield ``[]`` (not ``None``). Completeness is
    decided by the perception store / loop, not this mapper.
    """
    ...
    detections.append(
        Detection(
            class_name=_class_name(names, cls_id),
            confidence=conf,
            bbox_xyxy=(x1, y1, x2, y2),
        )
    )
```

**Wire contract notes:**
- `Detection.source` defaults to `"fixed"` in schema (`src/sentry_ai/schemas/perception.py` lines 48–57) — mapper omits `source`; default supplies ORT-02.
- Duck-typed boxes: `xyxy` / `conf` / `cls` + optional tensor `.cpu().numpy()` path (`_to_sequence`, lines 16–34).
- No ultralytics import in mapping module — golden fixtures use `SimpleNamespace` / fake boxes.

**Do not add** custom ORT decoder; Ultralytics `predict` on onnx already returns Results-like objects that this mapper consumes.

---

### `pyproject.toml` optional extras (config)

**Analog:** existing `detect` / `depth` extras (lines 33–52).  
**Plan:** 09-01 (ORT-03).

```toml
[project.optional-dependencies]
dev = [
  "pytest>=8",
  "ruff>=0.8",
  "httpx>=0.28",
]
# Fixed-class detection (Phase 3). Headless OpenCV variant avoids GUI conflict
# with core opencv-python-headless. Install: uv sync --extra dev --extra detect
detect = [
  "ultralytics-opencv-headless>=8.4.33,<9",
]
# Monocular depth (Phase 4). HF Transformers DAV2 Small. Install:
#   uv sync --extra dev --extra depth
# Combined with detection: uv sync --extra dev --extra detect --extra depth
depth = [
  "torch>=2.2,<3",
  "transformers>=4.45,<6",
  "huggingface-hub>=0.23,<2",
  "pillow>=10,<13",
]
```

**Pattern to copy for new `onnx` extra:**
```toml
# Live ONNX Runtime path for fixed-class YOLO (Phase 9). CPU ORT is enough
# for CI/makers; GPU ORT is optional system install — not required in CI.
# Install: uv sync --extra dev --extra detect --extra onnx
onnx = [
  "onnxruntime>=1.20,<1.29",
]
```

**Rules from CONTEXT:**
- Pin range `onnxruntime>=1.20,<1.29` (prefer 1.28.x within range).
- **No** `tensorrt` pip extra this phase.
- Keep `detect` separate (ultralytics); live ORT needs **both** detect + onnx in practice.
- Comment block style: phase note + install one-liner (match detect/depth).

---

### Export docs (docs honesty update)

**Analogs:**  
- `docs/export/yolo26-onnx-tensorrt.md` (lines 1–89)  
- `docs/export/README.md` (lines 1–68)  
- Keyword tests: `tests/test_export_docs.py`

**Current honesty that Phase 9 must revise carefully** (`yolo26-onnx-tensorrt.md` lines 3–5, 87–89):
```markdown
Export fixed-class **YOLO26** weights with Ultralytics `model.export`. Live
Sentry detection still runs the **PyTorch** Ultralytics path; these recipes are
for offline edge packaging.
...
`preferred_backend: tensorrt` on the jetson profile is a **device policy /
export target hint**. Live `sentry serve` still uses PyTorch unless a future
InferenceBackend ships.
```

**And README** (lines 3–18): "Live inference stays PyTorch unless a future backend ships."

**Update pattern (keyword-test friendly):**
- State live ORT **when** `preferred_backend=onnxruntime` + valid `.onnx` + `onnx` extra.
- Keep TRT as non-live / export-target-only (Phase 10).
- Document: `uv sync --extra detect --extra onnx`.
- Document env: `SENTRY_DETECTOR_ONNX`, optional `SENTRY_ARTIFACT_ROOT`.
- Keep: on-device TRT rules, AGPL, no invented FPS, CI does not require Jetson/GPU ORT.
- Soft-stub honesty: missing artifact/deps → torch + reason (not silent ORT claim).

---

### `tests/test_detection_factory.py` (test matrix extension)

**Analog:** same file — Phase 8 profile matrix + soft-stub asserts.  
**Plan:** 09-01 + 09-02.

**FakeModel inject** (lines 18–22) — reuse for live ORT without weights:
```python
class FakeModel:
    """Minimal injectable model so tests never download weights."""

    def predict(self, **kwargs: Any) -> list[Any]:
        return []
```

**Current soft-stub cases that change under live conditions** (lines 49–66):
```python
def test_cpu_fallback_ort_soft_stub() -> None:
    rt = _rt_for_profile("cpu-fallback")
    build = build_detection_worker(rt, model=FakeModel())
    assert build.backend_requested == "onnxruntime"
    assert build.backend_live == "torch"
    assert build.backend_reason == "ort_loader_not_implemented"
    ...

@pytest.mark.parametrize(
    "profile",
    ["desktop-gpu", "jetson", "cpu-fallback"],
)
def test_backend_live_never_ort_or_trt(profile: str) -> None:
    ...
    assert build.backend_live not in {"onnxruntime", "tensorrt"}
```

**Extension matrix (copy structure):**

| Case | Setup | Expect |
|------|--------|--------|
| cpu-fallback, no artifact | default FakeModel | `live=torch`, reason artifact-missing or soft reason (not `ort_loader_not_implemented` if that code is removed for "no path") |
| cpu-fallback, path_rejected | env outside roots | `live=torch`, `backend_reason=="path_rejected"` |
| cpu-fallback, dep missing | artifact present, no onnxruntime | `live=torch`, `backend_reason=="ort_dep_missing"` |
| cpu-fallback, live ORT | tmp `.onnx` + find_spec ok + `model=` | `live=onnxruntime`, `reason is None`, worker `_weights` ends with `.onnx` |
| jetson TRT | unchanged | still soft-stub `trt_loader_not_implemented` |
| desktop-gpu torch | unchanged | `live=torch`, reason None |
| module import hygiene | `inspect.getsource` | still no top-level `import onnxruntime` / `tensorrt` |

**Artifact fixture pattern** — copy from `tests/test_artifact_paths.py` lines 19–31:
```python
weights_dir = tmp_path / "weights"
weights_dir.mkdir()
artifact = weights_dir / "yolo26n.onnx"
artifact.write_bytes(b"fake-onnx")
# monkeypatch SENTRY_MODEL_CACHE / configure_model_cache or env SENTRY_DETECTOR_ONNX
```

**Conf duck-type assert already present** (lines 69–78) — keep; apply to live ORT worker too:
```python
def test_worker_duck_type_process_conf() -> None:
    ...
    assert hasattr(w, "process")
    assert hasattr(w, "get_conf")
    assert hasattr(w, "set_conf")
    w.set_conf(0.4)
    assert w.get_conf() == pytest.approx(0.4)
```

**Rewrite note for `test_backend_live_never_ort_or_trt`:**  
Parametrize must no longer claim "never ORT" for all profiles without fixtures. Split into:
1. Without artifact/deps → never live ORT/TRT.
2. With live ORT fixtures → `backend_live == "onnxruntime"` allowed only for that case.
3. TRT still never live in Phase 9.

---

### Parity / golden tests (09-02)

**Analogs:**
1. `tests/test_detection_mapping.py` — pure mapper golden with duck-typed Results  
2. `tests/test_detection_worker.py` — FakeModel + `image_frame_factory` end-to-end process  
3. Optional: `tests/test_backend_honesty_status.py` — status fields for live ORT (inject `backend_live="onnxruntime"`)

**Mapping golden pattern** (`test_detection_mapping.py` lines 13–72):
```python
class _FakeBoxes:
    def __init__(self, xyxy, conf, cls): ...
    def __len__(self) -> int: ...

def make_fake_yolo_result(*, boxes, names=None) -> SimpleNamespace:
    return SimpleNamespace(
        boxes=boxes,
        names=names if names is not None else {0: "person", 1: "bicycle", 2: "car"},
    )

def test_known_boxes_map_to_detections() -> None:
    dets = results_to_detections(result)
    assert dets[0].class_name == "person"
    assert dets[0].confidence == pytest.approx(0.91)
    assert dets[0].bbox_xyxy == (10.0, 20.0, 100.5, 200.25)
    # source defaults to fixed on Detection schema
```

**Worker process parity** (`test_detection_worker.py` lines 19–80):
```python
class FakeModel:
    def predict(self, **kwargs: Any) -> list[Any]:
        self.calls.append(kwargs)
        ...
        return [SimpleNamespace(boxes=boxes, names={0: "person"})]

worker = YoloDetectionWorker(model=model, conf=0.25)
dets = worker.process(frame)
assert dets[0].class_name == "person"
assert call["conf"] == pytest.approx(0.25)
```

**ORT-specific golden strategy (CONTEXT discretion):**  
Inject fake YOLO model on live ORT factory branch (artifact path present, `model=FakeOrtModel`) so CI never needs real onnxruntime GPU or Jetson. Optionally `pytest.importorskip("onnxruntime")` only for a marked optional integration test — default suite remains mock-based (ORT-04).

**Detection contract asserts for parity:**
```python
assert d.class_name == expected
assert d.confidence == pytest.approx(...)
assert tuple(d.bbox_xyxy) == expected_xyxy
assert d.source == "fixed"  # schema default; ORT-02
```

---

### `tests/test_export_docs.py` (keyword tests)

**Analog:** same file (EDGE-03).  
**Plan:** 09-01 docs + 09-02 doc honesty.

**Read helper** (lines 7–26):
```python
REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = REPO_ROOT / "docs" / "export"

def _read(name: str) -> str:
    path = EXPORT_DIR / name
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")
```

**Existing keyword style** (lines 44–58) — extend, do not replace TRT honesty:
```python
def test_yolo26_onnx_tensorrt_on_device_and_no_engine_copy() -> None:
    text = _read("yolo26-onnx-tensorrt.md")
    lowered = text.lower()
    assert "onnx" in lowered
    assert "tensorrt" in lowered
    assert "on-device" in lowered or "on device" in lowered
    ...
```

**New keywords to require after docs update:**
- `onnxruntime` or `onnx runtime` / extra name `onnx`
- `backend_live` or honest phrasing "live" + onnxruntime conditions
- `uv sync` + `onnx` extra install
- Still: no invented FPS; CI does not require Jetson; TRT on-device / never-copy
- Soft-stub / fallback language when artifact or dep missing

**Negative care:** Do not leave absolute "live always PyTorch" without ORT exception — old README lines 15–16 will fail product honesty once Phase 9 ships.

---

## Shared Patterns

### Factory sole author of `backend_live`
**Source:** `src/sentry_ai/models/detection/factory.py` + Phase 8 `08-01-SUMMARY.md`  
**Apply to:** factory only; status/banner/API pass-through (already Phase 8).  
- Success ORT: `backend_live="onnxruntime"`, `backend_reason=None`  
- Soft fall: `backend_live="torch"` + stable reason  
- Never invent live ORT in routes (`routes_preview.py` comment: never recompute live from preferred)

### Stable reason codes
**Source:** factory Phase 8 + CONTEXT  
**Apply to:** factory ORT branch  

| Reason | When |
|--------|------|
| `path_rejected` | explicit/env path fails allowlist (`ValueError` from resolver) |
| `ort_dep_missing` | onnxruntime not importable / find_spec None (new Phase 9) |
| `ort_artifact_missing` or legacy soft code | preferred ORT but no `.onnx` found |
| `ort_loader_not_implemented` | **retire** for true live path; only keep if intentional "not yet" subcase |
| `trt_loader_not_implemented` | unchanged Phase 9 |
| `unsupported_backend` | openvino / unknown |

### Ultralytics-native load (no custom ORT session)
**Source:** CONTEXT + `YoloDetectionWorker._ensure_model`  
**Apply to:** live ORT worker construction  
- `YOLO("path/to/yolo26n.onnx")` + existing `predict` + `results_to_detections`  
- Out of scope: hand-written decoder / raw `InferenceSession`

### `model=` injection for tests (no weight download)
**Source:** `yolo_worker.py`, `test_detection_factory.py`, `test_detection_worker.py`  
**Apply to:** all unit tests for factory/worker/parity  
```python
build = build_detection_worker(rt, conf=0.25, model=FakeModel())
```

### Optional extras install messaging
**Source:** `pyproject.toml` detect/depth comments; worker ImportError strings  
**Apply to:** `onnx` extra + any ImportError paths  
```text
Install the onnx extra: uv sync --extra detect --extra onnx
```

### Conf duck-typing (ModelWorker-adjacent)
**Source:** `YoloDetectionWorker` get/set_conf + factory `test_worker_duck_type_process_conf`  
**Apply to:** live ORT worker instances  
- Same `_validate_conf` [0, 1]  
- Thread-safe lock around conf  
- `process` reads conf at call time (not frozen at load)

### Detection wire contract
**Source:** `schemas/perception.py` + `results_to_detections`  
**Apply to:** ORT-02 parity  
```python
class Detection(BaseModel):
    class_name: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float] | list[float]
    source: Literal["fixed", "open_vocab"] = "fixed"
```

### Spine freeze
**Source:** CONTEXT + Phase 8  
**Apply to:** all plans  
- Do **not** modify DetectionLoop / FrameBus / PerceptionStore / `/v1` wire for this phase  
- Only factory + worker weights path (+ docs/extras/tests)

### Artifact allowlist
**Source:** `src/sentry_ai/config/artifact_paths.py`  
**Apply to:** factory live branch only via `_try_resolve_artifact`  
- Stems: `yolo26n|s|m`  
- Suffix for ORT: `.onnx`  
- Env: `SENTRY_DETECTOR_ONNX`, `SENTRY_ARTIFACT_ROOT`

### Doc keyword testing
**Source:** `tests/test_export_docs.py`, `tests/test_desktop_docs.py`  
**Apply to:** export doc updates  
- Read file → `lowered = text.lower()` → assert presence of honesty keywords  
- No Jetson / no real export in pytest

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| _(none)_ | — | — | Phase 8 factory + YOLO worker + mapping + extras + doc tests cover all Phase 9 surfaces |

**Partial / invent-with-care only:**
- Reason code `ort_dep_missing` — new string; structure mirrors `path_rejected` soft return.
- Live `backend_live="onnxruntime"` success tests — invert Phase 8 "never ORT" asserts; use artifact fixtures from `test_artifact_paths.py`.

---

## Plan → Analog Quick Index

### 09-01 — Live Ultralytics-native ORT worker path + `onnx` extra

| Work item | Copy from |
|-----------|-----------|
| Replace soft-stub branch | `factory.py` lines 131–139 structure; outcomes from recommended live-branch shape above |
| Artifact resolve | `factory.py` `_try_resolve_artifact` + `artifact_paths.py` |
| Worker weights path | `YoloDetectionWorker(weights=str(onnx_path), conf=, device=, model=)` |
| Optional extra | `pyproject.toml` detect/depth block style |
| Docs install + live conditions | `docs/export/*` + keyword tests in `test_export_docs.py` |
| Keep TRT soft-stub | `factory.py` lines 141–149 unchanged |

### 09-02 — Detection parity / golden tests

| Work item | Copy from |
|-----------|-----------|
| Factory matrix extension | `tests/test_detection_factory.py` + artifact tmp_path from `test_artifact_paths.py` |
| Mapping golden | `tests/test_detection_mapping.py` (`_FakeBoxes`, `make_fake_yolo_result`) |
| Process parity | `tests/test_detection_worker.py` (`FakeModel`, conf/process asserts) |
| Conf duck-typing | factory `test_worker_duck_type_process_conf` + worker conf tests |
| Status honesty optional | `tests/test_backend_honesty_status.py` inject live=onnxruntime |
| No Jetson | mock/`model=` only; optional importorskip for real ORT |

---

## Metadata

**Analog search scope:**  
`src/sentry_ai/models/detection/`, `src/sentry_ai/config/artifact_paths.py`, `src/sentry_ai/config/profile_runtime.py`, `src/sentry_ai/schemas/perception.py`, `pyproject.toml`, `docs/export/`, `tests/test_detection_*.py`, `tests/test_export_docs.py`, `tests/test_artifact_paths.py`, `tests/test_backend_honesty_status.py`, `tests/test_depth_worker.py`, `.planning/phases/08-backend-selection-honesty/`, `.planning/phases/09-live-ort-fixed-class-yolo/09-CONTEXT.md`

**Files scanned:** ~25  
**Pattern extraction date:** 2026-08-09  
**Primary analogs for 09-01 / 09-02:** Phase 8 `factory.py` + `yolo_worker.py` + `test_detection_factory.py` (exact); mapping/docs/extras as supporting exact matches.

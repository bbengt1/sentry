# Phase 10: Live TensorRT Fixed-Class YOLO - Pattern Map

**Mapped:** 2026-08-10  
**Files analyzed:** 12  
**Analogs found:** 12 / 12  

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sentry_ai/models/detection/factory.py` | service (factory) | request-response / branch | same file — Phase 9 ORT live branch (lines 144–179) | exact |
| `src/sentry_ai/models/detection/yolo_worker.py` | service (worker) | transform (frame→detections) | same file (`model=` inject + `YOLO(weights)`) | exact |
| `src/sentry_ai/models/detection/mapping.py` | utility | transform | same file (`results_to_detections`) | exact |
| `src/sentry_ai/config/profiles/jetson.yaml` | config | N/A | same file (comments only; Phase 9 left TRT non-live) | exact |
| `docs/export/yolo26-onnx-tensorrt.md` | config/docs | N/A | same file (Phase 9 live ORT honesty tables) | exact |
| `docs/export/jetson-packaging.md` | config/docs | N/A | same file (on-device / no-prebuilt rules) | exact |
| `docs/export/README.md` | config/docs | N/A | same file (live vs offline matrix) | exact |
| `docs/architecture.md` | config/docs | N/A | same file (live ORT paragraph) | exact |
| `docs/configuration.md` | config/docs | N/A | same file (preferred_backend honesty) | exact |
| `tests/test_detection_factory.py` | test | request-response | same file (ORT live matrix + soft-falls) | exact |
| `tests/test_trt_parity.py` | test | transform | `tests/test_ort_parity.py` | exact |
| `tests/test_backend_honesty_status.py` | test | request-response | same file (live ORT triple + TRT soft-stub) | exact |
| `tests/test_export_docs.py` | test | N/A (keyword) | same file (live ORT + on-device keywords) | exact |
| `tests/test_pyproject_onnx_extra.py` | test | N/A (static) | same file `test_no_tensorrt_optional_extra` — **keep** | exact |

**Plans covered:** 10-01 (live TRT factory + tests), 10-02 (on-device lifecycle + Jetson packaging docs).

**Unchanged / frozen (do not modify):** `loop.py`, FrameBus, PerceptionStore, `/v1` routes, `artifact_paths.py` (already resolves `.engine`), `pyproject.toml` extras (**no** `tensorrt` extra).

---

## Pattern Assignments

### `src/sentry_ai/models/detection/factory.py` (service, branch selection)

**Analog:** same file — Phase 9 ORT live branch (lines 72–74, 144–179) is the **1:1 structural template**.  
**Plan:** 10-01 primary — replace TRT soft-stub with real live loader branch.

**Module contract / no module-level TRT** (lines 1–24) — keep; update docstring for Phase 10:
```python
"""Serve-time fixed-class detection worker factory (BACK-01, EDGE-RT-02, ORT-01).

Branches on ``ProfileRuntime.preferred_backend``. Torch path is fully live via
``YoloDetectionWorker``. Phase 9: preferred ``onnxruntime`` is live when an
allowlisted ``.onnx`` artifact resolves and ``onnxruntime`` is importable;
...
Does not import ``onnxruntime`` or ``tensorrt`` at module level — dep probe uses
``importlib.util.find_spec`` only.
"""
from sentry_ai.config.artifact_paths import resolve_detector_artifact
from sentry_ai.config.profile_runtime import ProfileRuntime
from sentry_ai.models.cache import configure_model_cache
from sentry_ai.models.detection.yolo_worker import YoloDetectionWorker
```

**WorkerBuild contract** (lines 33–40) — keep unchanged; only `backend_live` / `backend_reason` values change for TRT success path:
```python
@dataclass(frozen=True)
class WorkerBuild:
    """Detection worker plus honest preferred-vs-live backend identity."""

    worker: Any  # ModelWorker duck-type
    backend_requested: str
    backend_live: str
    backend_reason: str | None = None
```

**Dep probe pattern** (lines 72–74) — copy for TRT:
```python
def _onnxruntime_available() -> bool:
    """True when the onnxruntime package is importable (no hard import)."""
    return importlib.util.find_spec("onnxruntime") is not None
```

**Recommended TRT probe (mirror ORT):**
```python
def _tensorrt_available() -> bool:
    """True when the system tensorrt package is importable (no hard import)."""
    return importlib.util.find_spec("tensorrt") is not None
```

**Artifact resolution already wired for TRT** (lines 77–116) — live branch must **consume** `path` instead of discarding `_path`:
```python
def _try_resolve_artifact(
    rt: ProfileRuntime,
    *,
    preferred: str,
) -> tuple[Path | None, str | None]:
    ...
    if preferred == "onnxruntime":
        env_value = os.environ.get("SENTRY_DETECTOR_ONNX")
    elif preferred == "tensorrt":
        env_value = os.environ.get("SENTRY_DETECTOR_ENGINE")
    ...
```

**Phase 9 ORT live branch — exact structure to copy** (lines 144–179):
```python
if requested == "onnxruntime":
    path, reject = _try_resolve_artifact(rt, preferred="onnxruntime")
    if reject:
        return WorkerBuild(
            worker=_torch_worker(rt, conf=conf, model=model),
            backend_requested="onnxruntime",
            backend_live="torch",
            backend_reason=reject,
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
    # Live ORT: Ultralytics-native YOLO("*.onnx") via same worker class.
    ort_worker = YoloDetectionWorker(
        weights=str(path),
        conf=conf,
        device=rt.device,
        model=model,
    )
    return WorkerBuild(
        worker=ort_worker,
        backend_requested="onnxruntime",
        backend_live="onnxruntime",
        backend_reason=None,
    )
```

**Phase 8 soft-stub to replace** (lines 181–189) — this is the exact branch 10-01 rewrites:
```python
if requested == "tensorrt":
    _path, reject = _try_resolve_artifact(rt, preferred="tensorrt")
    reason = reject or "trt_loader_not_implemented"
    return WorkerBuild(
        worker=_torch_worker(rt, conf=conf, model=model),
        backend_requested="tensorrt",
        backend_live="torch",
        backend_reason=reason,
    )
```

**Recommended live-TRT branch shape (copy ORT structure, TRT outcomes):**
```python
if requested == "tensorrt":
    path, reject = _try_resolve_artifact(rt, preferred="tensorrt")
    if reject:
        return WorkerBuild(
            worker=_torch_worker(rt, conf=conf, model=model),
            backend_requested="tensorrt",
            backend_live="torch",
            backend_reason=reject,  # path_rejected
        )
    if path is None:
        return WorkerBuild(
            worker=_torch_worker(rt, conf=conf, model=model),
            backend_requested="tensorrt",
            backend_live="torch",
            backend_reason="trt_artifact_missing",
        )
    if not _tensorrt_available():
        return WorkerBuild(
            worker=_torch_worker(rt, conf=conf, model=model),
            backend_requested="tensorrt",
            backend_live="torch",
            backend_reason="trt_dep_missing",
        )
    # Live TRT: Ultralytics-native YOLO("*.engine") via same worker class.
    trt_worker = YoloDetectionWorker(
        weights=str(path),  # resolved .engine, not .pt
        conf=conf,
        device=rt.device,  # device_for_backend → cuda:N for tensorrt
        model=model,       # tests inject FakeModel claiming engine path
    )
    return WorkerBuild(
        worker=trt_worker,
        backend_requested="tensorrt",
        backend_live="tensorrt",  # ONLY when actually taking this path
        backend_reason=None,
    )
```

**Honesty invariants (do not break):**
- Factory remains sole author of `backend_live` (Phase 8).
- Never set `backend_live="tensorrt"` unless artifact present + system `tensorrt` findable + worker constructed with `.engine` weights (or injected model under live branch).
- Never `import tensorrt` at module top (test `test_factory_module_does_not_import_ort_trt` must keep passing; `find_spec` only).
- **Never** call Ultralytics `check_tensorrt()` from factory (can auto-pip-install `tensorrt-cu*`).
- Retire `trt_loader_not_implemented` as default TRT outcome (same class of migration as ORT retired `ort_loader_not_implemented`).
- ORT branch stays Phase 9 live path (untouched).

**Related analog — device policy:**  
`src/sentry_ai/config/profile_runtime.py` lines 66–80: `tensorrt` → `cuda:0` / `cuda:N`. Live TRT worker inherits `rt.device` (already cuda-like). Docstring still says "not TRT runtime" — optional honesty tweak in 10-02, not required for code path.

**Related analog — artifact resolve:**  
`src/sentry_ai/config/artifact_paths.py` — suffix `.engine` for `preferred=="tensorrt"` already implemented. Do not reimplement path logic.

---

### `src/sentry_ai/models/detection/yolo_worker.py` (service, frame→detections)

**Analog:** same file — prefer **reuse** with `.engine` `weights=` over a new class (RESEARCH lock).  
**Plan:** 10-01 — **no code change expected**.

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
    ...
```

**Conf duck-typing** (lines 50–65) — TRT path must keep identical conf API (TRT-04):
```python
def set_conf(self, conf: float) -> None:
    value = self._validate_conf(conf)
    with self._conf_lock:
        self._conf = value

def get_conf(self) -> float:
    with self._conf_lock:
        return self._conf
```

**Ultralytics load path** (lines 69–89) — already format-agnostic: `YOLO(self._weights)` works for `.pt`, `.onnx`, and `.engine` when system TensorRT + CUDA are available:
```python
model = YOLO(self._weights)
```

**Process → mapping** (lines 131–141) — frozen DetectionLoop contract; TRT must still call `results_to_detections`:
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

**Do not** add custom TRT Runtime / bindings / NMS decoder. Conf caveat for docs only: runtime conf works via Ultralytics postprocess NMS for default (non-`nms=True` baked) engines.

---

### `src/sentry_ai/models/detection/mapping.py` (utility, transform)

**Analog:** same file — **do not rewrite** for TRT; parity tests prove reuse.  
**Plan:** 10-01 parity only (TRT-04).

**Public API** (lines 55–108):
```python
def results_to_detections(result: Any) -> list[Detection]:
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
- `Detection.source` defaults to `"fixed"` in schema — mapper omits `source`; default supplies TRT-04.
- No ultralytics import in mapping module — golden fixtures use `SimpleNamespace` / fake boxes.
- Do not add custom TRT decoder; Ultralytics `predict` on engine already returns Results-like objects.

---

### `src/sentry_ai/config/profiles/jetson.yaml` (config comments)

**Analog:** same file — comment honesty only (no YAML field changes).  
**Plan:** 10-02.

**Current non-live comments** (lines 1–7):
```yaml
# Built-in runtime profile: NVIDIA Jetson edge (FOUND-06 / EDGE-02)
# preferred_backend=tensorrt is export target / device policy only.
# Live path remains PyTorch CUDA if available; build engines via export recipes.
...
  preferred_backend: tensorrt  # device policy → cuda:0 live PyTorch (not silent TRT)
```

**Update pattern:**
```yaml
# preferred_backend=tensorrt → live TRT when allowlisted .engine + system tensorrt
# importable; else soft torch fallback with honest reason (trt_artifact_missing /
# trt_dep_missing / path_rejected). Build engines on-device only.
...
  preferred_backend: tensorrt  # live TRT when .engine + system tensorrt present
```

Do **not** change `detector_tier`, `device_id`, or other field values.

---

### Export + product docs (docs honesty update)

**Analogs:**  
- `docs/export/yolo26-onnx-tensorrt.md` (lines 1–125)  
- `docs/export/jetson-packaging.md` (lines 1–80)  
- `docs/export/README.md` (lines 1–80)  
- `docs/architecture.md` (lines 67–71)  
- `docs/configuration.md` (lines 12–42)  
- Keyword tests: `tests/test_export_docs.py`

**Current honesty that Phase 10 must revise** (`yolo26-onnx-tensorrt.md` lines 11, 111–121):
```markdown
| **TensorRT** | Still **non-live** in serve (policy / export target until a future TRT phase); build **on-device** only |
...
`preferred_backend: tensorrt` on the jetson profile remains a **device policy /
export target hint** — live TensorRT is not claimed until a future phase.
...
- Live TensorRT `InferenceBackend` inside Sentry (future phase)
```

**And jetson-packaging** (lines 7–8, 24):
```markdown
Live Sentry inference remains **PyTorch** (Ultralytics + HF). TensorRT is an
**export / preferred_backend policy** target, not a shipped TRT runtime in v1.
...
| `preferred_backend` | `tensorrt` | Device policy / export target; live path still PyTorch |
```

**And export README** (line 12): "**TRT not live yet**"

**And architecture** (lines 70–71) / configuration (lines 36–37): soft torch until future TRT phase.

**Update pattern (keyword-test friendly) — mirror Phase 9 ORT honesty for TRT:**

| Surface | New honesty |
|---------|-------------|
| Live conditions | `preferred_backend=tensorrt` + allowlisted `.engine` + system `tensorrt` importable → `backend_live=tensorrt` |
| Soft fallback | missing artifact / dep / path_rejected → torch + `trt_artifact_missing` \| `trt_dep_missing` \| `path_rejected` |
| Install | **No** project `tensorrt` pip extra; JetPack / system TensorRT only (TRT-03) |
| Env | `SENTRY_DETECTOR_ENGINE`, optional `SENTRY_ARTIFACT_ROOT` |
| On-device | keep: build on target device, never copy, no prebuilt multi-SKU, measure on device, no invented FPS |
| Serve recipe | export on-device → place engine under allowlist → `sentry serve --profile jetson` |
| CI | default pytest never loads real `.engine` / requires Jetson / system TRT |

**Recommended live-TRT table row (copy ORT row style from yolo26 lines 7–9):**
```markdown
| **Live TRT** | `preferred_backend=tensorrt` + allowlisted `.engine` present + system `tensorrt` importable → `backend_live=tensorrt` (Ultralytics-native `YOLO("*.engine")`) |
| **Soft torch fallback** | Missing artifact, missing system `tensorrt`, or rejected path → live stays **torch** with an honest reason (`trt_artifact_missing` / `trt_dep_missing` / `path_rejected`) |
```

**Preserve (do not weaken):**
- On-device / never-copy / no-prebuilt (TRT-02)  
- No project `tensorrt` pip extra (TRT-03)  
- CI does not require Jetson  
- AGPL / THIRD_PARTY_MODELS  
- Dual-model VRAM: measure on device; no FPS claims

---

### `tests/test_detection_factory.py` (test matrix extension)

**Analog:** same file — Phase 9 ORT live matrix + soft-stub asserts.  
**Plan:** 10-01.

**FakeModel inject** (lines 19–23) — reuse:
```python
class FakeModel:
    """Minimal injectable model so tests never download weights."""

    def predict(self, **kwargs: Any) -> list[Any]:
        return []
```

**Current TRT soft-stub that must change** (lines 41–47):
```python
def test_jetson_tensorrt_soft_stub() -> None:
    rt = _rt_for_profile("jetson")
    build = build_detection_worker(rt, model=FakeModel())
    assert build.backend_requested == "tensorrt"
    assert build.backend_live == "torch"
    assert build.backend_reason == "trt_loader_not_implemented"
```

**Rewrite to artifact-missing default** (mirror `test_cpu_fallback_ort_soft_stub_artifact_missing` lines 50–58):
```python
def test_jetson_tensorrt_soft_stub_artifact_missing() -> None:
    """Default jetson without fixture engine soft-falls (not live TRT)."""
    rt = _rt_for_profile("jetson")
    build = build_detection_worker(rt, model=FakeModel())
    assert build.backend_requested == "tensorrt"
    assert build.backend_live == "torch"
    assert build.backend_reason == "trt_artifact_missing"
    assert isinstance(build.worker, YoloDetectionWorker)
    assert str(build.worker._weights).endswith(".pt")
```

**ORT live success pattern to mirror for TRT** (lines 73–97):
```python
def test_live_ort_success_with_artifact_and_dep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    onnx_path = tmp_path / "yolo26n.onnx"
    onnx_path.write_bytes(b"fake-onnx")
    monkeypatch.setattr(
        factory_mod, "_try_resolve_artifact",
        lambda rt, *, preferred: (onnx_path, None),
    )
    monkeypatch.setattr(factory_mod, "_onnxruntime_available", lambda: True)
    rt = _rt_for_profile("cpu-fallback")
    build = build_detection_worker(rt, model=FakeModel())
    assert build.backend_live == "onnxruntime"
    assert str(build.worker._weights).endswith(".onnx")
```

**TRT extension matrix (copy structure):**

| Case | Setup | Expect |
|------|--------|--------|
| jetson, no artifact | default FakeModel | `live=torch`, `trt_artifact_missing` |
| jetson, path_rejected | monkeypatch reject | `live=torch`, `path_rejected` |
| jetson, dep missing | `.engine` path + `_tensorrt_available=False` | `live=torch`, `trt_dep_missing` |
| jetson, live TRT | tmp `.engine` + dep True + `model=` | `live=tensorrt`, `reason is None`, worker `_weights` ends with `.engine` |
| never live TRT with `.pt` | live claim only if suffix `.engine` | suffix honesty guard |
| desktop-gpu torch | unchanged | `live=torch`, reason None |
| cpu-fallback ORT | unchanged Phase 9 | live ORT fixtures still work |
| without fixtures | all three profiles | `backend_live not in {onnxruntime, tensorrt}` (keep) |
| module import hygiene | `inspect.getsource` | still no top-level `import tensorrt` / `onnxruntime` |

**Import hygiene** (lines 209–216) — keep as-is:
```python
def test_factory_module_does_not_import_ort_trt() -> None:
    source = inspect.getsource(factory_mod)
    assert "import onnxruntime" not in source
    assert "import tensorrt" not in source
    ...
```

---

### `tests/test_trt_parity.py` (NEW — Detection / conf parity)

**Analog:** `tests/test_ort_parity.py` (full file, 166 lines) — **copy and adapt**.  
**Plan:** 10-01 (TRT-04).

**Module docstring + live-build helper** (lines 1–95) — rename ORT→TRT:
```python
"""TRT-04: live TRT factory path Detection parity via mocks only.

Proves schema-identical detections + runtime conf on the factory live TRT
branch without Jetson, system TensorRT, or real YOLO("*.engine") loads in default CI.
"""
...
def _live_trt_build(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    model: FakeModel,
    *,
    conf: float = 0.25,
) -> WorkerBuild:
    engine_path = tmp_path / "yolo26n.engine"
    engine_path.write_bytes(b"fake-engine")

    monkeypatch.setattr(
        factory_mod,
        "_try_resolve_artifact",
        lambda rt, *, preferred: (engine_path, None),
    )
    monkeypatch.setattr(factory_mod, "_tensorrt_available", lambda: True)

    rt = profile_runtime(load_config(profile="jetson"))  # not cpu-fallback
    build = build_detection_worker(rt, conf=conf, model=model)

    assert build.backend_live == "tensorrt", (
        f"expected live TRT path, got live={build.backend_live!r} "
        f"reason={build.backend_reason!r}"
    )
    assert build.backend_requested == "tensorrt"
    assert build.backend_reason is None
    assert str(build.worker._weights).endswith(".engine")
    assert not str(build.worker._weights).endswith(".pt")
    return build
```

**Contract tests to copy** (lines 98–166):

| ORT test | TRT twin |
|----------|----------|
| `test_ort_process_detection_contract` | `test_trt_process_detection_contract` — person/0.88/bbox/`source=="fixed"` |
| `test_ort_set_conf_applies_on_next_process` | `test_trt_set_conf_applies_on_next_process` — set_conf(0.5) → predict conf |
| `test_ort_empty_predict_returns_empty_list` | `test_trt_empty_predict_returns_empty_list` — `[]` not None |
| `test_ort_live_weights_are_onnx_not_pt` | `test_trt_live_weights_are_engine_not_pt` — suffix honesty |

**Reuse FakeModel / _FakeBoxes** from ort_parity (lines 26–59) — identical; no real engine load.

**Detection contract asserts:**
```python
assert d.class_name == "person"
assert d.confidence == pytest.approx(0.88)
assert d.bbox_xyxy == (10.0, 20.0, 30.0, 40.0)
assert d.source == "fixed"
```

---

### `tests/test_backend_honesty_status.py` (status pass-through)

**Analog:** same file — soft-stub TRT + live ORT triples.  
**Plan:** 10-01.

**Update soft-stub reason fixtures** (lines 70–104, 204–220) that still use `trt_loader_not_implemented`:
```python
# BEFORE
backend_reason="trt_loader_not_implemented"
# AFTER (example soft-fall)
backend_reason="trt_artifact_missing"  # or trt_dep_missing for dep case
```

**Live ORT pattern to mirror for live TRT** (lines 161–181):
```python
def test_api_status_honesty_onnxruntime_live() -> None:
    loop, app = _running_app(
        backend_requested="onnxruntime",
        backend_live="onnxruntime",
        backend_reason=None,
    )
    ...
    assert data["backend_live"] == "onnxruntime"
    assert data.get("backend_reason") is None
```

**Add live TRT twin:**
```python
def test_api_status_honesty_tensorrt_live() -> None:
    """Live TRT: requested=tensorrt live=tensorrt reason=None pass-through."""
    loop, app = _running_app(
        backend_requested="tensorrt",
        backend_live="tensorrt",
        backend_reason=None,
    )
    ...
    assert data["backend_live"] == "tensorrt"
    assert data.get("backend_reason") is None
```

**Also add** `test_status_snapshot_live_trt_fields` mirroring lines 185–200 (live ORT snapshot).

**Soft-stub route test** (lines 86–104): keep “never invent live TRT without factory authorship” — soft-stub fixture should use new reason codes; live claim only in dedicated live tests.

---

### `tests/test_export_docs.py` (keyword tests)

**Analog:** same file — Phase 9 live ORT keywords + on-device rules.  
**Plan:** 10-02.

**Read helper** (lines 7–26) — keep.

**Live ORT keyword style** (lines 44–65) — add parallel live TRT test:
```python
def test_export_docs_live_trt_conditions_and_system_tensorrt() -> None:
    """Live fixed-class TRT conditions + system TensorRT (no pip pin) (TRT-01..03)."""
    yolo = _read("yolo26-onnx-tensorrt.md").lower()
    jetson = _read("jetson-packaging.md").lower()
    readme = _read("README.md").lower()
    blob = yolo + "\n" + jetson + "\n" + readme
    assert "live" in blob
    assert "tensorrt" in blob or "tensor rt" in blob
    assert ".engine" in (yolo + jetson + readme) or "engine" in blob
    # System / JetPack TRT — not project pip extra
    assert (
        "system" in blob
        or "jetpack" in blob
        or "no project" in blob
        or "no" in blob and "pip" in blob
    )
    # Soft-fallback honesty
    assert (
        "soft-fall" in blob
        or "soft fall" in blob
        or "missing" in blob
        or "fallback" in blob
    )
    # On-device rules still present
    assert "on-device" in blob or "on device" in blob
```

**Keep existing** `test_yolo26_onnx_tensorrt_on_device_and_no_engine_copy`, `test_jetson_packaging_honesty`, cross-device forbid tests — extend keywords if docs gain live language, do not drop on-device / no-prebuilt asserts.

**Negative care:** Do not leave absolute “live always PyTorch” / “TRT not live yet” / “until a future TRT phase” without live-TRT exception after Phase 10 ships.

---

### `tests/test_pyproject_onnx_extra.py` (static packaging)

**Analog:** same file — **must remain green; do not add tensorrt extra**.  
**Plan:** 10-02 hygiene.

**Keep** (lines 32–38):
```python
def test_no_tensorrt_optional_extra() -> None:
    extras = _optional_deps()
    assert "tensorrt" not in extras
    for name, deps in extras.items():
        joined = " ".join(deps).lower()
        assert "tensorrt" not in joined, f"tensorrt appears under extra {name!r}"
```

**No pyproject.toml change** this phase (unlike Phase 9 `onnx` extra).

---

## Shared Patterns

### Factory sole author of `backend_live`
**Source:** `src/sentry_ai/models/detection/factory.py` + Phase 8/9  
**Apply to:** factory only; status/banner/API pass-through (already Phase 8).  
- Success TRT: `backend_live="tensorrt"`, `backend_reason=None`  
- Soft fall: `backend_live="torch"` + stable reason  
- Never invent live TRT in routes

### Stable reason codes (TRT)
**Source:** Phase 9 ORT reason migration + RESEARCH  
**Apply to:** factory TRT branch  

| Reason | When |
|--------|------|
| `path_rejected` | explicit/env path fails allowlist (`ValueError` from resolver) |
| `trt_dep_missing` | `find_spec("tensorrt")` is None (new Phase 10) |
| `trt_artifact_missing` | preferred TRT but no `.engine` found |
| `trt_loader_not_implemented` | **retire** for implemented branch |
| `unsupported_backend` | openvino / unknown (unchanged) |

### Ultralytics-native load (no custom TRT session)
**Source:** CONTEXT/RESEARCH + `YoloDetectionWorker._ensure_model` + Phase 9 ORT  
**Apply to:** live TRT worker construction  
- `YOLO("path/to/yolo26n.engine")` + existing `predict` + `results_to_detections`  
- Out of scope: hand-written decoder / raw `tensorrt.Runtime` / bindings  
- Factory never calls Ultralytics `check_tensorrt()`

### `model=` injection for tests (no engine load / no weight download)
**Source:** `yolo_worker.py`, `test_detection_factory.py`, `test_ort_parity.py`  
**Apply to:** all unit tests for factory/worker/parity  
```python
build = build_detection_worker(rt, conf=0.25, model=FakeModel())
# live TRT: monkeypatch _try_resolve_artifact + _tensorrt_available
```

### No pip `tensorrt` extra (TRT-03)
**Source:** `tests/test_pyproject_onnx_extra.py::test_no_tensorrt_optional_extra` + RESEARCH  
**Apply to:** pyproject + docs  
```text
Use JetPack-bundled / system TensorRT — never pin tensorrt in project extras.
Verify: python -c "import tensorrt"
```

### Conf duck-typing (ModelWorker-adjacent)
**Source:** `YoloDetectionWorker` get/set_conf + factory `test_worker_duck_type_process_conf`  
**Apply to:** live TRT worker instances  
- Same `_validate_conf` [0, 1]  
- Thread-safe lock around conf  
- `process` reads conf at call time (not frozen at load)

### Detection wire contract
**Source:** `schemas/perception.py` + `results_to_detections` + `test_ort_parity.py`  
**Apply to:** TRT-04 parity  
```python
class Detection(BaseModel):
    class_name: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float] | list[float]
    source: Literal["fixed", "open_vocab"] = "fixed"
```

### Spine freeze
**Source:** RESEARCH + Phase 8/9  
**Apply to:** all plans  
- Do **not** modify DetectionLoop / FrameBus / PerceptionStore / `/v1` wire  
- Only factory TRT branch (+ docs / tests / jetson.yaml comments)

### Artifact allowlist
**Source:** `src/sentry_ai/config/artifact_paths.py` + factory `_try_resolve_artifact`  
**Apply to:** factory live branch only via existing resolver  
- Stems: `yolo26n|s|m`  
- Suffix for TRT: `.engine`  
- Env: `SENTRY_DETECTOR_ENGINE`, `SENTRY_ARTIFACT_ROOT`

### Doc keyword testing
**Source:** `tests/test_export_docs.py`  
**Apply to:** export + packaging + architecture/configuration honesty  
- Read file → `lowered = text.lower()` → assert live TRT conditions + on-device / system TRT / no pip pin  
- No Jetson / no real engine in pytest

### Mock-only CI (no real TensorRT)
**Source:** `tests/test_ort_parity.py` + RESEARCH EDGE-CI spirit  
**Apply to:** factory + parity suites  
- Monkeypatch resolve + dep probe; inject FakeModel  
- Optional real-engine marker: out of scope for Phase 10 default suite

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| _(none)_ | — | — | Phase 9 ORT live path + factory/worker/mapping/docs/tests cover all Phase 10 surfaces |

**Partial / invent-with-care only:**
- Reason codes `trt_artifact_missing` / `trt_dep_missing` — new strings; structure mirrors ORT `ort_artifact_missing` / `ort_dep_missing`.
- Live `backend_live="tensorrt"` success tests — invert Phase 8 “never TRT” soft-stub; use monkeypatch fixtures from `test_ort_parity.py` / `test_detection_factory.py`.
- Optional factory CUDA probe — RESEARCH discretion; start with `find_spec("tensorrt")` only (mirror ORT).

---

## Plan → Analog Quick Index

### 10-01 — Live Ultralytics-native TRT worker path (system TensorRT)

| Work item | Copy from |
|-----------|-----------|
| Replace soft-stub branch | `factory.py` lines 181–189 structure; outcomes from ORT live branch 144–179 |
| Dep probe | `factory.py` `_onnxruntime_available` → `_tensorrt_available` |
| Artifact resolve | `factory.py` `_try_resolve_artifact` + env `SENTRY_DETECTOR_ENGINE` (already wired) |
| Worker weights path | `YoloDetectionWorker(weights=str(engine_path), conf=, device=, model=)` |
| Factory matrix | `tests/test_detection_factory.py` ORT live/soft-fall tests |
| Parity module | **new** `tests/test_trt_parity.py` ← full copy of `tests/test_ort_parity.py` |
| Status honesty | `tests/test_backend_honesty_status.py` live ORT triple + update TRT soft reasons |
| Import hygiene | `test_factory_module_does_not_import_ort_trt` unchanged |
| No tensorrt extra | `test_no_tensorrt_optional_extra` must stay green |
| Keep ORT live | `factory.py` lines 144–179 untouched |

### 10-02 — On-device engine lifecycle + Jetson packaging notes

| Work item | Copy from |
|-----------|-----------|
| Live TRT conditions table | Phase 9 ORT rows in `yolo26-onnx-tensorrt.md` lines 7–9 |
| On-device / never-copy / no-prebuilt | existing sections in same docs (preserve, reframe around live) |
| Jetson packaging system TRT | `jetson-packaging.md` system TRT row + profile table |
| Export README matrix | `docs/export/README.md` live ORT section → add live TRT |
| Architecture / configuration | ORT live paragraphs → parallel TRT honesty |
| jetson.yaml comments | same file comment-only update |
| Keyword tests | `tests/test_export_docs.py` live ORT keyword test style |
| Serve recipe | RESEARCH install block: export_yolo `--format engine` → serve jetson |
| No pyproject change | TRT-03 / static test |

---

## Metadata

**Analog search scope:**  
`src/sentry_ai/models/detection/` (factory, yolo_worker, mapping), `src/sentry_ai/config/artifact_paths.py`, `src/sentry_ai/config/profile_runtime.py`, `src/sentry_ai/config/profiles/jetson.yaml`, `docs/export/*`, `docs/architecture.md`, `docs/configuration.md`, `tests/test_detection_factory.py`, `tests/test_ort_parity.py`, `tests/test_backend_honesty_status.py`, `tests/test_export_docs.py`, `tests/test_pyproject_onnx_extra.py`, `.planning/phases/09-live-ort-fixed-class-yolo/09-PATTERNS.md`, `.planning/phases/08-backend-selection-honesty/08-PATTERNS.md`, `.planning/phases/10-live-tensorrt-fixed-class-yolo/10-RESEARCH.md`

**Files scanned:** ~28  
**Pattern extraction date:** 2026-08-10  
**Primary analogs for 10-01 / 10-02:** Phase 9 ORT live `factory.py` branch + `tests/test_ort_parity.py` (exact isomorphism); TRT soft-stub + docs honesty surfaces as rewrite targets.

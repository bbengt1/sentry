# Phase 8: Backend Selection & Honesty - Research

**Researched:** 2026-08-09  
**Domain:** Serve-time detection worker factory, artifact path safety, preferred-vs-live backend honesty  
**Confidence:** HIGH (code-verified plug-in surface + existing honesty debt; no new third-party packages)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Factory plug-in at serve construction — DetectionLoop frozen
- Torch `.pt` path remains production default for desktop-gpu
- Prefer Ultralytics-native path later for ORT/TRT (Phase 9/10); Phase 8 only wires selection
- No silent `backend_live=tensorrt` when running torch
- Artifact paths: config/env/cache allowlist — no path traversal
- No prebuilt engines in wheel

### From v0.2 research
- `build_detection_worker(rt)` pattern at serve
- Status fields: `backend_requested`, `backend_live` (+ optional reason later)
- ORT/TRT branches may return NotImplemented worker or explicit torch with `backend_live=torch` + reason until phases 9–10 — honesty first

### Claude's Discretion
- Exact module layout (`models/detection/factory.py` vs `backend/factory.py`)
- Whether ORT/TRT stubs raise at construct vs run
- How Live Preview footer displays backend pair
- Env var names for artifact roots (`SENTRY_ONNX_PATH`, etc.)

### Deferred Ideas (OUT OF SCOPE)
- Live ORT/TRT inference
- Sticky thrash-free fallback modes
- Jetson JetPack matrix depth
- Dual-model VRAM budgets
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BACK-01 | Runtime profile `preferred_backend` selects the fixed-class detection **loader** (torch / onnxruntime / tensorrt), not device-policy logs alone | Factory branches on `rt.preferred_backend`; torch fully live; ORT/TRT branches wired as stubs with honest `backend_live` |
| BACK-02 | Status / serve banner expose both `backend_requested` and `backend_live` (no silent backend lies) | Extend `StatusSnapshot` + CLI banner + `/api/status`; optional Live Preview footer |
| BACK-04 | Artifact paths for `.onnx` / `.engine` resolve from config/env/cache with a safe allowlist (no arbitrary path traversal) | New pure path resolver with stem/extension allowlist + root confinement |
| EDGE-RT-01 | DetectionLoop / FrameBus / PerceptionStore / `/v1` remain the perception spine — no bus redesign | Factory returns duck-typed ModelWorker; loop only calls `process` / conf duck-type |
| EDGE-RT-02 | `sentry serve` constructs detection worker via a factory from `profile_runtime` (torch worker preserved for `.pt`) | Replace hard-coded `YoloDetectionWorker(...)` in `cli.serve` with `build_detection_worker(rt, …)` |
| EDGE-RT-03 | Desktop GPU path remains first-class with torch default; jetson/cpu-fallback profiles can select ORT/TRT honestly | Profile YAML already sets preferred backends; factory must honor desktop-gpu→torch live; jetson/cpu-fallback selection visible without false live claims |
</phase_requirements>

## Summary

Phase 8 closes the v1 residual where `preferred_backend` is device policy + honesty logs while serve always constructs `YoloDetectionWorker(.pt)`. The only structural change is a **serve-time factory** that branches on `ProfileRuntime.preferred_backend`, resolves artifact candidates safely, and returns a ModelWorker **plus** explicit `backend_requested` / `backend_live` (and a short reason when they differ). Torch remains fully end-to-end. ORT/TRT loader **branches exist** but must not claim live ORT/TRT until Phases 9–10 implement real loaders.

The perception spine is frozen: DetectionLoop, FrameBus, PerceptionStore, assemble/`/v1`, depth/OV/free-space workers. No new pip packages. No Jetson hardware required for tests. Existing inspect-source tests that assume direct `YoloDetectionWorker` construction in `serve` must be updated to assert factory wiring.

**Primary recommendation:** Add `build_detection_worker(rt) → WorkerBuild` at `models/detection/factory.py`, pure `resolve_detector_artifact(...)` at `config/artifact_paths.py`, soft ORT/TRT stubs that load torch with `backend_live=torch` + reason, and surface both backends on banner + `StatusSnapshot`/`/api/status`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Backend selection (torch/ORT/TRT branch) | API / Backend (serve construction) | — | One-shot resolve at process start; never per-frame in DetectionLoop |
| Torch `.pt` live inference | API / Backend (YoloDetectionWorker) | — | Existing Ultralytics path; desktop-gpu default |
| ORT/TRT loader stubs (Phase 8) | API / Backend (factory branch) | — | Branch wiring only; no real session/engine until 9–10 |
| Artifact path resolve + allowlist | API / Backend (config helpers) | Filesystem / cache | Pure path policy; no network; no Ultralytics import |
| `backend_requested` / `backend_live` identity | API / Backend (status model + app.state) | Browser / Client (Live Preview footer) | Single source of truth at serve; UI only displays |
| Serve banner honesty | CLI (cli.serve) | — | Operator-facing at process start |
| Detection scheduling / store write | API / Backend (DetectionLoop) | — | **Frozen** — backend-agnostic |
| FrameBus keep-latest | API / Backend | — | **Frozen** |
| Perception merge + `/v1` | API / Backend | — | **Frozen** — no Detection schema change |
| Depth / open-vocab workers | API / Backend | — | **Out of scope** — stay direct torch construction |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | ≥3.11 | Runtime | [VERIFIED: pyproject.toml] existing project pin |
| Pydantic 2 | ≥2.13,<3 | `StatusSnapshot` field extensions | [VERIFIED: pyproject.toml] already owns wire models |
| FastAPI | ≥0.141,<1 | `/api/status` merge | [VERIFIED: pyproject.toml] existing preview routes |
| Ultralytics (detect extra) | ≥8.4.33,<9 | Torch `.pt` live path only this phase | [VERIFIED: pyproject.toml + yolo_worker.py] |
| stdlib `pathlib.Path` | — | Artifact resolve + root confinement | No third-party path library needed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | ≥8 | Unit tests for factory, paths, status honesty | Existing `dev` extra |
| httpx | ≥0.28 | Optional `/api/status` field assertions via TestClient | Existing preview tests |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Soft torch stub for ORT/TRT | Hard-fail at construct | Hard-fail is closer to strict edge (Phase 11); breaks “torch still works” success criterion for jetson/cpu-fallback serve |
| `backend/factory.py` | `models/detection/factory.py` | Backend package owns `InferenceBackend` protocols; detection factory returns ModelWorkers — keep next to yolo_worker |
| Full `OrtBackend`/`TrtBackend` now | Stub branches only | Real backends are Phases 9–10; shipping empty InferenceBackend classes adds surface without live path |
| Put backend fields only in logs | StatusSnapshot + API | Logs alone fail BACK-02 for robots/UI consumers |

**Installation:** None for Phase 8.

```bash
# No new packages. Existing detect extra still required for live torch:
uv sync --extra dev --extra detect
```

**Version verification:** No new registry packages. Existing pins unchanged. [VERIFIED: pyproject.toml 2026-08-09]

## Package Legitimacy Audit

> Phase 8 installs **no** external packages. Factory, path resolver, and status fields are pure project code.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| — | — | — | — | — | n/a | No installs |

**Packages removed due to slopcheck [SLOP] verdict:** none  
**Packages flagged as suspicious [SUS]:** none  

*Do not add `onnxruntime`, `tensorrt`, or GPU wheels in this phase — those are Phase 9/10 + packaging docs.*

## Architecture Patterns

### System Architecture Diagram

```
                    Profile YAML + env + SENTRY_MODEL_CACHE
                                    │
                                    ▼
                         profile_runtime(cfg) → ProfileRuntime
                           preferred_backend, detector_weights, device
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────┐
│  build_detection_worker(rt, conf=…)          ← NEW (serve only)  │
│    ├─ resolve_detector_artifact(.onnx|.engine)  allowlist roots  │
│    ├─ branch preferred_backend:                                  │
│    │    torch|cpu → YoloDetectionWorker(.pt)  live=torch         │
│    │    onnxruntime → stub (Phase 8): torch + reason             │
│    │    tensorrt    → stub (Phase 8): torch + reason             │
│    └─ return WorkerBuild{worker, requested, live, reason}        │
└───────────────────────────────┬──────────────────────────────────┘
                                │ ModelWorker (duck-typed)
                                ▼
┌──────────────── SPINE FROZEN ────────────────────────────────────┐
│  FrameBus → DetectionLoop.process → PerceptionStore              │
│       → assemble_perception_frame → /v1 + Live Preview overlays  │
└──────────────────────────────────────────────────────────────────┘
                                │
          backend_requested / backend_live / reason
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
        CLI banner       app.state fields    /api/status JSON
                                              │
                                              ▼
                                      Live Preview footer
```

### Recommended Project Structure

```
src/sentry_ai/
├── models/detection/
│   ├── factory.py          # NEW: build_detection_worker + WorkerBuild
│   ├── yolo_worker.py      # UNCHANGED torch path (injectable model= for tests)
│   └── loop.py             # FROZEN
├── config/
│   ├── artifact_paths.py   # NEW: resolve_detector_artifact + allowlist
│   ├── profile_runtime.py  # minor: docstring honesty update; optional path fields later
│   └── models.py           # optional: detector_onnx / detector_engine fields (Phase 8 or 9)
├── capture/status.py       # ADD optional backend_* fields on StatusSnapshot
├── api/routes_preview.py   # MERGE backend_* into /api/status from app.state
├── api/app.py              # optional: app.state.backend_requested / backend_live
└── cli.py                  # serve: factory + banner; do not hard-code YOLO construct
```

### Pattern 1: Factory returns worker + honesty metadata

**What:** One construction function owns selection and truth labels.  
**When to use:** Always at `cli.serve` detection construction.  
**Example:**

```python
# Recommended shape (project-local design; not a third-party API)
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class WorkerBuild:
    worker: Any  # ModelWorker duck-type
    backend_requested: str  # torch | onnxruntime | tensorrt | cpu
    backend_live: str       # what is actually running
    backend_reason: str | None = None  # when requested != live


def build_detection_worker(
    rt: "ProfileRuntime",
    *,
    conf: float = 0.25,
    model: Any | None = None,  # test injection for torch path
) -> WorkerBuild:
    requested = _normalize_backend(rt.preferred_backend)
    if requested in {"torch", "cpu"}:
        worker = YoloDetectionWorker(
            weights=rt.detector_weights,
            conf=conf,
            device=rt.device,
            model=model,
        )
        live = "torch" if requested != "cpu" else "torch"  # live loader is torch; device may be cpu
        return WorkerBuild(worker=worker, backend_requested=requested, backend_live="torch")

    # Phase 8: ORT/TRT selection is real wiring, not live inference
    if requested == "onnxruntime":
        worker = YoloDetectionWorker(
            weights=rt.detector_weights, conf=conf, device=rt.device, model=model
        )
        return WorkerBuild(
            worker=worker,
            backend_requested="onnxruntime",
            backend_live="torch",
            backend_reason="ort_loader_not_implemented",  # Phase 9
        )
    if requested == "tensorrt":
        worker = YoloDetectionWorker(
            weights=rt.detector_weights, conf=conf, device=rt.device, model=model
        )
        return WorkerBuild(
            worker=worker,
            backend_requested="tensorrt",
            backend_live="torch",
            backend_reason="trt_loader_not_implemented",  # Phase 10
        )
    # openvino / unknown → torch + reason
    ...
```

[ASSUMED] exact reason string vocabulary — pick stable snake_case codes (`ort_loader_not_implemented`, `engine_missing`, `path_rejected`) for Phase 11 sticky policy reuse.

### Pattern 2: Artifact path resolver with root allowlist

**What:** Resolve candidate `.onnx` / `.engine` paths without arbitrary filesystem reads.  
**When to use:** Factory pre-check for ORT/TRT branches (Phase 8 records path existence for future use; Phase 9/10 load).  
**Example:**

```python
# Source pattern: scripts/export/export_yolo.py validate_weights (basename allowlist)
# Extended for absolute paths under allowlisted roots only.

from pathlib import Path

ALLOWED_STEMS = frozenset({"yolo26n", "yolo26s", "yolo26m"})
ALLOWED_SUFFIXES = frozenset({".onnx", ".engine"})


def resolve_detector_artifact(
    *,
    preferred_backend: str,
    detector_weights: str,  # e.g. yolo26n.pt
    explicit: str | Path | None = None,
    env_value: str | None = None,
    weights_dir: Path | None = None,
    cwd: Path | None = None,
) -> Path | None:
    """Return existing allowlisted path or None. Never invent; never traverse out."""
    ...
```

**Resolution order** [CITED: .planning/research/ARCHITECTURE.md]:

1. Explicit config / env (`SENTRY_DETECTOR_ONNX` | `SENTRY_DETECTOR_ENGINE`)  
2. `{weights_dir}/{stem}.onnx|.engine` from `configure_model_cache()`  
3. `{cwd}/{stem}.onnx|.engine` (basename only under CWD)  
4. Miss → `None` (factory sets reason; does not invent path)

**Safety rules:**

- Stem must map from known detector weights / `ALLOWED_STEMS`  
- Suffix must be `.onnx` or `.engine` matching preferred backend  
- Any explicit/env path: `Path.resolve()` then require `path.is_relative_to(root)` for each allowlisted root (`weights_dir`, optional `SENTRY_ARTIFACT_ROOT`, CWD)  
- Reject `..` components, symlink escape after resolve, wrong extension, unknown stems  
- Never ship or auto-download engines  

### Pattern 3: Preferred vs live on status surface

**What:** Two fields always present when detection is enabled; equal when torch requested and live.  
**When to use:** CLI banner, `/api/status`, optional UI footer.  
**Example:**

```python
# StatusSnapshot additions (optional fields — keep Phase 2 callers valid)
backend_requested: str | None = None
backend_live: str | None = None
backend_reason: str | None = None  # optional but recommended in Phase 8
```

Wire path:

1. `cli.serve` stores `WorkerBuild` fields on `app.state` (e.g. `backend_requested`, `backend_live`, `backend_reason`)  
2. `routes_preview.api_status` merges them into the dumped status dict (same pattern as pipeline_state / ov_mode)  
3. Optionally set on `StatusSnapshot` inside a thin helper so model_dump includes them without CaptureLoop knowing about backends  

**CLI banner (replace v1 “export target only” notes):**

```text
preferred_backend: tensorrt
backend_live: torch
backend_reason: trt_loader_not_implemented
```

Never print only `preferred_backend=tensorrt` without live identity.

### Pattern 4: Spine-agnostic ModelWorker

**What:** DetectionLoop only needs `process`, optional `get_conf`/`set_conf`, `name`.  
**When to use:** Any factory return value.  
**Verified:** [VERIFIED: src/sentry_ai/models/detection/loop.py] — no Ultralytics import, no `preferred_backend` read.

### Anti-Patterns to Avoid

- **`if backend == tensorrt` inside DetectionLoop:** Couples scheduling to vendor; untestable. Factory at serve only.  
- **`backend_live=tensorrt` while loading `.pt`:** Silent lie (PITFALLS #5).  
- **Passing `device="tensorrt"` to Ultralytics:** Invalid torch device — `device_for_backend` already avoids this; keep invariant.  
- **Implementing real ORT/TRT sessions in Phase 8:** Scope creep into Phases 9–10.  
- **Per-frame artifact re-resolve:** Fallback thrash (Phase 11 owns sticky policy).  
- **Rewriting InferenceBackend hierarchy now:** Protocol exists for later; not required for factory + honesty.  
- **Hard-importing `tensorrt` or `onnxruntime` in factory:** Breaks CI without GPU/extras.  
- **Changing depth/OV construction:** EDGE-RT-04 is Phase 11; leave direct torch workers.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Path traversal defense | Custom string replace heuristics only | `Path.resolve()` + `is_relative_to(allowlisted_root)` + stem/suffix allowlist | Symlinks and mixed separators defeat naive `..` checks alone |
| Basename allowlist for known YOLO weights | New ad-hoc set | Extend pattern from `KNOWN_WEIGHTS` / export `validate_weights` | Consistency with export CLI [VERIFIED: scripts/export/export_yolo.py] |
| ModelWorker contract | New abstract base class hierarchy | Existing duck-typing + optional Protocol | DetectionLoop already duck-typed |
| Status JSON schema evolution | Breaking required fields | Optional fields with defaults (existing StatusSnapshot pattern) | Phase 2–7 callers stay valid |
| Live ORT postprocess | Custom YOLO26 head decoder | Defer to Ultralytics-native path in Phase 9 | Postprocess drift risk (STACK.md) |

**Key insight:** Phase 8 is a **contract and wiring** phase. Complexity is in honesty and path safety, not inference math.

## Common Pitfalls

### Pitfall 1: Silent backend lies
**What goes wrong:** Status/UI still show `tensorrt`/`onnxruntime` as if live while torch runs.  
**Why it happens:** Copying v1 banner language or setting live=requested by default.  
**How to avoid:** Factory is sole author of `backend_live`; tests assert jetson profile → `live=torch` in Phase 8.  
**Warning signs:** `backend_live == backend_requested` for ORT/TRT without artifact load code.

### Pitfall 2: Path traversal / arbitrary file load
**What goes wrong:** Env `SENTRY_DETECTOR_ENGINE=../../etc/passwd` or absolute path outside cache accepted.  
**Why it happens:** `Path(env)` without root check; trusting suffixes only.  
**How to avoid:** Resolve + confine to allowlisted roots; reject non-`.onnx`/`.engine`; stem allowlist.  
**Warning signs:** Tests only cover happy paths under CWD.

### Pitfall 3: Breaking inspect-source CLI tests
**What goes wrong:** `test_serve_applies_profile_runtime` expects `rt.detector_weights` and `device=rt.device` inline in serve.  
**Why it happens:** Factory absorbs those kwargs.  
**How to avoid:** Update CLI tests to assert `build_detection_worker` + `backend_live` banner strings; keep weight assertions in factory unit tests.  
**Warning signs:** Green factory tests, red `test_cli_serve`.

### Pitfall 4: Raising ORT/TRT stubs kills serve on jetson/cpu-fallback
**What goes wrong:** Construct-time `NotImplementedError` prevents default profile demos.  
**Why it happens:** Strict interpretation of “stub.”  
**How to avoid:** Prefer soft torch stub + reason (CONTEXT allows either; success criteria require torch serve still works).  
**Warning signs:** `sentry serve --profile jetson` exits non-zero without user opt-in strict mode.

### Pitfall 5: Touching the frozen spine
**What goes wrong:** Backend switch inside DetectionLoop or PerceptionStore schema changes.  
**Why it happens:** “Just one if” for logging.  
**How to avoid:** Checklist: no edits to loop.py bus semantics, store writers, `/v1` Detection model.  
**Warning signs:** Diffs in `loop.py` beyond comments.

### Pitfall 6: Importing GPU-only modules in unit tests
**What goes wrong:** CI fails on `import tensorrt` / GPU ORT.  
**Why it happens:** Eager imports in factory module top-level.  
**How to avoid:** Lazy imports only inside future Phase 9/10 load paths; Phase 8 factory imports only torch worker.  
**Warning signs:** Factory module import fails without detect extra (should still import path helpers).

## Code Examples

### Current serve construction (to replace)

```python
# Source: src/sentry_ai/cli.py (serve) — VERIFIED 2026-08-09
worker = YoloDetectionWorker(
    weights=rt.detector_weights,
    conf=0.25,
    device=rt.device,
)
det_loop = DetectionLoop(bus, worker, store)
```

### Target serve construction

```python
from sentry_ai.models.detection.factory import build_detection_worker

build = build_detection_worker(rt, conf=0.25)
worker = build.worker
det_loop = DetectionLoop(bus, worker, store)  # UNCHANGED
# stash build.backend_requested / backend_live / backend_reason on app.state
```

### Export-style basename validation (reuse pattern)

```python
# Source: scripts/export/export_yolo.py validate_weights — VERIFIED
name = str(weights).strip()
if name != Path(name).name:
    raise ValueError("use basename only")
if ".." in name or "/" in name or "\\" in name:
    raise ValueError("path traversal rejected")
if name not in KNOWN_WEIGHTS:
    raise ValueError("must be in KNOWN_WEIGHTS allowlist")
```

### Status merge pattern (existing style)

```python
# Source: src/sentry_ai/api/routes_preview.py api_status — VERIFIED pattern
# After snapshot.model_dump(), merge optional app.state fields:
data["backend_requested"] = getattr(request.app.state, "backend_requested", None)
data["backend_live"] = getattr(request.app.state, "backend_live", None)
data["backend_reason"] = getattr(request.app.state, "backend_reason", None)
```

### device_for_backend honesty invariant (keep)

```python
# Source: src/sentry_ai/config/profile_runtime.py — VERIFIED
# tensorrt → cuda:0 (never device string "tensorrt")
# onnxruntime → "cpu"
```

## State of the Art

| Old Approach (v1.0) | Current Approach (v0.2 Phase 8) | When Changed | Impact |
|---------------------|----------------------------------|--------------|--------|
| `preferred_backend` device policy + honesty logs only | Factory selects loader branch + live identity fields | Phase 8 | Operators can trust status |
| Hard-coded `YoloDetectionWorker` in serve | `build_detection_worker(rt)` | Phase 8 | Plug-in point for 9–10 |
| Banner: “ORT is the export target” | Banner: requested vs live (+ reason) | Phase 8 | Replaces residual honesty debt |
| No artifact path API | Allowlisted `.onnx`/`.engine` resolver | Phase 8 | Safe prep for live loaders |
| Live ORT/TRT | Still deferred | Phases 9–10 | Stubs only |

**Deprecated/outdated:**

- Banner text claiming backends are “export targets only” without emitting `backend_live`  
- Treating profile `preferred_backend` as sufficient telemetry without live field  

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Soft torch stub (not hard-fail) is correct default for ORT/TRT branches in Phase 8 | Pattern 1 / Pitfall 4 | Strict edge operators may want fail-closed earlier — Phase 11 owns modes |
| A2 | Env names `SENTRY_DETECTOR_ONNX` / `SENTRY_DETECTOR_ENGINE` preferred over `SENTRY_ONNX_PATH` | Discretion | Docs/env mismatch if user prefers shorter names |
| A3 | Optional `backend_reason` included in Phase 8 (not deferred) | BACK-02 | Slightly more API surface; improves Phase 11 reuse |
| A4 | Config model fields `detector_onnx` / `detector_engine` can wait until Phase 9 if env+cache suffice | Artifact paths | Makers cannot set paths in YAML until added |
| A5 | Live Preview footer is a small static HTML change in Phase 8 (roadmap UI hint: yes) | BACK-02 | Can defer to status-only if UI churn is undesired |

## Open Questions

1. **Soft stub vs construct-time error for ORT/TRT**  
   - What we know: CONTEXT allows either; success criteria require torch serve still works.  
   - What's unclear: Whether jetson profile should warn louder (stderr) on every serve.  
   - Recommendation: Soft stub + one stderr note with reason code; no exit non-zero.

2. **Should `StatusSnapshot` own backend fields or only app.state merge?**  
   - What we know: CaptureLoop.build_status does not know backends today.  
   - What's unclear: Whether to expand StatusSnapshot vs free-form dict merge only.  
   - Recommendation: Add optional fields to StatusSnapshot for schema honesty; fill from routes or a small status helper — avoid teaching CaptureLoop about backends.

3. **YAML artifact path fields in Phase 8?**  
   - What we know: ARCHITECTURE suggests `models.detector_engine` / `detector_onnx`.  
   - What's unclear: Minimal Phase 8 vs prep for 9.  
   - Recommendation: Env + cache + CWD resolver in 08-01 is enough for BACK-04; add optional Pydantic fields if cheap (extra=forbid requires explicit model fields).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Runtime | ✓ (host 3.14.6 also present) | 3.14.6 host / project ≥3.11 | — |
| uv | Dev install | ✓ | 0.11.23 | pip |
| pytest | Unit tests | ✓ | 8.4.2 | — |
| detect extra (ultralytics) | Torch live path | project-optional | ≥8.4.33 | Tests inject `model=` |
| onnxruntime | Phase 9 live ORT | not required Phase 8 | — | Stub branch |
| system tensorrt | Phase 10 live TRT | not required Phase 8 | — | Stub branch |
| NVIDIA Jetson | Hardware TRT | not required | — | Mock/unit tests only |

**Missing dependencies with no fallback:** none for Phase 8  

**Missing dependencies with fallback:** ORT/TRT runtimes → intentional stubs  

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest ≥8 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_detection_factory.py tests/test_artifact_paths.py tests/test_backend_honesty_status.py -q` |
| Full suite command | `pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BACK-01 | Factory maps preferred_backend → branch; torch live | unit | `pytest tests/test_detection_factory.py -q` | ❌ Wave 0 |
| BACK-01 | ORT/TRT preferred does not set live=ort/trt | unit | `pytest tests/test_detection_factory.py -q` | ❌ Wave 0 |
| BACK-02 | StatusSnapshot /api fields expose requested+live | unit | `pytest tests/test_backend_honesty_status.py -q` | ❌ Wave 0 |
| BACK-02 | CLI banner source includes backend_live | unit (inspect) | `pytest tests/test_cli_serve.py -q` | ⚠️ update existing |
| BACK-04 | Path resolver rejects `..` and out-of-root paths | unit | `pytest tests/test_artifact_paths.py -q` | ❌ Wave 0 |
| BACK-04 | Allowlisted stem+suffix under cache resolves | unit | `pytest tests/test_artifact_paths.py -q` | ❌ Wave 0 |
| EDGE-RT-01 | DetectionLoop unchanged contract (process→store) | unit / no-diff | `pytest tests/test_detection_loop.py -q` | ✅ |
| EDGE-RT-02 | serve uses build_detection_worker | unit (inspect) | `pytest tests/test_cli_serve.py -q` | ⚠️ update existing |
| EDGE-RT-03 | desktop-gpu → requested=torch live=torch; jetson requested=tensorrt live=torch (Phase 8) | unit | `pytest tests/test_detection_factory.py tests/test_profile_application.py -q` | ⚠️ + new |

### Sampling Rate

- **Per task commit:** targeted new tests above  
- **Per wave merge:** `pytest -q`  
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_detection_factory.py` — covers BACK-01, EDGE-RT-02/03 factory matrix (mock `model=`, no weights download)
- [ ] `tests/test_artifact_paths.py` — covers BACK-04 traversal + allowlist
- [ ] `tests/test_backend_honesty_status.py` — covers BACK-02 StatusSnapshot /api merge
- [ ] Update `tests/test_cli_serve.py` — assert factory + backend_live banner (replace brittle inline weight wiring asserts as needed)
- [ ] Optional: Live Preview static test if footer added (`tests/test_api_preview.py` or desktop docs pattern)

*(No new framework install required.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Localhost-default serve unchanged |
| V3 Session Management | no | — |
| V4 Access Control | no (local process) | Non-localhost bind warning remains |
| V5 Input Validation | **yes** | Artifact path allowlist + resolve confinement; no arbitrary model paths |
| V6 Cryptography | no | — |

### Known Threat Patterns for this phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via env/config artifact path | Tampering | Resolve + `is_relative_to` allowlisted roots; stem/suffix allowlist |
| Loading untrusted model graph from arbitrary path | Elevation / Tampering | Known stems only (`yolo26n/s/m`); no remote URL fetch in resolver |
| Status spoofing (claim TRT when torch) | Spoofing | Factory sole writer of `backend_live`; tests for mismatch honesty |
| Dependency confusion via new extras | Tampering | **No new packages** this phase |

## What NOT to Change (spine freeze checklist)

| Component | Action |
|-----------|--------|
| `models/detection/loop.py` | **Do not edit** (except docstring if unavoidable) |
| `bus/frame_bus.py` | **Do not edit** |
| `state/perception_store.py` | **Do not edit** |
| `api/assemble.py`, `api/routes_v1.py` | **Do not edit** Detection schema |
| `models/depth/*`, `yoloe_worker.py`, free-space | **Do not edit** for backends |
| `backend/protocols.py` InferenceBackend | Optional comment only; no required Ort/Trt classes |
| `pyproject.toml` extras | **No** `onnx`/`tensorrt` extras in Phase 8 |
| Profile YAML preferred_backend values | Keep desktop-gpu=torch, jetson=tensorrt, cpu-fallback=onnxruntime; update comments only |

## Discretion Recommendations (for planner)

| Discretion item | Recommendation | Confidence |
|-----------------|----------------|------------|
| Module layout | `models/detection/factory.py` + `config/artifact_paths.py` | HIGH |
| ORT/TRT stub style | Soft: return torch worker + `backend_live=torch` + reason; do not raise | HIGH |
| Live Preview footer | Add one line: `Backend: {requested} → {live}` when fields present; muted color if equal | MEDIUM |
| Env var names | `SENTRY_DETECTOR_ONNX`, `SENTRY_DETECTOR_ENGINE` (+ optional `SENTRY_ARTIFACT_ROOT`) | HIGH |
| `backend_reason` | Include in Phase 8 (stable codes) | HIGH |

## Suggested plan split (from CONTEXT)

### 08-01 — Factory + artifact resolution + profile wiring
- `artifact_paths.py` + unit tests (traversal)
- `factory.py` + matrix tests (desktop-gpu/jetson/cpu-fallback)
- Wire `cli.serve` to factory; keep DetectionLoop construction identical
- Do not claim live ORT/TRT

### 08-02 — Status/banner honesty
- StatusSnapshot optional fields
- app.state + routes_preview merge
- CLI banner requested/live/reason
- Optional Live Preview footer
- Update CLI/API tests

## Sources

### Primary (HIGH confidence)

- [VERIFIED: codebase] `src/sentry_ai/cli.py` serve construction + honesty notes  
- [VERIFIED: codebase] `src/sentry_ai/config/profile_runtime.py` ProfileRuntime + device_for_backend  
- [VERIFIED: codebase] `src/sentry_ai/models/detection/{loop,yolo_worker}.py`  
- [VERIFIED: codebase] `src/sentry_ai/capture/status.py` StatusSnapshot  
- [VERIFIED: codebase] `src/sentry_ai/api/routes_preview.py` `/api/status` merge pattern  
- [VERIFIED: codebase] `scripts/export/export_yolo.py` path allowlist pattern  
- [VERIFIED: codebase] profile YAML under `src/sentry_ai/config/profiles/`  
- [CITED: .planning/research/ARCHITECTURE.md] factory plug-in, path order, frozen spine  
- [CITED: .planning/research/SUMMARY.md] Phase 8 deliverables  
- [CITED: .planning/research/PITFALLS.md] silent backend lies, CI without GPU, path/engine rules  
- [CITED: .planning/research/STACK.md] Ultralytics-native later; no tensorrt pip extra  
- [CITED: .planning/REQUIREMENTS.md] BACK-01/02/04, EDGE-RT-01..03  
- [CITED: .planning/ROADMAP.md] Phase 8 success criteria + plans 08-01/08-02  
- [CITED: .planning/phases/08-backend-selection-honesty/08-CONTEXT.md] locked decisions  

### Secondary (MEDIUM confidence)

- Live Preview footer UX details (discretion; no existing backend metrics in HTML)  
- Exact reason-code vocabulary for Phase 11 sticky policy alignment  

### Tertiary (LOW confidence)

- None material for Phase 8 execution  

## Project Constraints (from CLAUDE.md)

No project-root `CLAUDE.md` / `AGENTS.md` found in workspace. Parent user `~/.claude/Claude.md` only references graphify skill — not applicable to this phase’s code changes.

Repo conventions observed from existing code (treat as de facto constraints):

- Optional extras (`detect`/`depth`); graceful ImportError degrade in serve  
- Pydantic models `extra="forbid"`  
- Status fields added as optional with defaults  
- Pure helpers avoid hard torch imports at module level where possible  
- CI-safe tests: injectable fakes, no Jetson, no weight download in default pytest  

## Metadata

**Confidence breakdown:**

- Standard stack: **HIGH** — no new packages; existing pins verified  
- Architecture: **HIGH** — plug-in point and frozen spine code-verified  
- Pitfalls: **HIGH** — mapped to v0.2 research + current honesty debt in cli/profile_runtime  
- Stub policy (soft vs hard): **MEDIUM** — product discretion; recommendation given  

**Research date:** 2026-08-09  
**Valid until:** 2026-09-08 (30 days; stable domain — internal wiring)

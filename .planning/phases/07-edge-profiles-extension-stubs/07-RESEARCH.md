# Phase 7: Edge Profiles & Extension Stubs - Research

**Researched:** 2026-08-08  
**Domain:** Multi-target runtime profiles, edge export recipes (ONNX/TensorRT), headless serve, extension scaffolds  
**Confidence:** HIGH (codebase contracts verified; Ultralytics export API verified in installed 8.4.116; Jetson/TRT constraints cross-checked with prior STACK research + official Ultralytics export surface)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Three built-in profiles already exist as YAML: `desktop-gpu`, `jetson`, `cpu-fallback` (FOUND-06)
- Profiles must drive **detector_tier / depth_tier / preferred_backend** at serve time (not advisory-only docs)
- Export path is **recipes + scripts** (PyTorch → ONNX → TensorRT FP16 notes); do not require Jetson hardware in CI
- Headless = serve perception API without mounting/serving static UI (or `--no-ui` / equivalent)
- Stubs only for ROS2 / multi-cam / voice — scaffolds that compile/import and document extension points
- Perception-only, non-autonomy, privacy (localhost default) language finalized
- Local OSS only; `allow_cloud: false` default remains

### Claude's Discretion
- Whether headless is `--no-ui` flag, separate `sentry api` command, or env `SENTRY_HEADLESS`
- How far to go on real device probe (torch.cuda / platform hints) vs keep advisory + docs
- Export scripts location (`scripts/export/` vs `docs/export/`) and whether they invoke ultralytics export API
- ROS2 stub shape: package layout + README only vs importable Python bridge module with NotImplemented
- Profile defaults: keep serve default `cpu-fallback` or switch desktop-gpu when CUDA detected
- Whether open-vocab is disabled by default on jetson/cpu profiles
- Exact JetPack / TensorRT version matrix wording (honest “as of” notes)

### Deferred Ideas (OUT OF SCOPE)
- Full ROS2 Humble/Jazzy production package and launch files
- Multi-cam fusion and extrinsic calibration UI
- Voice ASR/TTS product
- Prebuilt TRT engines in releases
- OpenVINO first-class path beyond BackendName enum
- Authenticated remote API
- Metric-calibrated free-space meters (needs calibration phase)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EDGE-01 | Documented desktop GPU development path runs the full pipeline | README + `docs/desktop-gpu.md` E2E: extras, profile, USB, full stages; no new runtime code required beyond profile wiring |
| EDGE-02 | Runtime profiles for desktop, Jetson-class, CPU/lite fallback | Make YAML fields **executable at serve**: detector_tier (done), depth_tier map, preferred_backend→device policy, open-vocab tier; optional light `probe_device` |
| EDGE-03 | ONNX and/or TensorRT export recipes for edge deployment | `docs/export/` + `scripts/export/` using Ultralytics `model.export`; on-device TRT build notes; no CI Jetson; no prebuilt engines |
| EDGE-04 | Extension stubs: multi-cam `camera_id`, ROS2 scaffold, voice no-op | Schema multi-id tests; importable ROS2 bridge stub; `VoiceNullSink` entry point |
| EDGE-05 | Headless mode runs perception API without requiring the web UI | `create_app(serve_ui=…)` + `sentry serve --no-ui`; keep `/v1/*` `/api/*` |
</phase_requirements>

## Summary

Phase 7 closes the multi-target claim that Phase 1 only stubbed. The product already has three profile YAMLs, `load_config(profile=…)`, `RuntimeProfile` / `BackendName` enums, and **one live profile effect**: `cfg.models.detector_tier` → `tier_to_weight` → YOLO26 weights in `sentry serve`. Everything else is still advisory: `depth_tier` is unused (always DAV2 Small), `preferred_backend` never selects a real ORT/TRT runtime, `probe_device` always returns `available=False`, open-vocab always loads `yoloe-26s-seg.pt`, and the Live Preview HTML is always served at `GET /`.

This phase should **not** build a full TensorRT inference backend or a production ROS2 node. It should (1) make profiles drive model tiers + device policy at serve time, (2) ship honest export recipes/scripts for YOLO26/YOLOE (+ depth export feasibility notes), (3) add headless serve for robot-only consumers, (4) leave importable extension stubs, and (5) finalize desktop-GPU + safety/privacy docs.

**Primary recommendation:** Split into the roadmap’s three plans — **07-01** profile application + headless, **07-02** export recipes/scripts + Jetson packaging notes, **07-03** extension stubs + release docs. Keep v1 inference on Ultralytics/HF **PyTorch** paths; treat ONNX/TRT as **export + on-device build documentation**, not a mandatory new runtime backend in this phase.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Profile YAML load / merge | API / Backend (config) | — | `load_config` already owns profile→`SentryConfig` |
| Detector tier → weights | API / Backend (serve + cache) | — | Already wired via `tier_to_weight` |
| Depth tier → model id | API / Backend (depth worker) | — | Config exists; worker currently hardcodes Small allowlist |
| Preferred backend → device policy | API / Backend (workers) | Docs | v1 maps backend/device_id → torch device string; TRT/ORT runtime deferred |
| Device probe | API / Backend | CLI health | Advisory; never hard-fail serve if CUDA missing |
| Headless UI gate | Frontend Server (FastAPI static route) | CLI flag | Skip `GET /` HTML; keep perception APIs |
| Perception stream for robots | API / Backend (`/v1`) | — | Unchanged; headless primary consumer |
| Export ONNX/TRT | CDN / Static (scripts/docs offline) | Developer machine / Jetson | Offline recipes; not hot path |
| ROS2 / voice / multi-cam hooks | API / Backend (plugins) | External processes | Stubs only; no product features |
| Safety/privacy copy | Docs | UI footer (existing) | Finalize non-autonomy + localhost risk |

## Current State (what already exists)

### Profiles & config [VERIFIED: codebase]

| Profile | `preferred_backend` | `device_id` | `detector_tier` | `depth_tier` | Used by serve today |
|---------|---------------------|------------|-----------------|--------------|---------------------|
| `desktop-gpu` | `torch` | `cuda:0` | `s` | `small` | **detector_tier only** |
| `jetson` | `tensorrt` | `0` | `n` | `small` | **detector_tier only** |
| `cpu-fallback` | `onnxruntime` | `cpu` | `n` | `small` | **detector_tier only** |

- YAML under `src/sentry_ai/config/profiles/*.yaml` [VERIFIED: codebase]
- `ModelsConfig` has `detector_tier`, `depth_tier`; no open-vocab tier field [VERIFIED: `config/models.py`]
- Default profile when unset: `cpu-fallback` (`_DEFAULT_PROFILE`) [VERIFIED: `config/load.py`]
- Serve CLI default: `--profile cpu-fallback` [VERIFIED: `cli.py`]
- `probe_device` always `available=False` without touching CUDA [VERIFIED: `backend/protocols.py`]

### Inference path [VERIFIED: codebase]

- Fixed YOLO: `YoloDetectionWorker` + `resolve_device()` → `cuda` > `mps` > `cpu` (ignores profile `device_id` / `preferred_backend`)
- Depth: `DepthAnythingWorker` always Small HF ids via `MODE_TO_MODEL` (`depth_tier` unused)
- Open-vocab: `YoloeOpenVocabWorker(weights="yoloe-26s-seg.pt")` hard-coded in serve (ignores profile)
- No ONNX Runtime / TensorRT `InferenceBackend` implementations beyond `NullBackend`
- `BackendName` enum includes `torch | onnxruntime | tensorrt | openvino | cpu` [VERIFIED: `schemas/enums.py`]

### UI / headless gap [VERIFIED: codebase]

- `create_app` always includes `preview_router` with `GET /` → packaged `ui/static/index.html`
- No `--no-ui`, no `SENTRY_HEADLESS`, no separate `sentry api`
- Non-localhost bind already warns about unauthenticated camera exposure [VERIFIED: `cli.py`]

### Extension surface [VERIFIED: codebase]

- Plugin groups: `sentry_ai.sources|workers|sinks` entry points
- Builtins: `SyntheticSource`, `NoopWorker`, `NullSink`
- `camera_id` required on `Frame`, `PerceptionFrame`, store products, sources
- No ROS2 package, no voice sink, no multi-cam fusion
- Schema tests cover single `camera_id` identity only — not multi-id coexistence contracts

### Docs / packaging [VERIFIED: codebase]

- README covers serve, extras, open-vocab, depth, perception-only boundary
- `THIRD_PARTY_MODELS.md` documents AGPL YOLO/YOLOE + Apache DAV2 Small
- `docs/camera-sources.md` only extra doc
- No `docs/export/`, no `scripts/export/`
- Extras: `dev`, `detect`, `depth` only — no `onnx` / `tensorrt` extras

## Standard Stack

### Core (already in project — no new runtime deps required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | ≥3.11 | Runtime | Package baseline [VERIFIED: pyproject.toml] |
| FastAPI + Uvicorn | existing pins | Serve API + optional UI | Existing spine [VERIFIED: pyproject.toml] |
| Pydantic 2 | existing | Config / schemas | Existing [VERIFIED: codebase] |
| Ultralytics (detect extra) | **8.4.116** (`ultralytics-opencv-headless`) | YOLO26 + YOLOE + **export** | `YOLO.export` / `YOLOE.export` present; formats include `onnx`, `engine` [VERIFIED: .venv ultralytics 8.4.116] |
| torch + transformers (depth extra) | existing | DAV2 Small live path | Keep as edge runtime default for depth [VERIFIED: pyproject.toml] |
| pytest | ≥8 | Unit tests | Existing [VERIFIED: pyproject.toml] |

### Supporting (export / edge — docs & optional tools, not core install)

| Tool / package | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| Ultralytics export API | 8.4.x | `model.export(format="onnx"\|"engine", …)` | Desktop export scripts + Jetson on-device engine build [VERIFIED: installed package] |
| ONNX | **1.22.0** (PyPI) | Intermediate graph for portable deploy | Optional export helper only [VERIFIED: pypi.org/pypi/onnx/json] |
| onnxruntime | **1.28.0** (PyPI CPU) | CPU/lite inference experiments | **Docs-only for v1**; Jetson needs JetPack-matched wheels, not generic GPU PyPI [CITED: .planning/research/STACK.md] |
| System TensorRT (JetPack) | JetPack-bundled | Build/run `.engine` on NVIDIA edge | On-device only; never pip-pin TRT engines into wheel [CITED: STACK.md + Ultralytics Jetson guide lineage] |
| Community DAV2 ONNX/TRT | third-party | Depth export feasibility notes | Document links; do not vendor [CITED: Depth-Anything-V2 README deploy section] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `--no-ui` on `serve` | Separate `sentry api` command | Extra CLI surface; duplicate lifecycle — avoid for v1 |
| Light `probe_device` (cuda check) | Keep always-unavailable stub | Stub is honest but blocks health UX; light probe is better if non-hard-fail |
| Real ORT/TRT `InferenceBackend` | Export recipes only | Full backends are multi-week; CONTEXT locks recipes, not full TRT runtime |
| `export` pip extra with onnx | Docs + scripts using detect extra | Detect already pulls ultralytics export path; extra surface optional |
| Ship prebuilt `.engine` | On-device build docs | Engines not portable across GPU/TRT/JetPack SKUs |
| Full ROS2 package | Importable NotImplemented bridge + README | Production ROS2 is deferred |

**Installation (no new required packages for Phase 7 core):**

```bash
# Existing full pipeline (desktop primary path)
uv sync --extra dev --extra detect --extra depth

# Export recipes use detect extra (Ultralytics export) — optional:
#   uv run python scripts/export/export_yolo.py --weights yolo26n.pt --format onnx
# Do NOT add tensorrt as a project extra (system/JetPack concern).
```

**Version verification:**

| Package | Verified version | Source |
|---------|------------------|--------|
| `ultralytics-opencv-headless` | **8.4.116** | `.venv` + uv.lock [VERIFIED: codebase] |
| Ultralytics export formats | includes `onnx`, `engine` | `ultralytics.engine.exporter.export_formats()` [VERIFIED: .venv] |
| `onnx` (optional export) | **1.22.0** | PyPI JSON [VERIFIED: pypi.org] |
| `onnxruntime` (optional CPU) | **1.28.0** | PyPI JSON [VERIFIED: pypi.org] |

## Package Legitimacy Audit

> Phase 7 **should not install new required third-party packages** for the product wheel. Export tooling reuses the existing `detect` extra. Optional export packages (if planner adds an `export` extra) are listed below for legitimacy.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `ultralytics-opencv-headless` | PyPI | mature | high | github.com/ultralytics/ultralytics | unavailable | **Already approved** (detect extra) |
| `onnx` | PyPI | mature (yrs) | high | github.com/onnx/onnx | unavailable | **Optional only** — do not add unless scripts need it beyond Ultralytics [ASSUMED legitimacy gate] |
| `onnxruntime` | PyPI | mature | high | github.com/microsoft/onnxruntime | unavailable | **Docs/optional only** — not v1 runtime path [ASSUMED] |
| `tensorrt` (pip) | PyPI / NVIDIA | SKU-specific | varies | NVIDIA | — | **REMOVED from recommendations** — use system JetPack TRT; never pin as app extra |

**Packages removed due to slopcheck [SLOP] verdict:** none (slopcheck unavailable)  
**Packages flagged as suspicious [SUS]:** none  

*slopcheck was unavailable at research time. **No new required packages recommended.** If planner later adds `onnx`/`onnxruntime` extras, gate install with `checkpoint:human-verify`.*

## Recommended Approach by Requirement

### EDGE-01 — Desktop GPU E2E documentation

**What “done” looks like:** A maker with an NVIDIA (or Apple MPS) GPU can follow one doc path and run full pipeline: capture + fixed detect + depth + free-space + optional open-vocab + Live Preview + `/v1`.

**Prescribe:**

1. Add **`docs/desktop-gpu.md`** (or README section with deep link) covering:
   - Python 3.11+, `uv sync --extra dev --extra detect --extra depth`
   - `uv run sentry serve --profile desktop-gpu --source usb --device 0`
   - First-run model cache (`SENTRY_MODEL_CACHE` / `~/.cache/sentry-ai`)
   - Expected stages + UI URL `http://127.0.0.1:8000/`
   - AGPL caution for Ultralytics (`THIRD_PARTY_MODELS.md`)
   - Optional open-vocab Run path
   - Robot client: `/v1/snapshot` + `/v1/stream`
2. Mark desktop GPU as **primary maker path**; CPU profile as CI/dev-without-GPU; Jetson as deploy target with export recipes.
3. Do **not** require measured FPS numbers you cannot reproduce in CI — use “depends on GPU/thermal” language.

**Confidence:** HIGH — docs-only over existing working stack.

### EDGE-02 — Runtime profiles that actually select tiers/backends

#### Gap analysis [VERIFIED: codebase]

| Config field | Exists | Applied at serve | Phase 7 action |
|--------------|--------|------------------|----------------|
| `models.detector_tier` | yes | yes → YOLO26 n/s/m | Keep; add tests that profile→weight mapping is asserted |
| `models.depth_tier` | yes | **no** | Wire through `tier_to_depth_model` (v1: only `small` allowed; reject Base/Large NC) |
| `device.preferred_backend` | yes | **no** | Apply as **device policy** (see below); log backend; do not implement TRT EP |
| `device.device_id` | yes | **no** | Pass into workers as device override when backend is torch/cpu |
| open-vocab weights | hard-coded s | **no** | Map tier → `yoloe-26{n,s}-seg.pt` |
| open-vocab default mode | code `off` | yes | Keep **off** on all profiles; document edge must stay off/on-demand |

#### What profiles must drive in v1 (prescriptive)

1. **Detector weights** — already: `n→yolo26n.pt`, `s→yolo26s.pt`, `m→yolo26m.pt`
2. **Open-vocab weights** — new helper `tier_to_open_vocab_weight`:
   - `n` → `yoloe-26n-seg.pt`
   - `s`/`m`/default → `yoloe-26s-seg.pt`
   - Prefer deriving from `detector_tier` **or** add optional `models.open_vocab_tier` (default = detector_tier)
3. **Depth model** — `depth_tier: small` only for all built-in profiles (already). Implement mapping function that:
   - accepts `small` → current `MODE_TO_MODEL` relative/metric Small HF ids
   - rejects / refuses Base/Large (CC-BY-NC) [VERIFIED: THIRD_PARTY_MODELS + depth mapping allowlist]
4. **Preferred backend → device policy** (honest v1 semantics):

| preferred_backend | Serve behavior v1 |
|-------------------|-------------------|
| `torch` | Pass `device` from `device_id` if CUDA-like (`cuda:0`); else `resolve_device()` |
| `cpu` / `onnxruntime` | Force worker `device="cpu"`; log that ORT is export target, live path still PyTorch CPU unless ORT backend added later |
| `tensorrt` | **Do not silently claim TRT inference.** Log: “preferred_backend=tensorrt → live path still PyTorch CUDA if available; build engines via export recipes.” Optionally force `device="cuda:0"` / `"0"` for Jetson CUDA PyTorch |
| `openvino` | Log advisory only (enum exists; no runtime) |

5. **Serve startup banner** must print: profile, detector weight, open-vocab weight, depth model id, preferred_backend, resolved device, probe summary.

6. **`probe_device` (discretion — recommend light upgrade):**
   - If `torch` importable: set `available=torch.cuda.is_available()` for desktop/jetson; for cpu profile, `available=True` with backend cpu
   - Never raise; never import torch if not installed
   - Update tests that currently assert always-unavailable

#### Discretion recommendations (locked for planner unless user overrides)

| Decision | Recommendation | Rationale |
|----------|-----------------|-----------|
| Serve default profile | **Keep `cpu-fallback`** | Safe for CI/laptops without CUDA; desktop path is documented with `--profile desktop-gpu` |
| Auto-switch to desktop-gpu when CUDA detected | **No** for v1 | Surprises CI and reproducibility; opt-in profile is clearer |
| Open-vocab default on jetson/cpu | **Remain off** (already) | EDGE research + Phase 6: never always-on on edge |
| Load YOLOE at serve on edge | Keep constructing worker (mode off) **or** lazy-load on first Run | Lazy-load is nicer for Jetson RAM but larger code change — prefer keep current construct + mode off unless RAM issues surface |
| Real ORT/TRT InferenceBackend | **Out of Phase 7** | Recipes only per CONTEXT |

**Confidence:** HIGH for wiring tiers; MEDIUM for “backend” honesty wording (must not overclaim TRT live path).

### EDGE-03 — ONNX / TensorRT export recipes

#### YOLO26 / YOLOE [VERIFIED: ultralytics 8.4.116]

Installed API:

```python
from ultralytics import YOLO, YOLOE

YOLO("yolo26n.pt").export(format="onnx", imgsz=640, simplify=True)
YOLO("yolo26n.pt").export(format="engine", imgsz=640, quantize=16, device=0)  # TensorRT FP16
# YOLOE also exposes .export (same Exporter)
```

Export formats include ONNX (`.onnx`, CPU+GPU) and TensorRT (`engine`, **GPU only**) [VERIFIED: `export_formats()`].

**Prescribe layout:**

```
docs/export/
  README.md              # index: when to export, honesty notes
  yolo26-onnx-tensorrt.md
  yoloe-export.md        # maturity caveats; keep PyTorch fallback
  depth-anything-v2.md   # feasibility + community links; Sentry still HF by default
  jetson-packaging.md    # JetPack matrix “as of”, on-device engine build
scripts/export/
  export_yolo.py         # thin CLI wrapping ultralytics export
  README.md              # how to run; not imported by package runtime
```

**Hard rules for docs/scripts:**

1. **Build TensorRT engines on the target device** (same GPU arch + TensorRT/JetPack version). Never copy `.engine` across JetPack SKUs or desktop→Jetson. [CITED: .planning/research/STACK.md; Ultralytics Jetson guide lineage]
2. **CI must not require Jetson or TRT** — scripts may dry-run arg parse; optional `@pytest.mark.export` skipped by default.
3. **Do not ship prebuilt engines** in the repo or wheel.
4. **YOLOE export:** document try-ONNX path; if export fails or open-vocab text prompts break after export, keep **PyTorch YOLOE** as supported edge path for OV (on-demand only). [ASSUMED: YOLOE TRT text-prompt maturity incomplete — flag for validation]
5. **Depth Anything V2:** live path remains HF Transformers Small. Export section documents community ONNX/TRT projects and that metric/relative preprocessing must preserve `depth_kind` honesty. Do not block Phase 7 on first-class DAV2 TRT. [CITED: Depth-Anything-V2 README lists third-party ONNX/TRT links]
6. **Pi/CPU messaging:** YOLO26n ONNX + DAV2 Small + open-vocab off; **no sustained dual-model realtime claim** without measured FPS. Language: “spatial awareness lite / best-effort.”

#### Package extras for export

**Recommendation:** **docs + scripts only** for v1. Do **not** add `tensorrt` extra. Optional later:

```toml
# NOT required for Phase 7 — only if scripts need bare onnx outside ultralytics
export = ["onnx>=1.16"]
```

Ultralytics export already pulls needed pieces for YOLO ONNX/`engine` when the environment has CUDA+TRT.

**Confidence:** HIGH for YOLO ONNX/engine recipe shape; MEDIUM for YOLOE export completeness; MEDIUM for DAV2 export (community-only).

### EDGE-04 — Extension stubs

#### Multi-cam `camera_id` schema tests

Already present: `camera_id` on Frame / PerceptionFrame / products / sources [VERIFIED: codebase].

**Missing:** explicit tests that:

1. Two distinct `camera_id`s validate as separate identities (`cam0` vs `cam1`)
2. Assembler / store products preserve `camera_id` (no cross-camera overwrite assumption in single-pipeline v1)
3. Docstring/README note: **v1 is single active source**; multi-cam fusion is v2; `camera_id` is the extension key

No multi-source concurrent pipeline in Phase 7.

#### ROS2 bridge scaffold

**Recommend importable stub (not README-only):**

```
src/sentry_ai/extensions/
  __init__.py
  ros2/
    __init__.py
    bridge.py      # Ros2PerceptionBridge
    README.md      # install notes, message mapping sketch, deferred production scope
```

```python
class Ros2PerceptionBridge:
    """Stub sink-like bridge. Not a production ROS2 node (EDGE-04)."""
    name = "ros2_perception"

    def start(self) -> None:
        raise NotImplementedError(
            "ROS2 bridge is a v1 extension stub. See sentry_ai.extensions.ros2 README."
        )

    def emit(self, item: object) -> None:
        raise NotImplementedError(...)

    def close(self) -> None:
        return None
```

Optional: register as sink entry point `ros2-stub` **or** keep out of default `register_builtins` so health stays clean — prefer **importable without auto-register**, document entry-point snippet for integrators.

Do **not** depend on `rclpy` in core extras.

#### Voice plugin no-op

```python
class VoiceNullSink:  # or VoiceNoopSink
    name = "voice-null"
    def emit(self, item: object) -> None: ...
    def close(self) -> None: ...
```

Register under `sentry_ai.sinks` entry point `voice-null` + `register_builtins` optional. Document: no ASR/TTS; future voice I/O plugs here.

**Confidence:** HIGH.

### EDGE-05 — Headless mode

**Recommend:** `--no-ui` flag on `sentry serve` (+ optional env `SENTRY_NO_UI=1` for containers).

Implementation sketch:

```python
# create_app(..., serve_ui: bool = True)
# routes_preview.root_preview:
#   if not serve_ui: return JSONResponse({"detail": "UI disabled (headless)", "v1": "/v1/snapshot"}, 404)
# Keep: /v1/*, /api/*, /preview/mjpeg (useful for remote debug), /api/status
```

**Do not** remove MJPEG by default in headless — robots use `/v1`; MJPEG is still a debug surface. If planner wants pure API, add `--no-preview` later (out of minimal EDGE-05).

**Security note:** Headless does **not** equal safe LAN bind. Keep default `127.0.0.1`; keep non-localhost warning. Document that headless on `0.0.0.0` still exposes camera-derived perception without auth.

**Avoid** separate `sentry api` command in v1 (duplication).

**Confidence:** HIGH.

### Docs — safety / privacy / non-autonomy (cross-cutting EDGE-01/03/04)

Finalize in README + short `docs/safety-and-privacy.md`:

1. **Perception-only** — no motor/cmd_vel/path_plan (API-05 already enforced in code)
2. **Not autonomous driving / FSD** — monocular hobby perception ≠ vehicle-grade
3. **Free-space is not a safety interlock** — incomplete/STALE flags; human/robot controller owns e-stop
4. **Privacy** — localhost default; LAN opt-in unauthenticated; no mandatory cloud (`allow_cloud: false`)
5. **Licenses** — Ultralytics AGPL for detect/OV; DAV2 Small Apache default

## Architecture Patterns

### System Architecture Diagram

```
                    CLI: sentry serve [--profile] [--no-ui]
                              │
                              ▼
                    load_config(profile)
                              │
              ┌───────────────┼────────────────────────┐
              ▼               ▼                        ▼
        detector_tier   depth_tier              preferred_backend
        → YOLO weights  → DAV2 Small id         → device policy
        open_vocab_tier → YOLOE n/s weights     → startup log
              │               │                        │
              ▼               ▼                        ▼
        DetectionLoop    DepthLoop              resolve/force device
        OpenVocabLoop    FreeSpaceLoop                 │
              │               │                        │
              └───────┬───────┘                        │
                      ▼                                │
               PerceptionStore ◄────────────────────────┘
                      │
          ┌───────────┴────────────┐
          ▼                        ▼
   serve_ui?                 /v1 snapshot+stream
   yes → GET / HTML          /api/* controls
   no  → 404/JSON            /preview/mjpeg (keep)
          │
          ▼
   Extension stubs (not on hot path):
   Ros2PerceptionBridge (NotImplemented)
   VoiceNullSink (no-op)
   camera_id multi-id schema tests
```

### Recommended Project Structure (Phase 7 deltas)

```
src/sentry_ai/
├── api/
│   ├── app.py                 # serve_ui flag
│   └── routes_preview.py      # gate GET /
├── backend/
│   └── protocols.py           # light probe_device
├── config/
│   ├── models.py              # optional open_vocab_tier
│   ├── load.py                # unchanged merge order
│   └── profiles/*.yaml        # ensure tiers + comments honest
├── models/
│   ├── cache.py               # tier_to_open_vocab_weight (+ depth tier helper)
│   └── depth/mapping.py       # depth_tier allowlist enforce
├── extensions/                # NEW
│   ├── ros2/
│   └── voice/
├── plugins/builtins.py        # VoiceNullSink optional
└── cli.py                     # --no-ui; apply profile to workers; banner

docs/
├── desktop-gpu.md             # EDGE-01
├── export/                    # EDGE-03
├── safety-and-privacy.md      # release docs
└── camera-sources.md          # existing

scripts/export/                # EDGE-03
tests/
├── test_profile_application.py
├── test_headless_serve.py
├── test_camera_id_multi.py
├── test_extensions_stubs.py
└── test_export_script_cli.py  # argparse only; no GPU export in CI
```

### Pattern 1: Profile application at serve construction

**What:** Single function `apply_profile_to_workers(cfg) -> ProfileRuntime` used by CLI.

**When to use:** Whenever constructing YOLO/YOLOE/Depth workers.

```python
# Source: recommended Phase 7 pattern (local)
@dataclass
class ProfileRuntime:
    detector_weights: str
    open_vocab_weights: str
    depth_model_id: str | None  # None → worker default Small
    device: str | None          # forced device or None for auto
    preferred_backend: str
    profile: RuntimeProfile

def profile_runtime(cfg: SentryConfig) -> ProfileRuntime:
    det = tier_to_weight(cfg.models.detector_tier)
    ov = tier_to_open_vocab_weight(
        getattr(cfg.models, "open_vocab_tier", None) or cfg.models.detector_tier
    )
    device = device_for_backend(cfg.device.preferred_backend, cfg.device.device_id)
    return ProfileRuntime(...)
```

### Pattern 2: Headless via create_app flag

**What:** UI is a route concern, not a second process.

```python
# Source: recommended — FastAPI pattern [ASSUMED local design]
app = create_app(..., serve_ui=not no_ui)
# preview root checks request.app.state.serve_ui
```

### Pattern 3: Export scripts are offline tools

**What:** Scripts live outside import graph of `sentry_ai` runtime; makers run them explicitly.

```python
# Source: Ultralytics export API [VERIFIED: ultralytics YOLO.export]
from ultralytics import YOLO
path = YOLO("yolo26n.pt").export(format="onnx", imgsz=640, simplify=True)
```

### Anti-Patterns to Avoid

- **Advertising `preferred_backend: tensorrt` as live TRT inference without an engine loader** — log honesty
- **Copying `.engine` files between Jetson SKUs / JetPack versions**
- **Claiming Pi dual-model realtime FPS without measurements**
- **Headless on `0.0.0.0` without repeating auth warning**
- **Pulling `rclpy` into core dependencies for a stub**
- **Adding Base/Large DAV2 via depth_tier (CC-BY-NC)**
- **React/Vite rewrite** (out of scope)
- **Full TRT runtime in Phase 7** (recipes only)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YOLO ONNX/TRT export | Custom torch.onnx + TRT builder scripts from scratch | Ultralytics `model.export` | Handles YOLO26 NMS-free graph, opset, simplify [VERIFIED: ultralytics] |
| Device selection | Hardcoded `cuda:0` everywhere | Profile device policy + existing `resolve_device` | Multi-target + MPS/CPU laptops |
| ROS2 messages | Full msg package + QoS matrix | Stub + README mapping to PerceptionFrame JSON | Production ROS2 deferred |
| Multi-cam fusion | Calibration + sync | `camera_id` schema + tests | v2 scope |
| Headless process split | Second ASGI app module | Flag on same `create_app` | One lifecycle |
| Engine distribution | Prebuilt TRT in GitHub Releases | On-device build recipe | Portability failures |

**Key insight:** Phase 7 is mostly **wiring + honesty + scaffolding**. The expensive edge work (shared-GPU scheduling, thermal FPS, real TRT backends) is measurement/product follow-on — document limits instead of faking them.

## Common Pitfalls

### Pitfall 1: Overclaiming FPS / “Jetson ready”

**What goes wrong:** README implies full dual-model realtime on Orin/Pi.  
**Why:** Marketing language from FSD inspiration.  
**How to avoid:** Tiered claims — desktop primary; Jetson “n + DAV2 Small, OV off”; Pi “lite, best-effort.” No numeric FPS without measurement.  
**Warning signs:** “realtime on all targets” without profile qualifiers.

### Pitfall 2: TensorRT engine portability

**What goes wrong:** Desktop-built `.engine` fails or mis-infers on Jetson.  
**Why:** Engines are GPU-arch + TRT-version specific.  
**How to avoid:** Docs bold “build on device”; scripts default output to local path; never commit engines.  
**Warning signs:** CI artifact named `yolo26n.engine` for all platforms.

### Pitfall 3: Preferred backend false advertising

**What goes wrong:** Profile says `tensorrt` but process runs PyTorch.  
**Why:** Backend enum existed before runtime.  
**How to avoid:** Startup log clarifies live path vs preferred export target; health may show `preferred_backend` + `live_backend=torch`.  
**Warning signs:** Users file “TRT not used” bugs after `--profile jetson`.

### Pitfall 4: Headless still unsafe on LAN

**What goes wrong:** `--no-ui --host 0.0.0.0` feels “server-like” and secure.  
**Why:** UI absence ≠ auth.  
**How to avoid:** Reuse non-localhost warning; docs section for headless deploy risks.  
**Warning signs:** Docker compose examples binding `0.0.0.0` without warning.

### Pitfall 5: Ultralytics AGPL commercial surprise

**What goes wrong:** Commercial closed fork ships YOLO without AGPL plan.  
**Why:** Detect extra is optional but sticky.  
**How to avoid:** Keep THIRD_PARTY + desktop/export docs AGPL callouts.  
**Warning signs:** Removing license docs “to clean README.”

### Pitfall 6: Open-vocab always-on on edge

**What goes wrong:** Jetson profile loads continuous YOLOE + YOLO + depth → thermal collapse.  
**Why:** Convenience defaults.  
**How to avoid:** Default mode off; n-tier weights on jetson/cpu; docs say on-demand only.  
**Warning signs:** Profile YAML sets continuous OV true.

### Pitfall 7: Depth export changes semantics

**What goes wrong:** Exported depth model outputs treated as meters.  
**Why:** ONNX loses Sentry `depth_kind` metadata.  
**How to avoid:** Export docs require preserving relative vs metric labeling in any future ORT depth worker.  
**Warning signs:** “depth_m” in export sample code.

## Code Examples

### Profile → open-vocab weight

```python
# Source: recommended local helper (mirrors tier_to_weight) [ASSUMED design]
_OV_TIER = {
    "n": "yoloe-26n-seg.pt",
    "s": "yoloe-26s-seg.pt",
    "m": "yoloe-26s-seg.pt",  # no m OV weight in KNOWN_WEIGHTS — stay on s
}

def tier_to_open_vocab_weight(tier: str | None) -> str:
    if tier is None:
        return "yoloe-26s-seg.pt"
    return _OV_TIER.get(str(tier).strip().lower(), "yoloe-26s-seg.pt")
```

### Ultralytics export (YOLO26)

```python
# Source: Ultralytics YOLO.export [VERIFIED: ultralytics 8.4.116]
from ultralytics import YOLO

model = YOLO("yolo26n.pt")
model.export(format="onnx", imgsz=640, simplify=True, dynamic=False)
# On NVIDIA device with TensorRT installed:
# model.export(format="engine", imgsz=640, quantize=16, device=0)
```

### Headless create_app gate

```python
# Source: recommended [ASSUMED local design]
def create_app(..., serve_ui: bool = True) -> FastAPI:
    app = FastAPI(...)
    app.state.serve_ui = serve_ui
    app.include_router(preview_router)  # root handler checks serve_ui
    ...
```

### Device policy from profile

```python
# Source: recommended [ASSUMED local design]
def device_for_backend(backend: str | BackendName, device_id: str) -> str | None:
    b = str(backend)
    if b in {"cpu", "onnxruntime"}:
        return "cpu"
    if b in {"torch", "tensorrt"}:
        # Prefer explicit device_id when it looks like a torch device
        if device_id and device_id not in {"cpu"}:
            return device_id if device_id.startswith("cuda") else "cuda:0"
        return None  # fall through to resolve_device()
    return None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Profiles advisory-only (Phase 1) | Profiles drive detector tier (Phase 3) + must drive more (Phase 7) | Phase 3 / 7 | Multi-target real |
| Desktop-only PyTorch scripts | PyTorch live + ONNX/TRT export recipes | Phase 7 | Deploy path without rewrite |
| Always serve Live Preview | Optional headless API | Phase 7 | Robot deploy without UI assets dependency UX |
| YOLOE s-only | Profile-tiered n/s OV weights | Phase 7 | Edge RAM/FPS honesty |
| Full ROS2 early | HTTP/WS first; ROS2 stub | Project research | Avoids blocking non-ROS makers |

**Deprecated/outdated:**

- Treating `probe_device` always-unavailable as final — upgrade lightly in Phase 7
- Claiming Phase 1 FOUND-06 “profiles exist” equals multi-target deploy — Phase 7 completes the claim

## File / Module Impact Map

| Area | Files | Change type |
|------|-------|-------------|
| Profile apply | `cli.py`, `models/cache.py`, maybe `config/models.py` | Wire tiers + device |
| Depth tier | `models/depth/mapping.py`, `models/depth/worker.py`, `cli.py` | Honor `depth_tier` allowlist |
| Probe | `backend/protocols.py`, `tests/test_backend_protocols.py` | Light availability |
| Headless | `api/app.py`, `api/routes_preview.py`, `cli.py` | `serve_ui` / `--no-ui` |
| Profiles YAML | `config/profiles/*.yaml` | Comments; optional `open_vocab_tier` |
| Export | `docs/export/*`, `scripts/export/*` | New |
| Desktop docs | `docs/desktop-gpu.md`, `README.md` | New / update |
| Safety docs | `docs/safety-and-privacy.md`, `README.md` | New / update |
| ROS2 stub | `src/sentry_ai/extensions/ros2/*` | New |
| Voice stub | `plugins/builtins.py`, `pyproject.toml` entry point | New sink |
| Multi-cam tests | `tests/test_camera_id_multi.py` | New |
| Profile tests | `tests/test_profile_application.py`, extend `test_config_profiles.py` | New |
| Headless tests | `tests/test_headless_serve.py` | New |
| Packaging | `pyproject.toml` force-include if new package data | Only if needed |

## Test Strategy

| Req | Behavior | Test type | Automated command | Exists? |
|-----|----------|-----------|-------------------|---------|
| EDGE-01 | Desktop doc present + links from README | unit (file content) | `pytest tests/test_desktop_docs.py -q` | ❌ Wave 0 |
| EDGE-02 | Profile→detector weights | unit | `pytest tests/test_profile_application.py -q` | ❌ |
| EDGE-02 | Profile→OV weights n/s | unit | same | ❌ |
| EDGE-02 | cpu backend forces device=cpu | unit | same | ❌ |
| EDGE-02 | jetson/desktop still load_config allow_cloud false | unit | existing `test_config_profiles.py` | ✅ |
| EDGE-02 | probe_device optional cuda | unit (mock torch) | `tests/test_backend_protocols.py` update | ⚠️ update |
| EDGE-03 | export script --help / argparse | unit | `tests/test_export_script_cli.py` | ❌ |
| EDGE-03 | export docs mention on-device TRT + no engine copy | unit content | `tests/test_export_docs.py` | ❌ |
| EDGE-04 | multi camera_id schema | unit | `tests/test_camera_id_multi.py` | ❌ |
| EDGE-04 | Ros2 bridge NotImplemented | unit | `tests/test_extensions_stubs.py` | ❌ |
| EDGE-04 | VoiceNullSink no-op + registry | unit | same / plugins tests | ❌ |
| EDGE-05 | create_app(serve_ui=False) → GET / not HTML 200 | API | `tests/test_headless_serve.py` | ❌ |
| EDGE-05 | headless still has /v1/snapshot | API | same | ❌ |
| EDGE-05 | `--no-ui` in serve help | unit | `tests/test_cli_serve.py` extend | ⚠️ |

**CI rule:** Never run real `model.export` or download weights in default suite.

## Validation Architecture

> `workflow.nyquist_validation` is **true** in `.planning/config.json` — include this section.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest ≥8 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_profile_application.py tests/test_headless_serve.py tests/test_extensions_stubs.py tests/test_camera_id_multi.py -q` |
| Full suite command | `uv run pytest -q` (~365 tests today) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EDGE-01 | Desktop GPU E2E doc + README pointer | unit content | `uv run pytest tests/test_desktop_docs.py -q` | ❌ Wave 0 |
| EDGE-02 | Profiles select detector/OV/depth tiers + device policy | unit | `uv run pytest tests/test_profile_application.py tests/test_config_profiles.py -q` | ⚠️ partial |
| EDGE-03 | Export recipes/scripts + on-device TRT notes | unit content + CLI help | `uv run pytest tests/test_export_docs.py tests/test_export_script_cli.py -q` | ❌ Wave 0 |
| EDGE-04 | Multi-cam camera_id + ROS2 stub + voice no-op | unit | `uv run pytest tests/test_camera_id_multi.py tests/test_extensions_stubs.py -q` | ❌ Wave 0 |
| EDGE-05 | Headless API without UI HTML | API | `uv run pytest tests/test_headless_serve.py -q` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** quick command above for touched area
- **Per wave merge:** `uv run pytest -q`
- **Phase gate:** full suite green + ruff before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_profile_application.py` — EDGE-02
- [ ] `tests/test_headless_serve.py` — EDGE-05
- [ ] `tests/test_camera_id_multi.py` — EDGE-04
- [ ] `tests/test_extensions_stubs.py` — EDGE-04
- [ ] `tests/test_export_docs.py` + `tests/test_export_script_cli.py` — EDGE-03
- [ ] `tests/test_desktop_docs.py` — EDGE-01
- [ ] Update `tests/test_backend_protocols.py` if probe_device behavior changes
- [ ] Update `tests/test_cli_serve.py` for `--no-ui`

## Security Domain

> `security_enforcement` not disabled — include.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (localhost default; auth deferred) | Document risk only |
| V3 Session Management | no | — |
| V4 Access Control | partial | Bind default 127.0.0.1; warn on 0.0.0.0 [VERIFIED: cli.py] |
| V5 Input Validation | yes | Pydantic configs; export script path allowlists for weights (`KNOWN_WEIGHTS`) |
| V6 Cryptography | no new | — |

### Known Threat Patterns for this phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unauthenticated LAN camera/API exposure | Information Disclosure | Localhost default; headless ≠ auth; docs warning |
| Export script path traversal (`--weights ../../etc`) | Tampering | Restrict to `KNOWN_WEIGHTS` basenames under cache |
| Overtrusted free-space as safety | Elevation of privilege (safety misuse) | Safety docs; completeness/STALE; no cmd fields |
| Supply-chain TRT wheel mismatch | Denial of Service / Tampering | System JetPack TRT; no random pip tensorrt |
| AGPL compliance blind spot | (legal) | THIRD_PARTY_MODELS.md |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | all | ✓ | 3.14 host / 3.11 project venv | — |
| uv | install/test | ✓ | 0.11.23 | pip |
| pytest suite | validation | ✓ | 365 tests collected | — |
| ultralytics (detect) | export scripts / detect | ✓ in .venv | 8.4.116 | skip export tests |
| torch/transformers | depth | ✓ (depth extra) | present in research env | docs-only depth export notes |
| Jetson / JetPack | on-device TRT | ✗ (dev machine) | — | Docs + scripts only; no CI TRT |
| System TensorRT | engine build | ✗ | — | Document on-device build |
| ROS2 / rclpy | production bridge | ✗ | — | Stub without rclpy |
| slopcheck | package audit | ✗ | — | All new pkgs [ASSUMED] |

**Missing dependencies with no fallback:** none for Phase 7 scope (Jetson absence is expected; recipes are the deliverable).

**Missing dependencies with fallback:** Jetson/TRT → documentation; ROS2 → NotImplemented stub.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | YOLOE `.export` to ONNX/TRT preserves usable open-vocab text-prompt path | EDGE-03 | Must keep PyTorch OV on edge; doc-only export for YOLOE |
| A2 | Light `probe_device` cuda check is acceptable (not always-unavailable) | EDGE-02 | Tests need rewrite; optional stay stub |
| A3 | Forcing `device=cpu` for onnxruntime preferred_backend is enough without ORT runtime | EDGE-02 | Users may expect ORT speedups not delivered |
| A4 | Keeping MJPEG in headless mode is OK for EDGE-05 | EDGE-05 | Purists may want pure API — add flag later |
| A5 | No new pip packages required for Phase 7 | Package audit | Export scripts might want explicit `onnx` dep |
| A6 | JetPack matrix “as of” notes without live Orin measurement are acceptable | EDGE-03 docs | Community may want FPS tables — mark TBD |
| A7 | `open_vocab_tier` can derive from `detector_tier` without new YAML field | EDGE-02 | Explicit field clearer for power users |

**If empty:** N/A — several discretion items need planner/user confirmation only if they reject recommendations above.

## Open Questions

1. **YOLOE export fidelity for text prompts**  
   - What we know: YOLOE class has `.export` in 8.4.116.  
   - What's unclear: whether exported engines support runtime `set_classes` text prompts.  
   - Recommendation: document experimental; default edge OV path remains PyTorch on-demand.

2. **Shared-GPU Jetson scheduling (depth vs detect)**  
   - What we know: research flag from SUMMARY; not measurable without hardware.  
   - What's unclear: priority policy under thermal load.  
   - Recommendation: document “measure on device”; do not invent priority scheduler in Phase 7.

3. **Whether to auto-detect CUDA for default profile**  
   - Recommendation: **no** (see discretion table); document `--profile desktop-gpu`.

## Locked vs Discretionary (planner cheat sheet)

### Locked (must honor)

- Three profiles; drive tiers/backends at serve (not docs-only)
- Export = recipes + scripts; no Jetson CI requirement; no prebuilt engines
- Headless = API without static UI
- Stubs only for ROS2 / multi-cam tests / voice
- Perception-only + privacy + local OSS language finalized
- `allow_cloud: false` default remains

### Discretion (research recommendations)

| Item | Use this |
|------|----------|
| Headless CLI | `--no-ui` (+ optional `SENTRY_NO_UI`) |
| Device probe | Light torch.cuda check; non-fatal |
| Export location | `scripts/export/` + `docs/export/` |
| ROS2 stub | Importable `NotImplemented` module + README |
| Serve default profile | Keep `cpu-fallback` |
| OV on jetson/cpu | Mode off; weights n-tier |
| JetPack wording | Honest “as of research date; verify on device” |
| Package extras for export | None required |

## Sources

### Primary (HIGH confidence)

- Codebase: `config/profiles/*.yaml`, `config/load.py`, `config/models.py`, `cli.py`, `api/app.py`, `api/routes_preview.py`, `backend/protocols.py`, `models/cache.py`, `models/depth/mapping.py`, `plugins/*`, `schemas/*`, `pyproject.toml`, `README.md`, `THIRD_PARTY_MODELS.md`
- Ultralytics 8.4.116 installed: `YOLO.export` / `YOLOE.export`, `export_formats()` including `onnx` and `engine` [VERIFIED: .venv]
- `.planning/research/STACK.md` — multi-target backend policy, TRT on-device, Pi lite [CITED: in-repo research 2026-08-07]
- `.planning/research/PITFALLS.md` — desktop-only trap, engine portability, AGPL [CITED: in-repo]
- `.planning/research/SUMMARY.md` Phase 7 section [CITED: in-repo]
- Phase 6 RESEARCH deferred notes (edge/headless/YOLOE export → Phase 7) [VERIFIED: 06-RESEARCH.md]
- PyPI: `onnx` 1.22.0, `onnxruntime` 1.28.0 [VERIFIED: pypi.org JSON]

### Secondary (MEDIUM confidence)

- Ultralytics public docs pages (export / Jetson) — content partially JS-rendered; API confirmed via package source [CITED: docs.ultralytics.com/modes/export/, guides/nvidia-jetson/]
- Depth Anything V2 README third-party ONNX/TRT links [CITED: github.com/DepthAnything/Depth-Anything-V2]

### Tertiary (LOW confidence)

- Sustained Jetson thermal FPS / shared-GPU priority — not measured this session [ASSUMED]
- YOLOE TensorRT open-vocab prompt support post-export [ASSUMED incomplete]

## Metadata

**Confidence breakdown:**

- Standard stack: **HIGH** — existing project stack + verified Ultralytics export API
- Architecture: **HIGH** — clear gaps vs locked CONTEXT; no speculative rewrite
- Pitfalls: **HIGH** — aligned with prior PITFALLS + code honesty gaps
- YOLOE/DAV2 export depth: **MEDIUM** — needs hardware or smoke export outside CI
- Jetson FPS claims: **LOW** — deliberately undocumented as numbers

**Research date:** 2026-08-08  
**Valid until:** ~2026-09-07 (30 days; re-check Ultralytics export + JetPack notes if newer)

## Project Constraints (from CLAUDE.md)

No project-root `CLAUDE.md` / `AGENTS.md` found in the Sentry workspace. Parent skill note (graphify) does not constrain Phase 7 implementation. Follow existing package conventions: `src/sentry_ai/`, pytest, ruff, optional extras, localhost default, local OSS only.

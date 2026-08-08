# Phase 6: Developer Controls & Open-Vocab - Research

**Researched:** 2026-08-08  
**Domain:** Runtime control plane + YOLOE open-vocabulary detection (Ultralytics) on existing Sentry perception loops  
**Confidence:** HIGH (codebase contracts verified; YOLOE API verified against Ultralytics 8.4.116 + official docs)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Developer-first overlays + controls (not chat-first)
- Fixed-class remains primary continuous path; open-vocab secondary (on-demand / lower rate)
- UI and API share PerceptionStore truth
- Local OSS only (Ultralytics AGPL documented)
- Stages disabled = skip worker / Spatial Post work, not just hide overlay
- From Phase 1–5 shipped:
  - PATCH `/api/detection/config` conf already exists
  - PATCH `/api/depth/config` depth_mode exists
  - DetectionLoop, DepthLoop, FreeSpaceLoop + serve lifecycle
  - Live Preview conf slider + status polling
  - `/v1/snapshot` + `/v1/stream` assembler
  - MJPEG overlay pipeline

### Claude's Discretion
- Control plane shape: `/api/pipeline/config` vs per-stage routes
- Open-vocab via YOLOE in same `detect` extra vs separate extra
- How open-vocab merges into Detection list (separate field vs tagged class_name prefix)
- Source switch in UI (synthetic/usb) vs CLI-only for v1 Phase 6
- Free-space cutoff knobs wired into FreeSpaceLoop config

### Deferred Ideas (OUT OF SCOPE)
- Edge profiles / headless packaging → Phase 7  
- Voice / VLM chat → v2  
- Full multi-source switcher UX if not cheap → optional  
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-03 | Toggle perception stages (detection, depth, free-space) at runtime | Thread-safe enable flags on loops; PATCH `/api/pipeline/config`; disabled = skip compute |
| UI-04 | Adjust thresholds (det conf, free-space near/mid cutoffs) interactively | Existing conf PATCH + FreeSpaceLoop runtime cutoffs + UI sliders |
| UI-05 | Dashboard performance telemetry (FPS, stage latency) | Expand status + Live Preview footer from store metrics already present |
| OVD-01 | Open-vocab detector (YOLOE) accepts text prompts | `YOLOE.set_classes` + `predict`; YoloeWorker with injectable model |
| OVD-02 | On-demand or lower-rate without blocking fixed-class | Separate OpenVocabLoop + modes off/on_demand/continuous |
| OVD-03 | Open-vocab on dashboard + stream when enabled | Store product + assembler merge + distinct overlay color |
</phase_requirements>

## Summary

Phase 6 makes the Live Preview a full developer console and adds YOLOE open-vocabulary detection as a **secondary path** that must never stall fixed-class detection, depth, or capture. The shipped system already has the right spine: daemon stage loops (DetectionLoop / DepthLoop / FreeSpaceLoop), keep-latest PerceptionStore, cold-path PATCH configs for det conf and depth mode, MJPEG overlays from store truth, and `/v1` assembly. What is missing is a **unified pipeline control plane** (stage enable + free-space cutoffs), **loop-level pause gates** (skip compute without tearing down `sentry serve`), and a **parallel open-vocab worker/loop** with prompt UX.

Open-vocab must be a separate producer. DetectionLoop and OpenVocabLoop must not both call `set_detections` or they will thrash. Research recommends a fourth store product (`OpenVocabProduct`), assembler merge into wire `detections` with an additive optional `source` field, and distinct overlay color/prefix. YOLOE is already inside the installed `detect` extra (`ultralytics-opencv-headless` 8.4.116); no new package required. Default weights: `yoloe-26s-seg.pt` (desktop) with cache under `SENTRY_MODEL_CACHE/weights`. Modes: off (default) → Run (single-shot on-demand) → optional continuous lower-rate (e.g. 2 Hz / every N frames).

**Primary recommendation:** Ship plan 06-01 (control plane + stage gates + free-space cutoffs + telemetry UI) then 06-02 (YOLOE worker + OpenVocabLoop + prompt UX + store/stream/overlay merge). Prefer enable-flag pause over start/stop threads; prefer unified GET/PATCH `/api/pipeline/config` while keeping existing per-stage conf routes.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Stage enable/disable | API / Backend (control plane + loops) | Browser (checkboxes) | Loops own compute skip; UI only RPC |
| Det conf threshold | API / Backend (worker lock) | Browser (slider) | Already `YoloDetectionWorker.set_conf` |
| Free-space near/mid cutoffs | API / Backend (FreeSpaceLoop config) | Browser (sliders) | Pure Spatial Post params; no model reload |
| Depth mode (existing) | API / Backend | Browser (optional) | Already PATCH `/api/depth/config` |
| Performance telemetry | Database / Storage (store metrics) | Browser (footer panel) | Metrics already in PerceptionStore + `/api/status` |
| Open-vocab prompt + schedule | API / Backend (OpenVocabLoop) | Browser (text + Run/enable) | Cold path sets classes; loop owns rate |
| Open-vocab inference | API / Backend (YOLOE worker) | — | Local OSS; never in browser |
| Merge OV + fixed dets | API / Backend (store + assemble) | CDN / Static (overlay draw) | Single truth for UI-06 / OVD-03 |
| Live preview overlays | Frontend Server (MJPEG encode) | Browser (display) | Server-drawn boxes from store |
| Capture always-on | API / Backend (CaptureLoop) | — | Stage toggles must not stop capture/serve |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.11+ (repo requires ≥3.11) | Runtime | Existing package baseline [VERIFIED: pyproject.toml] |
| FastAPI | ≥0.141,<1 (installed) | REST control plane | Existing routes pattern [VERIFIED: codebase] |
| Pydantic | 2.x | Config bodies `extra=forbid` | Existing DetectionConfigUpdate / DepthConfigUpdate [VERIFIED: codebase] |
| Ultralytics YOLOE | **8.4.116** via `ultralytics-opencv-headless` | Open-vocab text prompts | Official YOLOE API; same detect extra [VERIFIED: .venv + docs.ultralytics.com/models/yoloe] |
| YOLOE weights | **`yoloe-26s-seg.pt`** default desktop | Text-prompt open-vocab | Aligns with YOLO26 family; s-scale realtime [CITED: docs.ultralytics.com/models/yoloe] |
| NumPy / OpenCV | existing | Free-space cutoffs + overlay | No new deps [VERIFIED: codebase] |
| pytest | ≥8 | Unit/API tests with mocks | Existing suite [VERIFIED: pyproject.toml] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `threading.Lock` / `Event` | stdlib | Stage enable + conf/cutoffs | All runtime knobs (match worker conf pattern) |
| Existing `results_to_detections` | local | Map YOLOE Results → Detection | Reuse; add source tag post-map |
| `configure_model_cache` | local | Weights under SENTRY_MODEL_CACHE | Extend KNOWN_WEIGHTS for YOLOE files |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| YOLOE | YOLO-World (`set_classes`) | Still valid fallback; YOLOE is current Ultralytics OV push [CITED: STACK.md + docs] |
| YOLOE | Grounding DINO | Accuracy↑ FPS↓ — not live path [CITED: STACK.md] |
| Separate OV store product | Prefix-only merge into fixed dets in one loop | Simpler schema but couples rates and races |
| Unified `/api/pipeline/config` | Only expand per-stage routes | More endpoints; harder UI batch PATCH |
| New `openvocab` extra | Same `detect` extra | Extra package surface for zero new deps — avoid |
| React/Vite rewrite | Extend static `index.html` | CONTEXT locks static extend for Phase 6 |

**Installation:**

```bash
# No new package for open-vocab — YOLOE ships with detect extra
uv sync --extra dev --extra detect --extra depth

# First-run weights (YOLOE) land under SENTRY_MODEL_CACHE/weights via Ultralytics
# Default: yoloe-26s-seg.pt (desktop); document yoloe-26n-seg.pt for edge later
```

**Version verification:**

| Package | Verified version | Source |
|---------|------------------|--------|
| `ultralytics-opencv-headless` | **8.4.116** | `.venv` + PyPI [VERIFIED: npm N/A — PyPI] |
| ultralytics (upstream) | **8.4.116** | PyPI JSON 2026-08-08 [VERIFIED: pypi.org/pypi/ultralytics/json] |
| YOLOE class | `ultralytics.models.yolo.model.YOLOE` | Installed package [VERIFIED: .venv] |

## Package Legitimacy Audit

> Phase 6 does **not** require installing a new third-party package name. Open-vocab uses the existing `detect` extra.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `ultralytics-opencv-headless` | PyPI | mature (Ultralytics line) | high (Ultralytics ecosystem) | github.com/ultralytics/ultralytics | unavailable | **Approved — already in pyproject detect extra** [ASSUMED legitimacy gate: slopcheck not installed] |

**Packages removed due to slopcheck [SLOP] verdict:** none  
**Packages flagged as suspicious [SUS]:** none  

*slopcheck was unavailable at research time. No new packages recommended. Existing detect extra is already project-locked from Phase 3.*

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────┐
  UI / REST cold    │  Control plane               │
  path              │  GET/PATCH /api/pipeline/*   │
  (not hot path)    │  PATCH /api/detection/config │
                    │  PATCH /api/depth/config     │
                    │  PATCH /api/open-vocab/*     │
                    └──────┬──────────────────────┘
                           │ thread-safe flags + thresholds
           ┌───────────────┼────────────────┬──────────────────┐
           ▼               ▼                ▼                  ▼
     DetectionLoop    DepthLoop      FreeSpaceLoop      OpenVocabLoop
     enabled?         enabled?       enabled?           mode + rate
     conf             depth_mode     near/mid cut       set_classes
           │               │                │                  │
           │               │                │                  │
           └───────┬───────┘                │                  │
                   │                        │                  │
                   ▼                        ▼                  ▼
            PerceptionStore  ◄── depth ── Spatial Post    OpenVocabProduct
            det | depth | free_space | open_vocab
                   │
         assemble_perception_frame (merge dets + OV)
                   │
          ┌────────┴────────┐
          ▼                 ▼
   MJPEG overlays      /v1 snapshot+stream
   (distinct OV color)   (source-tagged dets)
```

Hot path remains: FrameBus → stage loops → store → assemble / MJPEG.  
Cold path only mutates flags/thresholds/prompts for **next** frames.

### Recommended Project Structure

```
src/sentry_ai/
├── api/
│   ├── routes_pipeline.py      # NEW: GET/PATCH stage flags + free-space cutoffs
│   ├── routes_open_vocab.py    # NEW: prompt, mode, conf, run-once
│   ├── routes_detection.py     # KEEP conf PATCH
│   ├── routes_depth.py         # KEEP depth_mode
│   ├── routes_preview.py       # EXTEND status + MJPEG OV draw
│   ├── assemble.py             # EXTEND merge open-vocab dets
│   ├── app.py                  # wire routers + open_vocab_worker
│   └── deps.py                 # optional open_vocab_worker on AppState
├── control/                    # NEW small package OR api/pipeline_state.py
│   └── pipeline_state.py       # thread-safe PipelineState (flags + cutoffs)
├── models/detection/
│   ├── yolo_worker.py          # unchanged fixed-class
│   ├── yoloe_worker.py         # NEW open-vocab worker
│   ├── open_vocab_loop.py      # NEW OpenVocabLoop (or models/open_vocab/)
│   ├── mapping.py              # reuse results_to_detections
│   └── overlay.py              # EXTEND color by source
├── spatial/loop.py             # EXTEND enabled + near/mid cut setters
├── models/detection/loop.py    # EXTEND enabled gate
├── models/depth/loop.py        # EXTEND enabled gate
├── state/perception_store.py   # EXTEND OpenVocabProduct + metrics
├── models/cache.py             # EXTEND KNOWN_WEIGHTS for yoloe-*.pt
├── cli.py                      # wire OpenVocabLoop lifecycle
└── ui/static/index.html        # stage toggles, cutoffs, OV UX, telemetry
tests/
├── test_pipeline_config.py
├── test_loop_enable_gates.py
├── test_free_space_runtime_cuts.py
├── test_yoloe_worker.py
├── test_open_vocab_loop.py
├── test_api_open_vocab.py
└── test_assemble_open_vocab.py
```

### Pattern 1: Thread-safe PipelineState (cold path)

**What:** One object owned by serve, injected into loops + FastAPI `app.state`.  
**When to use:** All stage flags and free-space cutoffs (UI-03/UI-04).

```python
# Recommended shape (prescriptive)
@dataclass
class PipelineState:
    _lock: threading.Lock = field(default_factory=threading.Lock)
    detection_enabled: bool = True
    depth_enabled: bool = True
    free_space_enabled: bool = True
    near_cut: float = 0.72  # DEFAULT_NEAR_CUT
    mid_cut: float = 0.45   # DEFAULT_MID_CUT

    def snapshot(self) -> dict: ...
    def update(self, **kwargs) -> dict: ...  # validate + lock
```

Loops read via `pipeline.is_enabled("detection")` under lock (or copy flags each iteration). **Never** block the FastAPI event loop on inference.

### Pattern 2: Enable gate inside loop (pause without teardown)

**What:** At top of `_run` iteration, if disabled → `Event.wait(0.01)` and continue; do not call `worker.process`.  
**When to use:** DetectionLoop, DepthLoop, FreeSpaceLoop, OpenVocabLoop.

```python
# Structural addition to existing loops
while not self._stop.is_set():
    if not self._enabled.is_set():  # or pipeline flag
        # Optional once: clear product so completeness goes false after disable
        self._stop.wait(0.01)
        continue
    # existing keep-latest process path...
```

**Do not** call `loop.stop()` for UI toggles — that joins threads and complicates re-enable. Keep threads alive for serve lifetime; only `_stop` on process shutdown (existing cli.py pattern).

**On disable (recommended default):**
1. Stop producing new products immediately (skip compute).  
2. Clear the stage product once (`set_*` with empty/error or explicit clear method) so `/v1` completeness flips false and overlays drop.  
3. Do **not** clear capture or other stages.

### Pattern 3: Free-space runtime cutoffs

**What:** FreeSpaceLoop holds `near_cut` / `mid_cut` behind a lock; pass into `compute_free_space(...)` each frame.  
**When to use:** UI-04 free-space sliders.

Validation (prescriptive):
- Both in `[0.0, 1.0]`
- Require `near_cut > mid_cut` (else 422)
- Defaults: `near_cut=0.72`, `mid_cut=0.45` [VERIFIED: free_space.py]

`OccupancySmoother` state stays on FreeSpaceLoop; changing cuts does not require smoother reset (acceptable flicker for 1–2 frames).

### Pattern 4: YOLOE open-vocab worker (prompt-then-detect)

**What:** Mirror `YoloDetectionWorker` with injectable model for tests.  
**Official API** [CITED: docs.ultralytics.com/models/yoloe + ultralytics 8.4.116]:

```python
from ultralytics import YOLOE

model = YOLOE("yoloe-26s-seg.pt")
# Once per prompt change (cold path / next process):
model.set_classes(["person", "red cup", "toolbox"])
results = model.predict(
    source=image_bgr,
    conf=0.25,
    imgsz=640,
    verbose=False,
    save=False,
)
# results[0].boxes → results_to_detections; ignore masks for v1 boxes
```

Notes:
- `set_classes(classes: list[str], embeddings=None)` generates text PE when embeddings omitted [VERIFIED: installed YOLOE.set_classes].  
- Call `set_classes` only when prompt changes (CLIP encode cost); not every frame.  
- `predict` accepts conf like fixed YOLO.  
- Segmentation masks exist; **v1 draws boxes only** (same Detection schema).  
- Visual prompts / prompt-free PF weights are **out of scope** for Phase 6.

### Pattern 5: OpenVocabLoop scheduling (OVD-02)

| Mode | Behavior | Default |
|------|----------|---------|
| `off` | Loop sleeps; no product / cleared | **Yes** |
| `on_demand` | Process **one** latest frame after Run/prompt, then idle | After Run |
| `continuous` | Process at lower rate (recommended **every_n=3** or **min_interval_ms=500**) | Opt-in checkbox |

Prescriptive defaults:
- Default mode: `off`  
- Run button → set prompt + mode `on_demand` + arm one-shot  
- Continuous enable → `continuous` with `every_n=3` (or 2 Hz)  
- Fixed-class DetectionLoop **always independent** (own thread, own enable flag)

### Pattern 6: Merge strategy (OVD-03) — **recommended**

| Approach | Verdict |
|----------|---------|
| **A. Fourth store product `OpenVocabProduct` + assembler merge** | **Use this** — no writer race; dual rate OK |
| B. Single DetectionProduct, one writer merges | Couples loops; harder |
| C. Separate wire field `open_vocab: list[Detection]` | Clean but expands robot schema more; optional later |
| D. Class name prefix only `ov:red cup` | Works without schema change; weaker typing |

**Prescriptive merge:**
1. Add `OpenVocabProduct` + `set_open_vocab` / `snapshot_open_vocab` + ov metrics on PerceptionStore.  
2. Extend `Detection` with optional `source: Literal["fixed", "open_vocab"] = "fixed"` (additive; `extra=forbid` still OK).  
3. `assemble_perception_frame` concatenates fixed + OV detections (OV first or last — prefer **fixed first, OV after**).  
4. Completeness.detections true if **either** product present (and no hard error policy — match fixed: present counts).  
5. Overlay: fixed color existing cyan `(0,255,180)`; OV distinct e.g. magenta `(255,0,255)` or orange; label may include `ov:` prefix for readability.  
6. When OV mode `off`, clear OV product; stream shows fixed only.

### Pattern 7: Control plane API shape — **recommended**

| Endpoint | Role |
|----------|------|
| `GET/PATCH /api/pipeline/config` | Stages enabled + free-space cutoffs (+ optional rates) |
| `GET/PATCH /api/detection/config` | Keep conf (compat) |
| `GET/PATCH /api/depth/config` | Keep depth_mode (compat) |
| `GET/PATCH /api/open-vocab/config` | prompt, mode, conf, every_n |
| `POST /api/open-vocab/run` | Optional explicit one-shot arm |

PATCH pipeline body example:

```json
{
  "detection_enabled": true,
  "depth_enabled": true,
  "free_space_enabled": true,
  "near_cut": 0.72,
  "mid_cut": 0.45
}
```

All fields optional; `extra=forbid`; return full snapshot.

### Anti-Patterns to Avoid

- **Hide-only toggles:** UI hiding overlays while workers still run — violates UI-03 / CONTEXT  
- **stop()/start() threads per toggle:** Join races, GPU reload thrash, serve fragility  
- **Open-vocab on DetectionLoop same thread:** Blocks fixed-class FPS (OVD-02 fail)  
- **Dual writers to `set_detections`:** Silent thrashing / lost boxes  
- **`set_classes` every frame:** Unnecessary CLIP encode cost  
- **Always-on continuous OV by default:** GPU contention; CONTEXT says secondary  
- **React rewrite:** Deferred; extend static HTML  
- **Source switcher as Phase 6 blocker:** CLI-only is fine (discretion → recommend defer)  
- **Motor/safety language in UI:** Keep perception-only (API-05)  
- **Downloading weights in unit tests:** Inject fake model like Phase 3

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Open-vocab detection | Custom CLIP+YOLO head | Ultralytics YOLOE | PE, set_classes, predict battle-tested |
| Thread-safe conf | ad-hoc globals | Worker lock pattern from YoloDetectionWorker | Already proven DET-03 |
| Free-space bands | New network | `compute_free_space` + runtime cuts | Pure algorithm already shipped |
| Overlay drawing | Client canvas rewrite | Server `draw_detections` + color branch | UI-06 store parity |
| Model download/cache | Custom HTTP fetch | `configure_model_cache` + Ultralytics weights_dir | MODEL-02 |
| Stage telemetry | Custom metrics bus | PerceptionStore.metrics_snapshot | Already has det/depth/fs fps |

**Key insight:** Phase 6 is **control + scheduling + thin YOLOE worker**, not a new perception architecture.

## Common Pitfalls

### Pitfall 1: Pause = teardown
**What goes wrong:** UI disable calls `loop.stop()`; re-enable is slow or broken.  
**Why:** join + thread recreate + model still loaded but lifecycle races.  
**How to avoid:** enable Event/flag; stop only on serve shutdown.  
**Warning signs:** serve must restart to re-enable stage.

### Pitfall 2: Writer race on detections
**What goes wrong:** Fixed and OV alternate overwriting store.  
**Why:** single DetectionProduct mailbox.  
**How to avoid:** OpenVocabProduct + merge in assemble/overlay.  
**Warning signs:** flickering class sets; missing fixed boxes when OV runs.

### Pitfall 3: Disable depth but leave free-space "fresh"
**What goes wrong:** Free-space continues from last depth map or stale product looks live.  
**Why:** FreeSpaceLoop polls store depth independently.  
**How to avoid:** Free-space enable gate; when depth disabled, free-space should idle (no new depth) and/or clear free-space product when either stage disabled. Prefer: if depth disabled → clear depth product; free-space idles on missing depth (already) + clear free-space when free-space disabled.  
**Warning signs:** free-space age stays low while depth toggle off.

### Pitfall 4: Invalid near/mid ordering
**What goes wrong:** `mid_cut >= near_cut` empties mid band or confuses occupancy.  
**How to avoid:** validate `near_cut > mid_cut` on PATCH.  
**Warning signs:** bands always 0 mid_frac.

### Pitfall 5: YOLOE first-run download blocks UI thread
**What goes wrong:** PATCH run triggers weight download on request thread.  
**How to avoid:** Lazy load inside worker thread on first process (like YOLO fixed); return 202/armed immediately; surface `loading`/`error` on status.  
**Warning signs:** HTTP hang on first Run.

### Pitfall 6: AGPL surprise
**What goes wrong:** Contributors ship commercial closed fork unaware.  
**How to avoid:** THIRD_PARTY_MODELS.md YOLOE row active + UI note (same as YOLO26).  
**Warning signs:** missing AGPL mention for YOLOE.

### Pitfall 7: Telemetry only on API, not dashboard
**What goes wrong:** UI-05 incomplete; makers only see capture FPS.  
**How to avoid:** Footer already has det/depth/fs ms — add **det_fps, depth_fps, free_space_fps, ov_ms/ov_fps** from `/api/status` (metrics already mostly present).  
**Warning signs:** status JSON has fps fields UI never renders.

### Pitfall 8: Continuous OV starves GPU for depth/det
**What goes wrong:** shared GPU, both at full rate.  
**How to avoid:** default off; continuous every_n≥3; document.  
**Warning signs:** det_latency_ms spikes when OV continuous on.

## Code Examples

### YOLOE text prompt (official)

```python
# Source: https://docs.ultralytics.com/models/yoloe/ (Text Prompt example)
from ultralytics import YOLOE

model = YOLOE("yoloe-26s-seg.pt")
model.set_classes(["person", "bus"])
results = model.predict("path/to/image.jpg")
```

### Worker-shaped process (Sentry style)

```python
# Pattern mirrors YoloDetectionWorker (src/sentry_ai/models/detection/yolo_worker.py)
class YoloeOpenVocabWorker:
    name = "yoloe-open-vocab"

    def set_prompt_classes(self, classes: list[str]) -> None:
        with self._prompt_lock:
            self._classes = [c.strip() for c in classes if c.strip()]
            self._prompt_dirty = True

    def process(self, frame) -> list[Detection]:
        model = self._ensure_model()
        with self._prompt_lock:
            classes = list(self._classes)
            dirty = self._prompt_dirty
            conf = self._conf
            if dirty:
                model.set_classes(classes)  # cold-ish; once per change
                self._prompt_dirty = False
        if not classes:
            return []
        results = model.predict(
            source=frame.image_bgr, conf=conf, imgsz=640,
            verbose=False, save=False,
        )
        dets = results_to_detections(results[0]) if results else []
        # tag source for merge/overlay
        return [
            Detection(
                class_name=d.class_name,
                confidence=d.confidence,
                bbox_xyxy=d.bbox_xyxy,
                source="open_vocab",
            )
            for d in dets
        ]
```

### Loop enable gate

```python
# Add to DetectionLoop / DepthLoop / FreeSpaceLoop
def set_enabled(self, enabled: bool) -> None:
    if enabled:
        self._enabled.set()
    else:
        self._enabled.clear()
        # optional one-shot clear of product via store

def _run(self) -> None:
    while not self._stop.is_set():
        if not self._enabled.is_set():
            self._stop.wait(0.01)
            continue
        # existing body...
```

### Pipeline PATCH (FastAPI)

```python
class PipelineConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    detection_enabled: bool | None = None
    depth_enabled: bool | None = None
    free_space_enabled: bool | None = None
    near_cut: float | None = Field(default=None, ge=0.0, le=1.0)
    mid_cut: float | None = Field(default=None, ge=0.0, le=1.0)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| YOLO-World primary OV | YOLOE (+ YOLOE-26) | Ultralytics 2025–2026 | Prefer YOLOE; World fallback only if load fails |
| Restart process to retune | Runtime conf PATCH | Phase 3 | Extend to stages + cutoffs |
| Fixed-class only | Fixed + secondary OV | Phase 6 | Dual-rate workers |
| React planned UI | Static Live Preview | Phases 2–5 shipped | Extend HTML, not Vite rewrite |

**Deprecated/outdated for this phase:**
- Grounding DINO / OWL-ViT on live path  
- Always-on open-vocab as default  
- Chat/VLM as primary control surface  
- Full multi-source switcher as required UI (CLI remains source of truth)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `yoloe-26s-seg.pt` is the right default weight (vs 11s) | Standard Stack | Larger download / slightly different AP; still valid OV path |
| A2 | `set_classes` without explicit embeddings is enough for text PE on 8.4.116 | Pattern 4 | May need `get_text_pe` explicit path on some weights — verify with smoke once |
| A3 | Ignoring YOLOE masks is acceptable for v1 (boxes only) | Pattern 4 | Fine for OVD requirements (detections, not seg) |
| A4 | Clearing products on disable is preferred UX | Pattern 2 | Alternative: freeze last product with stale TTL — document if chosen |
| A5 | Source switcher deferred to CLI-only | Discretion | Makers may want UI switch; not required by UI-03–05/OVD |
| A6 | No new pip package; detect extra sufficient | Deps | If headless package ever strips YOLOE (unlikely) — pin note |

**If empty after verification:** A1–A6 remain soft defaults for planner/discuss — not blockers.

## Open Questions

1. **Default YOLOE weight: `yoloe-26s-seg.pt` vs `yoloe-11s-seg.pt` vs `yoloe-26n-seg.pt`?**  
   - What we know: docs list all; 26 aligns with fixed YOLO26; s is desktop-friendly.  
   - Recommendation: **`yoloe-26s-seg.pt`** desktop default; document n for edge (Phase 7).

2. **On disable: clear product vs freeze last with stale?**  
   - Recommendation: **clear once** so completeness/overlays honestly reflect "stage off".

3. **Schema: add `Detection.source` vs prefix-only?**  
   - Recommendation: **additive `source` field** (default `"fixed"`) — small, typed, overlay-friendly.

4. **Continuous rate: every_n vs Hz?**  
   - Recommendation: **`every_n=3`** (simpler, frame-aligned) + expose in config.

5. **Source switcher in UI?**  
   - Recommendation: **CLI-only** for Phase 6 (cheap defer; not in requirements IDs).

6. **Should free-space auto-disable when depth disabled?**  
   - Recommendation: independent flags, but free-space naturally idles without depth; **clear free-space when free-space disabled**; when depth disabled clear depth (free-space stops updating).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | all | ✓ | 3.11 in .venv (system 3.14 also present) | — |
| uv | install | ✓ | 0.11.23 | pip |
| pytest | tests | ✓ | 8.4.2 | — |
| ultralytics-opencv-headless | detect + YOLOE | ✓ in .venv | 8.4.116 | Install detect extra |
| torch / depth extra | depth stage | optional | project depth extra | Stage toggle disabled if missing |
| CUDA GPU | realtime OV+det+depth | environment-dependent | — | CPU slower; continuous OV off |
| slopcheck | package audit | ✗ | — | No new packages; existing extra |
| ctx7 CLI | docs | ✗ | — | Official Ultralytics docs fetched |

**Missing dependencies with no fallback:** none for planning/implementation of control plane + mocked OV tests.

**Missing dependencies with fallback:** GPU (CPU works; document FPS); real YOLOE weights (lazy download first run).

## Validation Architecture

> `workflow.nyquist_validation` is **true** in `.planning/config.json` — section required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest ≥8 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` testpaths=`tests` |
| Quick run command | `uv run pytest tests/test_pipeline_config.py tests/test_loop_enable_gates.py tests/test_yoloe_worker.py -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-03 | PATCH pipeline disables stage → loop skips process | unit/integration | `pytest tests/test_loop_enable_gates.py -q` | ❌ Wave 0 |
| UI-03 | Disabled stage → no new store product / cleared | unit | `pytest tests/test_pipeline_config.py -q` | ❌ Wave 0 |
| UI-04 | conf still PATCHable | unit | `pytest tests/test_api_detection.py -q` | ✅ |
| UI-04 | near/mid cut update affects FreeSpaceLoop | unit | `pytest tests/test_free_space_runtime_cuts.py -q` | ❌ Wave 0 |
| UI-04 | invalid mid≥near → 422 | unit | `pytest tests/test_pipeline_config.py -q` | ❌ Wave 0 |
| UI-05 | status exposes det/depth/fs fps + latency | unit | `pytest tests/test_api_preview.py -q` (extend) | ✅ extend |
| OVD-01 | set_prompt_classes + process with FakeModel | unit | `pytest tests/test_yoloe_worker.py -q` | ❌ Wave 0 |
| OVD-02 | on_demand runs once; continuous respects every_n; fixed loop independent | unit | `pytest tests/test_open_vocab_loop.py -q` | ❌ Wave 0 |
| OVD-03 | assemble merges OV+fixed with source tags | unit | `pytest tests/test_assemble_open_vocab.py -q` | ❌ Wave 0 |
| OVD-03 | MJPEG/API include OV when enabled | unit | `pytest tests/test_api_open_vocab.py -q` | ❌ Wave 0 |
| FOUND-05 | THIRD_PARTY YOLOE AGPL active | unit | `pytest tests/test_third_party_models_doc.py -q` | ✅ extend |
| MODEL-02 | YOLOE weights in KNOWN_WEIGHTS / cache | unit | `pytest tests/test_model_cache.py -q` | ✅ extend |
| API-05 | no motor fields on new routes | unit | `pytest tests/test_api_perception_only.py -q` | ✅ extend |

### Sampling Rate

- **Per task commit:** targeted pytest files for that task (< 30s)  
- **Per wave merge:** `uv run pytest -q`  
- **Phase gate:** full suite green + manual: toggles + Run OV prompt on synthetic/USB (optional real weights)

### Wave 0 Gaps

- [ ] `tests/test_pipeline_config.py` — GET/PATCH `/api/pipeline/config`, validation  
- [ ] `tests/test_loop_enable_gates.py` — Detection/Depth/FreeSpace enable skip  
- [ ] `tests/test_free_space_runtime_cuts.py` — near/mid applied next frame  
- [ ] `tests/test_yoloe_worker.py` — FakeModel, set_classes once, conf, empty prompt  
- [ ] `tests/test_open_vocab_loop.py` — modes off/on_demand/continuous, no fixed-class block  
- [ ] `tests/test_api_open_vocab.py` — config + run endpoints  
- [ ] `tests/test_assemble_open_vocab.py` — merge + completeness  
- [ ] Extend `tests/test_api_preview.py` — stage flags + ov telemetry fields  
- [ ] Extend `tests/test_third_party_models_doc.py` — YOLOE active AGPL  
- [ ] Extend `tests/test_model_cache.py` — yoloe weights known list  
- [ ] Extend `tests/test_cli_serve.py` — OpenVocabLoop lifecycle source asserts  
- [ ] Framework install: none — pytest already present  

**Mocking rule:** All OV tests inject fake model; **never** download YOLOE weights in CI.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (localhost default) | MODEL-03; no auth in v1 |
| V3 Session Management | no | — |
| V4 Access Control | partial | Localhost bind; warn on 0.0.0.0 |
| V5 Input Validation | **yes** | Pydantic `extra=forbid`; conf/cut ranges; prompt length limit |
| V6 Cryptography | no | — |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Oversized / malicious prompt string | DoS | Cap classes count (e.g. ≤32) and string length (e.g. ≤64 chars each); strip empties |
| Path injection via weights name | Tampering | Only KNOWN_WEIGHTS allowlist (extend for yoloe-*.pt) |
| Remote bind without auth | Info disclosure | Keep 127.0.0.1 default; existing serve warning |
| Conf/cut out of range | Tampering | Field(ge/le) + near>mid validation |
| Motor command smuggling in new JSON | Elevation | API-05 denylist tests; PerceptionFrame extra=forbid |

## What NOT to Build (Phase 6)

| Non-goal | Why |
|----------|-----|
| React/Vite frontend rewrite | CONTEXT; static HTML extend |
| VLM / chat UI | Deferred v2 |
| Visual-prompt YOLOE / PF prompt-free as primary | Text prompts only for OVD-01 |
| Grounding DINO / SAM always-on | FPS destroyers |
| TensorRT export for YOLOE | Phase 7 |
| Multi-cam fusion / ROS2 | Phase 7 stubs |
| Robot control / "safe to drive" | API-05 |
| Live source switcher (if non-trivial) | CLI-only recommended |
| Segmentation mask overlays for OV | Boxes only |
| Training / fine-tune YOLOE in product | Docs only |
| New pip dependency for OV | Use detect extra |

## Package Layout (implementation map)

| Package / module | Responsibility |
|------------------|----------------|
| `sentry_ai.control.pipeline_state` (new) or `api.pipeline_state` | Thread-safe flags + free-space cuts |
| `sentry_ai.api.routes_pipeline` | GET/PATCH pipeline |
| `sentry_ai.api.routes_open_vocab` | OV config + run |
| `sentry_ai.models.detection.yoloe_worker` | YOLOE ModelWorker |
| `sentry_ai.models.detection.open_vocab_loop` | Dual-rate / on-demand loop |
| `sentry_ai.state.perception_store` | OpenVocabProduct + metrics |
| `sentry_ai.api.assemble` | Merge OV into wire detections |
| `sentry_ai.models.detection.overlay` | Dual colors |
| `sentry_ai.spatial.loop` | enabled + cutoffs |
| `sentry_ai.models.detection.loop` / `depth.loop` | enabled gates |
| `sentry_ai.models.cache` | YOLOE weight names |
| `sentry_ai.cli` | construct + start/stop OpenVocabLoop |
| `sentry_ai.ui.static.index.html` | Console UX |
| `THIRD_PARTY_MODELS.md` | YOLOE AGPL active |

## AGPL Documentation Checklist

1. Update `THIRD_PARTY_MODELS.md` YOLOE row: **Phase 6 active**, AGPL-3.0, non-default commercial caution, same cache path as YOLO26.  
2. List default weight `yoloe-26s-seg.pt` + offline-after-first-download.  
3. Live Preview note: first open-vocab Run may download weights (AGPL Ultralytics).  
4. Keep `tests/test_third_party_models_doc.py` assertions green (extend for YOLOE active).  
5. Do not claim Apache-2.0 for YOLOE weights.

## Sources

### Primary (HIGH confidence)

- Codebase: `cli.py`, `DetectionLoop`/`DepthLoop`/`FreeSpaceLoop`, `PerceptionStore`, `routes_*`, `index.html`, `yolo_worker.py`, `free_space.py`, `assemble.py`, `pyproject.toml`, `THIRD_PARTY_MODELS.md`  
- Ultralytics YOLOE docs: https://docs.ultralytics.com/models/yoloe/ (fetched 2026-08-08; `set_classes` + predict examples)  
- Installed package: ultralytics **8.4.116** / YOLOE class + `set_classes(classes, embeddings=None)`  
- Phase research: `.planning/research/SUMMARY.md`, `STACK.md`, `ARCHITECTURE.md` control path  
- Phase 5 SUMMARYs: store/assembler/MJPEG/serve lifecycle patterns  

### Secondary (MEDIUM confidence)

- STACK.md open-vocab dual-rate / on-demand guidance  
- PyPI ultralytics 8.4.116 version check  

### Tertiary (LOW confidence)

- Exact desktop FPS with fixed + OV continuous concurrent — measure, don't claim  
- slopcheck unavailable — no new packages anyway  

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — YOLOE verified in env + official docs; no new deps  
- Architecture: **HIGH** — maps cleanly onto Phase 2–5 loops/store; race analysis explicit  
- Pitfalls: **HIGH** — derived from existing loop/store contracts + OV dual-writer hazard  
- Weight default (26s vs 11s): **MEDIUM** — both valid; recommend 26s  

**Research date:** 2026-08-08  
**Valid until:** ~2026-09-08 (Ultralytics minor may move; re-check YOLOE weight names if >30 days)

## RESEARCH COMPLETE

**Phase:** 6 - Developer Controls & Open-Vocab  
**Confidence:** HIGH  

### Key Findings
1. **Pause = enable flags inside loops**, not thread stop/start; serve/capture stay up.  
2. **Unified `/api/pipeline/config`** for stage flags + free-space cutoffs; keep det/depth conf routes.  
3. **YOLOE via existing detect extra** (`YOLOE.set_classes` + `predict`); default `yoloe-26s-seg.pt`; mock in tests.  
4. **Separate OpenVocabLoop + OpenVocabProduct** to avoid detection writer races; merge in assemble with `source` tag.  
5. **Modes:** off default, on-demand Run, optional continuous every_n=3; fixed-class never blocked.  

### File Created
`.planning/phases/06-developer-controls-open-vocab/06-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | Ultralytics 8.4.116 + YOLOE API verified |
| Architecture | HIGH | Grounded in shipped loops/store/API |
| Pitfalls | HIGH | Dual-writer, teardown, GPU, AGPL explicit |

### Open Questions
Weight default (26s), clear-vs-freeze on disable, continuous every_n — recommendations provided above.

### Ready for Planning
Research complete. Planner can create `06-01-PLAN.md` (control plane + UI) and `06-02-PLAN.md` (YOLOE + stream/UI). Do not commit per orchestrator instruction.

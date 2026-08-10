# Phase 11: Sticky Fallback & Dual-Model Guardrails - Research

**Researched:** 2026-08-10  
**Domain:** Sticky ORT/TRT fallback policy (soft vs strict), thrash-free resolve, depth/open-vocab torch scope lock, dual-model operator honesty  
**Confidence:** HIGH (code-verified factory/cli/status/depth/OV paths + Phase 8–10 shipped contracts; soft-vs-strict product default is the only open product decision)

> **Note:** No `*-CONTEXT.md` for this phase (discuss-phase not run). Locked decisions below are taken from `.planning/STATE.md`, ROADMAP, REQUIREMENTS, and Phase 8–10 shipped patterns.

<user_constraints>
## User Constraints (from STATE / ROADMAP / prior phase locks)

### Locked Decisions
- v0.2 = live ORT + live TRT for **fixed-class YOLO only**; depth / open-vocab stay PyTorch [VERIFIED: STATE.md, REQUIREMENTS EDGE-RT-04]
- Plug-in at serve factory (`build_detection_worker`); DetectionLoop / FrameBus / PerceptionStore / `/v1` **frozen** [VERIFIED: EDGE-RT-01, factory sole consumer in cli]
- Soft torch fallback default (loud); sticky resolve; **strict mode available** [VERIFIED: STATE.md Accumulated Decisions]
- Factory remains sole author of `backend_live` (Phase 8) [VERIFIED: factory.py + routes_preview pass-through]
- Artifact resolution via existing `resolve_detector_artifact` + env `SENTRY_DETECTOR_ONNX` / `SENTRY_DETECTOR_ENGINE` (BACK-04) [VERIFIED: artifact_paths.py]
- Ultralytics-native fixed-class path only (`YOLO("*.onnx|engine")`); no custom ORT/TRT decode [VERIFIED: Phase 9/10]
- No `tensorrt` pip extra; on-device engines only [VERIFIED: pyproject + TRT-03]
- No FPS claims; dual-model **measure-on-device** only [VERIFIED: jetson-packaging.md, yolo26-onnx-tensorrt.md, STATE]
- No continuous open-vocab + TRT + DAV2 as a first-class claim [VERIFIED: ROADMAP SC4, PITFALLS.md]

### Claude's Discretion
- Soft vs strict **default for jetson profile** (STATE blocker: “decide in Phase 11 planning”)
- Exact config surface for strict mode: env (`SENTRY_FALLBACK_TO_TORCH`), profile YAML field (`device.fallback_to_torch`), CLI flag, or combination
- Whether strict fail-closed means **serve exit non-zero** vs **detection stage disabled / worker None** with process still up
- Whether to add `fallback_mode` (or equivalent) to status/banner/UI footer, or only document soft/strict in docs
- How deeply dual-model VRAM guidance is written (guidance + knobs vs any runtime OOM early-fail)
- Whether residual load-failure thrash (corrupt `.engine` after live claim) is hardened this phase or documented only
- Exact test module split (`test_fallback_policy.py` vs extend factory/status/docs tests)

### Deferred Ideas (OUT OF SCOPE)
- Live ORT/TRT for depth or YOLOE (later milestones)
- Pi dual-model published FPS as first-class claim
- Full edge-serve narrative polish + AGPL lineage refresh (Phase 12 EDGE-DOC-*)
- CI selection matrix hardening beyond Phase 11 unit tests (Phase 12 EDGE-CI-*)
- Sequential GPU time-slicing / concurrent dual-model scheduler rewrite
- Prebuilt multi-SKU engines; custom TRT Runtime decode
- Runtime reconfigure of backend without process restart (profile reload thrash)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BACK-03 | When preferred ORT/TRT artifact or dependency is missing, behavior is **documented and sticky** (fail-closed or explicit torch fallback with reason logged once — never thrash every frame) | Factory already resolves once at serve; Phase 11 must codify + document soft vs strict, ensure reason is logged once via structured path, add strict fail-closed option, prove no per-frame re-resolve |
| EDGE-RT-04 | Depth and open-vocab continue on existing PyTorch paths this milestone (no live ORT/TRT for them) | Depth/OV already torch-only by construction; Phase 11 locks via tests + docs honesty + dual-model guidance (no continuous OV+TRT+DAV2 claim) |
</phase_requirements>

## Summary

Phases 8–10 already delivered the hard parts of backend honesty: `build_detection_worker` is the sole author of `backend_requested` / `backend_live` / `backend_reason`; live ORT/TRT exist for fixed-class YOLO when artifact + dep resolve; soft torch fallback with stable reason codes is the only path when they do not. Serve calls the factory **once** and freezes the worker into `DetectionLoop` for process lifetime. Status, CLI banner, and Live Preview footer already surface requested → live (+ reason when they differ). Depth and open-vocab are constructed on separate torch/HF paths and never enter the detection factory.

What Phase 11 must still deliver is **policy completeness and proof**, not a second loader stack:

1. **Sticky contract made explicit** — document and test that resolve is one-shot; never re-probe preferred backend per frame.
2. **Soft vs strict modes** — today soft is hard-coded (always torch worker on miss). STATE requires strict mode available; research architecture already names `fallback_to_torch: true|false`.
3. **Reason logged once** — banner `typer.echo(..., err=True)` once at start is de facto “once,” but there is no structured `logger.warning/error` for factory soft-fall; docs should state the contract; add a single structured log at resolve time.
4. **Depth/OV torch scope lock** — enforce with static/docs/tests that no live ORT/TRT claim exists for those stages; dual-model guidance for TRT YOLO + torch depth only, OV off/on-demand.
5. **Operator surface** — requested/live/reason already work; optionally expose fallback mode; remove “Phase 11 deferred” language from dual-model docs.

**Primary recommendation:** Keep factory as sole resolve site; default **soft** (`fallback_to_torch=true`) for maker-friendly serve; add **strict** path that refuses detection (or exits) when preferred ORT/TRT cannot go live, with the same reason codes; log reason once at construct; document sticky policy; add EDGE-RT-04 + dual-model honesty tests/docs; do not touch DetectionLoop/bus/store/`/v1`.

### Top recommendations for planner

1. **11-01 — Sticky resolve + soft/strict fallback policy (BACK-03)**  
   - Codify sticky: factory called once from serve; no loop re-entry.  
   - Add `fallback_to_torch` (or `strict_backend`) config: env override + optional `DeviceConfig` field; default soft `true`.  
   - Soft: current behavior (torch worker + reason).  
   - Strict: do not construct torch shadow under preferred ORT/TRT; fail closed (prefer: detection disabled + non-zero exit **or** serve continues with detection off + loud error — pick one and document).  
   - Structured log once at resolve when requested ≠ live (or on strict fail).  
   - Docs: soft vs strict table; sticky guarantee; reason vocabulary.  
   - Tests: soft matrix unchanged; strict miss → no live claim + no silent torch; sticky (call factory once / assert no thrash hooks in loops).

2. **11-02 — Dual-model scope lock + operator status surface (EDGE-RT-04)**  
   - Tests: depth worker / serve construction never sets ORT/TRT for depth; OV uses `.pt` YOLOE path; factory not used for depth/OV.  
   - Docs: TRT YOLO + torch DAV2 measure-on-device; continuous OV + TRT + DAV2 **not** first-class; jetson OV default off.  
   - Operator surface: keep footer/status triple; add fallback mode if implemented; retire “Phase 11 deferred” dual-model language.  
   - No VRAM measurement in CI; no FPS tables.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Backend resolve (requested → live) | API / Backend (`build_detection_worker` at serve construct) | CLI serve | One-shot sticky; never per-frame |
| Soft vs strict policy | API / Backend (factory + config) | Profile YAML / env | Product policy; not loop logic |
| Reason emission (once) | API / Backend (factory or serve after factory) | CLI banner + logger | BACK-03 “logged once” |
| Status honesty pass-through | API / Backend (`/api/status`) | Live Preview footer | Factory-authored fields only |
| Fixed-class detect runtime | API / Backend (`DetectionLoop` + worker) | — | **Frozen** spine; worker already sticky-loaded |
| Depth inference | API / Backend (`DepthAnythingWorker` torch/HF) | — | EDGE-RT-04 torch-only |
| Open-vocab inference | API / Backend (`YoloeOpenVocabWorker` torch) | — | EDGE-RT-04 torch-only; default mode off |
| Dual-model VRAM guidance | Docs / operator runbooks | Optional status notes | Measure-on-device; no fake FPS |
| Artifact allowlist | API / Backend (`artifact_paths`) | Env | BACK-04 already shipped |
| FrameBus / store / `/v1` | API / Backend | — | **Frozen** |

## Current Codebase State (verified)

### 1. Fallback is already sticky at process level — HIGH

[VERIFIED: `src/sentry_ai/cli.py` L506–510, L645–646]

- `build = build_detection_worker(rt, conf=0.25)` runs **once** during serve startup.
- `worker` is injected into `DetectionLoop` and never rebuilt.
- Only call site of `build_detection_worker` outside tests is `cli.py` serve.

[VERIFIED: `src/sentry_ai/models/detection/yolo_worker.py` `_ensure_model`]

- Model load is once-per-worker (`self._model` cached under lock).
- No re-resolve of preferred backend inside `process`.

[VERIFIED: `src/sentry_ai/models/detection/loop.py` `_dep_failed`]

- Missing ultralytics → sticky pause, log once, stage off — pattern to mirror for policy messaging.

**Implication for planner:** Thrash is **not** currently happening via factory re-probe. BACK-03 work is: (a) make sticky contract documented + tested, (b) add strict mode, (c) ensure reason log is intentional/once, (d) note residual risk if live claim succeeds then YOLO load fails (non-ImportError exceptions retry every frame — see Pitfalls).

### 2. Soft is hard-coded; strict does not exist — HIGH

[VERIFIED: `factory.py` ORT/TRT branches always return `_torch_worker` on miss]

| Condition | Today | Reason codes |
|-----------|-------|--------------|
| ORT path_rejected | soft torch | `path_rejected` |
| ORT artifact missing | soft torch | `ort_artifact_missing` |
| ORT dep missing | soft torch | `ort_dep_missing` |
| TRT path_rejected | soft torch | `path_rejected` |
| TRT artifact missing | soft torch | `trt_artifact_missing` |
| TRT dep missing | soft torch | `trt_dep_missing` |
| Unknown backend | soft torch | `unsupported_backend` |
| Strict miss | **not implemented** | — |

[VERIFIED: `DeviceConfig` has only `preferred_backend` + `device_id` — no `fallback_to_torch`]

[VERIFIED: no `SENTRY_FALLBACK*` env in config load]

Architecture research already prescribed:

```text
if fallback_to_torch:
  live_backend = torch + reason
else:
  fail serve OR detection disabled  # strict
```

[CITED: `.planning/research/ARCHITECTURE.md` Fallback chain / Strict vs soft modes]

**Recommendation (discretion):**

| Mode | Default | Behavior when preferred ORT/TRT cannot go live |
|------|---------|--------------------------------------------------|
| **Soft** | **Yes** (all profiles) | Construct torch worker; `backend_live=torch`; set reason; log once; continue serve |
| **Strict** | Opt-in | Do **not** shadow with torch under preferred ORT/TRT; set reason; detection disabled (worker/loop None) **or** exit non-zero; still surface requested/live/reason on status if process stays up |

**Jetson default:** Keep soft default for maker “serve without engine still previews.” Document that production robots wanting fail-closed set strict. Do **not** flip jetson YAML to strict without user confirmation (STATE open question). [ASSUMED product default — soft remains global default]

### 3. Reason visibility today — HIGH

| Surface | Soft-fall reason shown? | Once? |
|---------|-------------------------|-------|
| CLI banner | Yes — `backend_reason: …` on stderr | Once per process start [VERIFIED: cli.py L616–617] |
| `/api/status` | Yes — `backend_reason` pass-through | Sticky field [VERIFIED: routes_preview.py L179–187] |
| Live Preview footer | Yes — `req → live (reason)` when differ | Polled display of sticky field [VERIFIED: index.html L449–458] |
| Structured logger | **No** factory log | Gap vs BACK-03 “logged once” wording |

**Recommendation:** Add single `logger.warning` (soft) or `logger.error` (strict) in factory or immediately after factory in serve when `backend_reason is not None`. Do not log inside DetectionLoop per frame.

### 4. Depth / open-vocab torch-only — HIGH (EDGE-RT-04 largely satisfied in code)

[VERIFIED: cli.py L513–562]

- OV: `YoloeOpenVocabWorker(weights=rt.open_vocab_weights, …)` — always profile `.pt` YOLOE path; default `OpenVocabLoop` mode **off**.
- Depth: `DepthAnythingWorker(... device=rt.device)` — transformers + torch; no factory, no preferred_backend branch.

[VERIFIED: no ORT/TRT symbols in depth worker load path; yoloe uses `YOLOE(self._weights)` with `.pt` defaults]

**Gap:** No automated test asserts “depth/OV never claim backend_live ORT/TRT” or “serve never routes depth through factory.” Docs still say “Phase 11 owns first-class dual-model guardrails” in places — update language.

### 5. Dual-model guidance partial — MEDIUM/HIGH

Already present:

- jetson-packaging “Dual-model honesty” + measure-on-device [VERIFIED]
- yolo26-onnx-tensorrt dual-model note + Phase 11 deferral language [VERIFIED]
- jetson profile: detector `n`, depth Small, OV mode off by default [VERIFIED]

Still needed for SC4:

- Explicit **supported claim**: TRT (or torch) fixed-class YOLO **+** torch DAV2 Small may share GPU — measure VRAM/latency on device; no published dual-model FPS.
- Explicit **non-claim**: continuous open-vocab + TRT YOLO + DAV2 is **not** a first-class supported configuration this milestone.
- Operator knobs listed: disable depth, OV off/on_demand only, nano tier, `--no-ui`, measure with `nvidia-smi` / on-device tools.
- Remove “Phase 11 deferred” once this phase ships.

### 6. Operator status surface — HIGH (mostly done)

| Field | Present | Gap |
|-------|---------|-----|
| `backend_requested` | Yes | — |
| `backend_live` | Yes | — |
| `backend_reason` | Yes | Soft-stub fixture still uses retired `ort_loader_not_implemented` in one test [VERIFIED: test_backend_honesty_status.py L112] — cleanup if touched |
| `fallback_mode` / `fallback_to_torch` | No | Add if strict mode ships |
| Depth/OV backend fields | No | Not required if docs + construction prove torch-only; avoid inventing fake backend_live for depth |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Existing factory / WorkerBuild | Phase 8–10 | Sticky resolve + reason codes | Sole author of live identity [VERIFIED: factory.py] |
| Existing CLI serve | — | One-shot construct + banner | Sticky by construction [VERIFIED: cli.py] |
| Existing status + UI footer | Phase 8 | Operator visibility | Pass-through honesty [VERIFIED] |
| Pydantic `DeviceConfig` / profiles | existing | Optional `fallback_to_torch` field | `extra=forbid` — new fields must be explicit [VERIFIED: models.py] |
| pytest ≥8 | dev extra | Unit proof without Jetson | Existing suite [VERIFIED: pyproject.toml] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `logging` (stdlib) | — | Once-per-process reason log | Soft warn / strict error |
| `os.environ` | — | Optional `SENTRY_FALLBACK_TO_TORCH` | Operator override without YAML edit |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Soft default + opt-in strict | Strict default on jetson | Breaks jetson serve without engine; worse maker UX; STATE left open |
| Serve exit non-zero on strict | Detection disabled, serve up | Exit is clearer for automation; disabled stage better for capture-only debugging — **prefer document both, implement one** |
| New status field `fallback_mode` | Docs-only soft/strict | Field improves robot debugging; small schema add on StatusSnapshot |
| Runtime dual-model OOM guard | Docs knobs only | Runtime guard needs GPU metrics + policy; out of scope for honest docs milestone |

**Installation:**

```bash
# No new packages for Phase 11 — policy/docs/tests only
uv sync --extra detect --extra depth --extra dev
# optional ORT path:
uv sync --extra detect --extra onnx --extra depth --extra dev
```

**Version verification:** No new registry packages. Existing pins unchanged. Package Legitimacy Audit: N/A install set.

## Package Legitimacy Audit

> Phase 11 is expected to install **no** new external packages.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| *(none)* | — | — | — | — | — | No new installs |

**Packages removed due to slopcheck [SLOP] verdict:** none  
**Packages flagged as suspicious [SUS]:** none  

*If a later plan invents a package, re-run the Package Legitimacy Gate before install.*

## Architecture Patterns

### System Architecture Diagram

```text
                    profile YAML / SENTRY_PROFILE / env artifacts
                                      │
                                      ▼
                         load_config → ProfileRuntime
                                      │
                    ┌─────────────────┼──────────────────┐
                    │                 │                  │
                    ▼                 ▼                  ▼
         build_detection_worker   DepthAnythingWorker  YoloeOpenVocabWorker
         (preferred_backend)      (torch/HF only)      (.pt YOLOE only)
                    │                 │                  │
         resolve once:                │                  │
         artifact + dep probe         │                  │
                    │                 │                  │
         ┌──────────┴──────────┐      │                  │
         │ soft: torch + reason│      │                  │
         │ strict: fail-closed │      │                  │
         │ live: ORT/TRT worker│      │                  │
         └──────────┬──────────┘      │                  │
                    │                 │                  │
                    ▼                 ▼                  ▼
              DetectionLoop      DepthLoop         OpenVocabLoop
              (sticky worker)    (sticky dep)      (mode off default)
                    │                 │                  │
                    └────────┬────────┴────────┬─────────┘
                             ▼                 ▼
                      PerceptionStore    /api/status + banner + UI footer
                      (backend_* sticky)  requested / live / reason
                             │
                             ▼
                           /v1  (frozen)
```

### Recommended Project Structure (touch set)

```text
src/sentry_ai/
├── models/detection/factory.py     # soft/strict policy + once log
├── config/models.py                # optional DeviceConfig.fallback_to_torch
├── config/load.py                  # optional env override
├── config/profile_runtime.py       # plumb fallback flag if on ProfileRuntime
├── cli.py                          # strict fail-closed wiring; banner mode
├── capture/status.py               # optional fallback_mode field
├── api/app.py / deps.py            # pass-through if new field
├── api/routes_preview.py           # pass-through if new field
└── ui/static/index.html            # optional mode in footer
docs/
├── configuration.md                # soft vs strict + sticky
├── architecture.md                 # fallback chain honesty
└── export/{yolo26-onnx-tensorrt,jetson-packaging}.md  # dual-model lock
tests/
├── test_detection_factory.py       # strict matrix + sticky contract
├── test_backend_honesty_status.py  # mode field if added
├── test_export_docs.py / new dual-model keyword tests
└── test_edge_rt04_torch_only.py    # recommended new module
```

### Pattern 1: Soft fallback (existing — keep)

**What:** Preferred ORT/TRT cannot go live → torch worker + reason.  
**When:** Default / maker-friendly.  
**Example:**

```python
# Source: src/sentry_ai/models/detection/factory.py (shipped)
if path is None:
    return WorkerBuild(
        worker=_torch_worker(rt, conf=conf, model=model),
        backend_requested="tensorrt",
        backend_live="torch",
        backend_reason="trt_artifact_missing",
    )
```

### Pattern 2: Strict fail-closed (new)

**What:** Same miss conditions → do not construct torch shadow under preferred ORT/TRT.  
**When:** `fallback_to_torch=false` (env/profile).  
**Recommended shape:**

```python
# Source: research recommendation (not yet in tree)
if not fallback_to_torch:
    # Option A (preferred for robots): raise / return sentinel;
    # serve catches → detection disabled + exit code or loud continue
    return WorkerBuild(
        worker=None,  # or raise BackendUnavailable(reason)
        backend_requested=requested,
        backend_live="unavailable",  # OR leave live unset / "none"
        backend_reason=reason,
    )
```

**Honesty rule:** Never set `backend_live` to `onnxruntime`/`tensorrt` on strict fail. Prefer `backend_live` ∈ {`torch` only on soft, `none`/`unavailable` on strict} — pick vocabulary and test it. [ASSUMED: use `backend_live="none"` + reason for strict; avoid inventing new live backend names that look successful]

**Safer alternative (lower risk to StatusSnapshot consumers):** On strict fail, keep process pattern of soft identity fields but set `worker=None` / skip DetectionLoop, with `backend_live="torch"` **forbidden** if no worker — better: `backend_live=None` and `backend_reason=…` so UI shows requested → — (reason). Align with existing optional None fields on StatusSnapshot.

### Pattern 3: Log once at construct (new, mirror device resolve / loop sticky)

```python
# Analog: DetectionLoop._handle_dependency_failure log-once
# Analog: resolve_device CUDA fallback warning (device path)
logger.warning(
    "detection backend soft-fallback: requested=%s live=%s reason=%s",
    build.backend_requested,
    build.backend_live,
    build.backend_reason,
)
```

Call **only** when reason is not None, from serve after factory (or factory once).

### Pattern 4: EDGE-RT-04 construction lock

```python
# Serve (already true) — keep separate constructors; never:
#   build_detection_worker → depth
#   preferred_backend → YOLOE
depth_worker = DepthAnythingWorker(...)          # torch/HF
ov_worker = YoloeOpenVocabWorker(weights=rt.open_vocab_weights, ...)  # .pt
```

### Anti-Patterns to Avoid

- **Per-frame factory re-resolve:** Would reintroduce thrash; never call `build_detection_worker` from DetectionLoop.
- **Silent strict→soft:** Strict mode that still loads torch without reason violates BACK-03.
- **Claiming continuous OV+TRT+DAV2:** Explicit non-goal; docs must not imply first-class support.
- **Publishing dual-model FPS:** Forbidden without measurement protocol (PITFALLS #10).
- **Touching DetectionLoop scheduling** for dual-model: out of scope; docs knobs only.
- **Auto-pip tensorrt / re-import probes in loop:** Keep `find_spec` only at factory time.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Backend selection | Custom InferenceBackend rewrite | Existing factory + Ultralytics-native workers | Spine freeze; Phase 9/10 already live |
| Thrash prevention | Retry/backoff state machine in loop | One-shot factory resolve + sticky worker | Already process-sticky; policy is enough |
| Dual-model scheduler | GPU time-slice framework | Docs knobs + OV default off | Unmeasured; later milestone |
| VRAM accounting | In-process CUDA mem governor | Operator `nvidia-smi` + measure-on-device | Device-specific; no CI Jetson |
| Strict mode | New microservice / health sidecar | Factory + serve construct branch | Same process honesty |

**Key insight:** Phase 11 is a **policy and honesty** phase on top of a working sticky factory — not a new inference stack.

## Runtime State Inventory

> Not a rename/refactor migration. Omitted categories answered for completeness.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | None — backend identity is process-local, not persisted | none |
| Live service config | None in external UIs — profiles in package YAML only | optional profile comment / field |
| OS-registered state | None | none |
| Secrets/env vars | `SENTRY_DETECTOR_ONNX`, `SENTRY_DETECTOR_ENGINE`, `SENTRY_ARTIFACT_ROOT`, `SENTRY_PROFILE` — no fallback env yet | add optional `SENTRY_FALLBACK_TO_TORCH` if chosen; document |
| Build artifacts | None for this phase | none |

## Common Pitfalls

### Pitfall 1: Assuming thrash still happens via factory
**What goes wrong:** Plans rebuild a complex sticky cache layer that already exists.  
**Why:** BACK-03 language sounds like per-frame thrash is present.  
**How to avoid:** Verify single call site; write a regression test that factory is not imported/called from loops.  
**Warning signs:** New “BackendResolver” class with TTL/retry.

### Pitfall 2: Soft vs strict default flip on jetson without UX decision
**What goes wrong:** Jetson serve without `.engine` exits; makers think product broke.  
**Why:** PITFALLS.md suggested strict as jetson candidate.  
**How to avoid:** Default soft globally; document strict opt-in; leave jetson YAML values unchanged unless user locks strict.  
**Warning signs:** CI jetson profile tests start expecting exit 1 without fixtures.

### Pitfall 3: Live claim then load thrash (residual)
**What goes wrong:** Artifact + dep present → `backend_live=tensorrt`, then `YOLO(engine)` fails every frame (wrong arch / corrupt) with `logger.exception` spam.  
**Why:** DetectionLoop sticky-pauses only dependency-class errors; `_ensure_model` leaves `_model is None` on failure.  
**How to avoid (Phase 11 optional hardening):** On first non-recoverable load error for fixed-class worker, sticky-pause stage + set store error once (mirror dep failure). Or document as known residual.  
**Warning signs:** Log spam “Detection worker failed” with TensorRT deserialize errors.

### Pitfall 4: Dual-model FPS / VRAM fiction
**What goes wrong:** Docs invent “Orin Nano dual-model 30 FPS.”  
**How to avoid:** Measure-on-device language only; keyword tests forbid guaranteed FPS tables.  
**Warning signs:** Numbers without methodology.

### Pitfall 5: Status recomputation from preferred_backend
**What goes wrong:** Route invents live backend from profile when factory not injected.  
**How to avoid:** Keep pass-through only (Phase 8 invariant).  
**Warning signs:** status handler imports factory or profile preferred_backend for live.

### Pitfall 6: Config injection of preferred_backend (security-adjacent)
**What goes wrong:** Untrusted profile/env sets `preferred_backend=tensorrt` expecting production path; soft mode silently runs torch — robots trust wrong latency/backend.  
**How to avoid:** Honesty fields + optional strict mode; document that status must be monitored; keep artifact path allowlist (BACK-04).  
**Warning signs:** Deploy scripts ignore `backend_live` / `backend_reason`.

### Pitfall 7: Breaking StatusSnapshot extra=forbid
**What goes wrong:** Add field only in HTML, not Pydantic model.  
**How to avoid:** If new status field, update `StatusSnapshot`, app.state, deps, route, tests together.

## Code Examples

### Sticky serve wiring (existing)

```python
# Source: src/sentry_ai/cli.py (serve detection block)
build = build_detection_worker(rt, conf=0.25)
worker = build.worker
backend_requested = build.backend_requested
backend_live = build.backend_live
backend_reason = build.backend_reason
det_loop = DetectionLoop(bus, worker, store)
# ... later, once:
if det_loop is not None:
    det_loop.start()
```

### Soft-fallback reason matrix (existing)

```python
# Source: factory.py — do not rename codes without test updates
# ORT: path_rejected | ort_artifact_missing | ort_dep_missing
# TRT: path_rejected | trt_artifact_missing | trt_dep_missing
# other: unsupported_backend
```

### Live Preview honesty (existing)

```javascript
// Source: src/sentry_ai/ui/static/index.html
var pair = (req || "—") + " → " + (live || "—");
if (reason && req && live && req !== live) {
  elBackend.textContent = pair + " (" + reason + ")";
}
```

### Recommended strict env parse

```python
# Source: research recommendation — mirror SENTRY_ALLOW_CLOUD bool parse in load.py
# SENTRY_FALLBACK_TO_TORCH=true|false  (default true)
```

## State of the Art (project-local)

| Old Approach (v1 / early v0.2) | Current Approach (post Phase 10) | When Changed | Impact |
|--------------------------------|-----------------------------------|--------------|--------|
| preferred_backend = export hint only | preferred selects real loader + soft fall | Phases 8–10 | Live ORT/TRT fixed-class |
| Soft-stub reasons `*_loader_not_implemented` | `*_artifact_missing` / `*_dep_missing` / `path_rejected` | 9–10 | Honest miss vocabulary |
| No status backend fields | requested / live / reason + UI footer | Phase 8 | Operator visibility |
| Sticky/strict undocumented | **Phase 11** | now | BACK-03 complete |
| Dual-model “Phase 11 deferred” | **Phase 11** docs lock | now | EDGE-RT-04 + SC4 |

**Deprecated/outdated:**
- Docs saying sticky policy is “deferred to Phase 11” after this phase ships — must update.
- Test fixture reason `ort_loader_not_implemented` in honesty tests — retire if touched.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Soft remains **global default** (including jetson); strict is opt-in | Soft vs strict | If user wanted jetson strict-by-default, production miss becomes silent torch unless they opt in — mitigated by loud reason + docs |
| A2 | Strict fail-closed prefers detection disabled + process may continue (vs hard exit) | Pattern 2 | Automation expecting non-zero exit needs explicit CLI contract |
| A3 | No new pip packages required | Standard Stack | If planner adds deps, legitimacy gate required |
| A4 | Residual live-load thrash (corrupt engine) is optional hardening, not must-have for BACK-03 | Pitfall 3 | Operators with bad engines still see per-frame exception logs |
| A5 | `backend_live` vocabulary on strict fail uses None/`none` not fake torch | Pattern 2 | Status consumers may need one migration note |

**If A1 is critical:** Confirm with user before locking jetson profile default.

## Open Questions

1. **Strict default on jetson?**  
   - What we know: STATE lists as Phase 11 planning decision; soft is shipped everywhere.  
   - What's unclear: production robot preference.  
   - Recommendation: soft default + document strict opt-in; do not change jetson YAML values without confirm.

2. **Strict semantics: exit vs detection-off?**  
   - What we know: ARCHITECTURE allows either.  
   - Recommendation: detection-off + exit code 1 **optional** via flag is complex — pick **one**: serve continues with detection disabled + error banner (better capture debug) **or** `typer.Exit(1)` after printing reason (better CI/robot). Prefer **Exit(1)** for strict clarity in automation.

3. **Expose `fallback_mode` on status?**  
   - Recommendation: yes if strict ships (small, high debug value).

4. **Harden live-load sticky pause?**  
   - Recommendation: if cheap, sticky-pause on first YOLO load failure for fixed-class; else document residual.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | tests / runtime | ✓ | 3.14.6 host / project ≥3.11 | — |
| uv | sync / pytest | ✓ | 0.11.23 | pip |
| pytest | unit suite | ✓ | 9.1.1 (env) / pin ≥8 | — |
| onnxruntime | live ORT (optional) | optional | via `onnx` extra | soft torch |
| system tensorrt | live TRT | device-specific | JetPack/system | soft torch |
| Jetson hardware | dual-model measure | ✗ (this host) | — | docs-only measure-on-device; no CI requirement |
| CUDA / nvidia-smi | dual-model guidance | host-dependent | — | docs knobs only |

**Missing dependencies with no fallback:** none for Phase 11 code/docs/tests.

**Missing dependencies with fallback:** Jetson/GPU for dual-model measurement → documentation only.

Step 2.6: external tools only for optional live paths already handled by soft fallback; Phase 11 itself is code/config/docs.

## Validation Architecture

> `workflow.nyquist_validation` is **true** in `.planning/config.json` — section required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest ≥8 (`dev` extra); env observed pytest 9.1.1 |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]` `testpaths = ["tests"]` |
| Quick run command | `uv run pytest tests/test_detection_factory.py tests/test_backend_honesty_status.py -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BACK-03 | Soft miss → torch + sticky reason codes | unit | `uv run pytest tests/test_detection_factory.py -q -k soft_fallback` | ✅ (partial — soft matrix exists) |
| BACK-03 | Resolve not invoked from DetectionLoop / per frame | unit / static | `uv run pytest tests/test_detection_factory.py -q` + source inspect or import graph assert | ❌ Wave 0 — add sticky contract test |
| BACK-03 | Strict miss → no silent torch live claim; fail-closed | unit | `uv run pytest tests/test_detection_factory.py -q -k strict` | ❌ Wave 0 |
| BACK-03 | Reason logged once (caplog) | unit | `uv run pytest tests/test_detection_factory.py -q -k log_once` | ❌ Wave 0 |
| BACK-03 | Soft vs strict documented | keyword docs | `uv run pytest tests/test_export_docs.py tests/test_desktop_docs.py -q` (extend) | ❌ Wave 0 keywords |
| EDGE-RT-04 | Depth construction torch/HF only | unit | `uv run pytest tests/test_edge_rt04_torch_only.py -q` | ❌ Wave 0 |
| EDGE-RT-04 | OV uses YOLOE `.pt` path; mode default off | unit | same / existing open_vocab tests extended | ⚠️ partial (`test_yoloe_worker`, `test_open_vocab_loop`) |
| EDGE-RT-04 | Dual-model docs: measure-on-device; no continuous OV+TRT+DAV2 claim; no FPS fiction | keyword | `uv run pytest tests/test_export_docs.py -q -k dual` | ❌ Wave 0 keywords |
| BACK-03/EDGE | Status still pass-through requested/live/reason (+ mode if added) | unit | `uv run pytest tests/test_backend_honesty_status.py -q` | ✅ (extend if new field) |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_detection_factory.py tests/test_backend_honesty_status.py -q`
- **Per wave merge:** `uv run pytest tests/test_detection_factory.py tests/test_backend_honesty_status.py tests/test_export_docs.py tests/test_cli_serve.py -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_detection_factory.py` — strict mode matrix + log-once (caplog) + sticky single-resolve contract
- [ ] `tests/test_edge_rt04_torch_only.py` (recommended) — depth/OV never use factory ORT/TRT; serve source inspect optional
- [ ] `tests/test_export_docs.py` — soft vs strict keywords; dual-model non-claims; sticky language
- [ ] `tests/test_backend_honesty_status.py` — retire `ort_loader_not_implemented` fixture if present; add fallback_mode if shipped
- [ ] Framework install: already present via `uv sync --extra dev`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Localhost default bind; no new auth this phase |
| V3 Session Management | no | — |
| V4 Access Control | partial | Unauthenticated LAN bind risk unchanged; document only |
| V5 Input Validation | yes | Artifact allowlist (BACK-04); Pydantic `extra=forbid` on config; bool env parse for fallback flag |
| V6 Cryptography | no | — |

### Known Threat Patterns for edge backend policy

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via engine/onnx path | Tampering | Existing allowlist `resolve_detector_artifact` (BACK-04) |
| Config injection of `preferred_backend` / fallback mode | Spoofing / Elevation of privilege (ops) | Status honesty fields; strict mode for fail-closed deploys; do not trust banner prose alone |
| Malicious/corrupt `.engine` DoS (load thrash) | Denial of Service | Sticky stage pause on load failure (optional); allowlisted stems only; no auto-download |
| Silent torch under tensorrt label | Spoofing | Factory sole author of `backend_live`; never recompute in routes |
| Resource exhaustion dual-model OOM | Denial of Service | Docs knobs; OV default off; nano tier on jetson; no continuous OV+TRT+DAV2 claim |

## Sources

### Primary (HIGH confidence)

- `src/sentry_ai/models/detection/factory.py` — live ORT/TRT + soft reasons; single resolve function
- `src/sentry_ai/cli.py` — one-shot factory + banner + depth/OV construction
- `src/sentry_ai/api/routes_preview.py` — status pass-through
- `src/sentry_ai/ui/static/index.html` — footer requested → live (reason)
- `src/sentry_ai/models/detection/loop.py` — sticky dep failure pattern
- `src/sentry_ai/models/depth/worker.py` / `yoloe_worker.py` — torch-only paths
- `src/sentry_ai/config/models.py` / profiles — no fallback field yet
- `.planning/REQUIREMENTS.md` — BACK-03, EDGE-RT-04
- `.planning/ROADMAP.md` — Phase 11 success criteria
- `.planning/STATE.md` — soft default; sticky; strict available; jetson default open
- Phase 8–10 RESEARCH/VERIFICATION — prior locks and deferrals

### Secondary (MEDIUM confidence)

- `.planning/research/ARCHITECTURE.md` — soft vs strict table, fallback chain
- `.planning/research/PITFALLS.md` — thrash, dual-model VRAM, silent lies
- `docs/export/jetson-packaging.md`, `yolo26-onnx-tensorrt.md` — dual-model honesty partial

### Tertiary (LOW confidence)

- Exact strict exit-code UX preference (product) — needs lock at plan time if not using A2 default
- Per-SKU VRAM budgets — intentionally unmeasured here

## Project Constraints (from CLAUDE.md)

- Workspace has no project-root `CLAUDE.md` / `AGENTS.md`.
- User-global `~/.claude/Claude.md` only notes graphify skill trigger — no coding constraints that alter Phase 11 stack.
- No project `.claude/skills` or `.agents/skills` discovered for this repo.

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — no new libs; existing factory/status stack verified in tree
- Architecture: **HIGH** — sticky resolve verified; soft/strict design from project research + code gaps clear
- Pitfalls: **HIGH** — thrash/dual-model/silent-lie pitfalls already project-documented and re-checked against code
- Soft vs strict product default: **MEDIUM** — recommendation soft-default; jetson strict still open (A1)

**Research date:** 2026-08-10  
**Valid until:** ~2026-09-09 (30 days; policy phase stable unless factory contracts change)

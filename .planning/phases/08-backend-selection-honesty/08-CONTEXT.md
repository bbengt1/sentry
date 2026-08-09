# Phase 8: Backend Selection & Honesty - Context

**Gathered:** 2026-08-09  
**Status:** Ready for planning  
**Source:** ROADMAP + REQUIREMENTS + v0.2 research (YOLO plan-phase)

<domain>
## Phase Boundary

Operators and robots see **honest backend identity**. `sentry serve` constructs the fixed-class detector via a **factory** driven by `preferred_backend`, with **safe artifact path resolution**. Torch path remains fully live end-to-end. ORT/TRT **loader branches are wired** (may stub until phases 9–10) but **must not claim live ORT/TRT when torch is running**.

**In scope:**
- Detection worker factory from `profile_runtime` (BACK-01, EDGE-RT-02)
- Loader branch selection: torch | onnxruntime | tensorrt (BACK-01)
- `backend_requested` + `backend_live` on status/banner (BACK-02)
- Artifact path resolution for `.onnx` / `.engine` with allowlist (BACK-04)
- Spine unchanged: DetectionLoop / FrameBus / store / `/v1` (EDGE-RT-01)
- Desktop-gpu torch default; jetson/cpu-fallback can select ORT/TRT honestly (EDGE-RT-03)
- Live Preview status can surface backend identity (roadmap UI hint)

**Out of scope (later phases):**
- Actual live ORT inference (Phase 9)
- Actual live TRT inference (Phase 10)
- Sticky fallback policy details beyond honest live identity (Phase 11) — minimal stub ok
- Depth/OV backend changes (EDGE-RT-04)
- Full InferenceBackend rewrite of YOLO internals

</domain>

<decisions>
## Implementation Decisions

### Locked
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

</decisions>

<canonical_refs>
## Canonical References

- `.planning/PROJECT.md` — v0.2 Edge Runtime
- `.planning/REQUIREMENTS.md` — BACK-01, BACK-02, BACK-04, EDGE-RT-01..03
- `.planning/ROADMAP.md` — Phase 8
- `.planning/research/SUMMARY.md`, `ARCHITECTURE.md`, `PITFALLS.md`, `STACK.md`
- `src/sentry_ai/cli.py` — serve construction
- `src/sentry_ai/config/profile_runtime.py`
- `src/sentry_ai/models/detection/yolo_worker.py`
- `src/sentry_ai/models/detection/loop.py`
- `src/sentry_ai/api/routes_preview.py` — `/api/status`
- `src/sentry_ai/capture/status.py`
- `src/sentry_ai/backend/protocols.py`

</canonical_refs>

<specifics>
## Plans (roadmap)

1. **08-01** — Factory + artifact resolution + profile wiring  
2. **08-02** — Status/banner honesty (`backend_requested` / `backend_live`)

Success: torch serve still works; factory used; status shows requested vs live; path resolver rejects traversal; ORT/TRT selection visible without false live claims.

</specifics>

<deferred>
## Deferred

- Live ORT/TRT inference
- Sticky thrash-free fallback modes
- Jetson JetPack matrix depth
- Dual-model VRAM budgets

</deferred>

---

*Phase: 08-backend-selection-honesty*  
*Context gathered: 2026-08-09 via YOLO plan-phase*

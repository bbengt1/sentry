# Phase 1: Foundations & Contracts - Context

**Gathered:** 2026-08-07  
**Status:** Ready for planning  
**Source:** Project initialization decisions + ROADMAP Phase 1 (no separate discuss-phase)

<domain>
## Phase Boundary

Establish the installable product skeleton and non-negotiable contracts so every later phase shares types, plugins, licenses, and multi-target hooks.

**In scope:**
- Installable Python package layout and tooling
- One-command local start skeleton (health/smoke against synthetic frames)
- Shared schemas: `Frame`, `PerceptionFrame` with `frame_id`, `camera_id`, timestamps
- Depth typing enum: `relative` | `metric_estimated` | `metric_calibrated`
- Plugin registry stubs: camera sources, model workers, sinks
- Config system with runtime profiles: `desktop-gpu`, `jetson`, `cpu-fallback`
- Device/backend abstraction protocols (stubs OK)
- Model license policy + `THIRD_PARTY_MODELS.md` (commercially friendly defaults)
- Local OSS model path policy (MODEL-01)

**Out of scope for this phase:**
- Real camera capture (Phase 2)
- Model inference (Phases 3–4)
- Web UI beyond nothing or minimal smoke (Phase 2+)
- Free-space, open-vocab, edge packaging (later phases)

</domain>

<decisions>
## Implementation Decisions

### Product identity
- Package/product name: **Sentry AI** / repo `sentry`
- Camera-only perception product for maker robotics
- Perception stream only — never motor commands

### Depth honesty (locked early)
- Depth outputs MUST carry `depth_kind`: `relative` | `metric_estimated` | `metric_calibrated`
- Relative depth must never be labeled or field-named as meters (`depth_m` forbidden for relative)

### Multi-target from day one
- Config supports profiles: `desktop-gpu`, `jetson`, `cpu-fallback`
- Backend/device abstraction protocols exist even if only desktop is implemented in v1 early phases

### Extensibility
- Plugin registry stubs for sources, model workers, sinks
- `camera_id` in schemas from day one (single camera v1; multi-cam later)

### Models & licenses
- Local open-source models only for core path (no mandatory cloud)
- Default weights commercially friendly (e.g. Depth Anything V2 **Small** Apache-2.0)
- Document Ultralytics AGPL and any NC weights as non-default / research-only in `THIRD_PARTY_MODELS.md`

### Stack direction (from research — Phase 1 should not fight this)
- Python 3.11+, FastAPI later; Phase 1 can scaffold without full inference
- Prefer `uv` + `pyproject.toml` packaging
- Pydantic v2 for schemas
- Single-process architecture direction (Frame Bus later)

### Claude's Discretion
- Exact package directory layout (`src/sentry_ai/` vs `sentry/`)
- Test runner (pytest) and CI provider details
- Whether smoke CLI is `sentry` entry point vs `python -m sentry_ai`
- Minimal README structure for one-command start
- Whether config is YAML, TOML, or Pydantic settings / env

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project definition
- `.planning/PROJECT.md` — core value, constraints, key decisions
- `.planning/REQUIREMENTS.md` — FOUND-01..06, MODEL-01
- `.planning/ROADMAP.md` — Phase 1 goal, success criteria, plan split

### Research
- `.planning/research/SUMMARY.md` — stack, architecture spine, Phase 1 implications
- `.planning/research/STACK.md` — recommended versions and anti-choices
- `.planning/research/ARCHITECTURE.md` — component boundaries, schema direction
- `.planning/research/PITFALLS.md` — depth typing, licenses, desktop-only trap

</canonical_refs>

<specifics>
## Specific Ideas

- Success: developer installs package and runs health/smoke against synthetic frames
- Plans expected (roadmap): 01-01 scaffold, 01-02 schemas+config, 01-03 plugins+licenses
- Frame bus and models are NOT this phase — only contracts that enable them

</specifics>

<deferred>
## Deferred Ideas

- Camera ingest, frame bus, live preview → Phase 2
- Detection / depth workers → Phases 3–4
- Free-space + `/v1` stream → Phase 5
- Interactive UI + open-vocab → Phase 6
- Edge TensorRT packs, ROS2/voice implementations → Phase 7 (stubs only in Phase 1)

</deferred>

---

*Phase: 01-foundations-contracts*  
*Context gathered: 2026-08-07 via project init decisions*

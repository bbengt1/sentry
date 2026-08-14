# Retrospective

Living document of milestone lessons for Sentry AI.

## Milestone: v1.0 — Camera-only perception MVP

**Shipped:** 2026-08-09  
**Phases:** 7 | **Plans:** 18 | **Tasks:** ~52  
**Timeline:** 2026-08-07 → 2026-08-09 (~3 days wall-clock)  
**Scale:** ~7.4k LOC Python under `src/`; 134 commits through archive prep

### What Was Built

Installable camera-only perception stack: capture → bus → YOLO + depth + free-space + open-vocab → single PerceptionStore → Live Preview + `/v1` stream, with runtime profiles, headless serve, export recipes, and extension stubs.

### What Worked

- **Vertical slices per phase** — each phase was runnable; makers never waited for “the end”
- **Honest contracts early** — `depth_kind`, perception-only API denylist, localhost default prevented FSD/overclaim debt
- **Single PerceptionStore truth** — UI overlays and robot API stayed aligned (UI-06)
- **Optional ML extras** — core package + CI stayed mockable without weight downloads
- **Profile YAML → serve wiring in Phase 7** — multi-target claim became real without inventing a full TRT runtime
- **GSD plan → execute → verify** cadence with atomic plan commits

### What Was Inefficient

- **`human_needed` UAT left open** on phases 2–4 — blocked milestone close psychologically even though automated scores were full; should mark residual UAT as acknowledged tech debt earlier
- **Nyquist VALIDATION.md** mostly stayed `nyquist_compliant: false` while tests were strong — doc hygiene lag
- **Device policy vs availability** — desktop-gpu/`cuda:0` broke Mac without CUDA until a post-phase fix; profile device should always pass through availability checks
- **README dual-edit risk** in Phase 7 wave 2 (export vs safety) — sequential execution avoided merge pain

### Patterns Established

- Keep-latest FrameBus; workers never open cameras
- Loop enable flags (pause compute, don’t tear down threads)
- Assembler-only merge for `/v1` and `/api/snapshot`
- Injectable model workers for CI
- Docs + keyword tests for honesty matrices (export, safety, desktop-gpu)
- Stubs importable + NotImplemented rather than empty READMEs only

### Key Lessons

1. Ship honesty constraints (depth typing, no motor fields) in Phase 1 — cheaper than retrofit  
2. “Profiles exist” ≠ “profiles select” — force executable wiring before claiming multi-target  
3. Residual operator UAT should not be a hard gate when automated verification is complete  
4. Edge export recipes are enough for v1; live TRT is a different milestone  

### Cost Observations

- Heavy use of parallel research/plan/execute agents per phase  
- Milestone closed after formal audit (`tech_debt`) rather than clean `passed` — appropriate given residual UAT  

### Known Deferred at Close

See STATE.md Deferred Items and `milestones/v1.0-MILESTONE-AUDIT.md` tech_debt.

## Milestone: v0.2 — Edge Runtime

**Shipped:** 2026-08-10  
**Phases:** 5 | **Plans:** 10 | **Tasks:** 26  
**Timeline:** 2026-08-09 → 2026-08-10  
**Scale:** ~9.3k LOC Python under `src/`; audit **passed** 20/20

### What Was Built

Live fixed-class YOLO on ORT and TensorRT via a factory-driven backend selection path; honest requested vs live status; sticky soft/strict fallback; depth/OV remain PyTorch; edge-serve docs hub; Jetson-free CI locks.

### What Worked

- **ORT isomorphism for TRT** — copy live factory branch + mock parity tests avoided custom TRT decoders
- **Honesty as a first-class product surface** — banner + `/api/status` + UI footer prevented silent backend lies
- **Soft default + opt-in strict** — makers keep working when engines missing; deployers can fail closed
- **Keyword/static tests for docs and CI policy** — split-brain docs and GPU CI creep became merge-blocking
- **Process-level sticky resolve** — single factory call at serve; DetectionLoop never re-probes

### What Was Inefficient

- **Nyquist VALIDATION.md** still `nyquist_compliant: false` after green suites — bookkeeping lag again (same as v1.0)
- **One-liner extraction noise** in SUMMARY frontmatter (e.g. plan-check self notes) polluted MILESTONES draft — clean before archive
- **Continuity camera work** landed on main between edge phases — high value but out of v0.2 scope (good ship, dilutes milestone narrative)

### Patterns Established

- Ultralytics-native `YOLO("*.onnx"|*.engine)` for live edge paths  
- Soft reason codes: `*_artifact_missing` / `*_dep_missing` / `path_rejected`  
- System TensorRT only — never pip `tensorrt` extra  
- Operator hub `docs/edge-serve.md` as export→serve single entry  
- Static GHA contract tests (`test_edge_ci_workflow.py`)

### Key Lessons

1. "Export recipes" ≠ "live runtime" — force factory `backend_live` claims before marketing edge  
2. Soft-by-default fallback is maker-friendly; document strict for edge deploys  
3. Mirror-proven paths (ORT→TRT) beat greenfield decoders  
4. Docs honesty needs the same keyword tests as code  

### Cost Observations

- Parallel plan-phase + execute-phase agents; high documentation volume in Phase 12  
- Milestone closed on formal audit **passed** (cleaner than v1.0 tech_debt close)

### Known Deferred at Close

See `milestones/v0.2-MILESTONE-AUDIT.md` tech_debt (Nyquist frontmatter, residual load honesty, hardware E2E checklist).

## Milestone: v0.3 — Metric Depth Calibration UX

**Shipped:** 2026-08-14  
**Phases:** 6 | **Plans:** 12 | **Tasks:** 17  
**Timeline:** 2026-08-11 → 2026-08-14  
**Scale:** package remains 0.1.0; audit **passed** 19/19

### What Was Built

Honest monocular metric scale via Live Preview wizard, DepthLoop `apply_map`, free-space meters iff calibrated, and per-camera YAML persist with fingerprint refuse. Relative depth never claims meters. No vehicle-grade / FSD claims. Synthetic CI only.

### What Worked

- **Honesty first** — Phase 13 contracts + CalibrationState before any product mutation
- **Math before chrome** — pure NumPy fit + DepthLoop apply before wizard labels
- **Single apply site** — `apply_map` only after `DepthAnythingWorker.process` and before `set_depth`
- **Cancel vs Clear** — draft-only cancel; Clear drops applied and deletes YAML
- **Keyword + inventory tests** — operator hub and Phase 13–17 suites cannot silently drift
- **Zero new deps** — NumPy + existing stack; DetectionLoop / FrameBus / ORT-TRT frozen

### What Was Inefficient

- **Nyquist VALIDATION.md** still `wave_0_complete: false` after green suites — bookkeeping lag again (v1.0 / v0.2 / v0.3)
- **Formal VERIFICATION only for Phase 13** — 14–18 closed on SUMMARY; fine for product close, weaker paper trail
- **REQUIREMENTS checkboxes left open until complete-milestone** — correct process, but live file lagged shipped work
- **MCP placeholder restores** on `cli.py` / `free_space.py` during execute — extra restore commits

### Patterns Established

- DepthLoop sole `apply_map` site (no re-scale in free-space / UI / persist I/O)
- Cancel = `clear_draft`; Clear = `clear_applied` + unlink YAML
- STACK path `$SENTRY_MODEL_CACHE/calibration/{safe_id}.yaml` (not `~/.config` JSON)
- Free-space `units="m"` iff `metric_calibrated` + absolute 1.5/3.0 m cuts
- Living `V03_INVENTORY` so deleting a Phase 13–17 suite fails CI
- Operator hub `docs/calibration.md` as wizard → persist single entry

### Key Lessons

1. Honesty contracts before meters — cheaper than retrofitting unit labels  
2. One apply site prevents double-scale and split-brain UI/API  
3. Persist late, only after the in-memory apply path is proven  
4. Docs keyword tests catch “always ordinal” drift the same way code tests catch unit lies  

### Cost Observations

- Parallel research/plan/execute agents per phase; Phase 18 docs-only + inventory (no product code)
- Milestone closed on formal audit **passed** 19/19; no next product phase

### Known Deferred at Close

See `milestones/v0.3-MILESTONE-AUDIT.md` tech_debt (Nyquist still false, SUMMARY-only 14–18, no package bump / Release).

## Cross-Milestone Trends

| Trend | v1.0 | v0.2 | v0.3 |
|-------|------|------|------|
| Honesty constraints | depth_kind, perception-only API | backend_live vs requested | metric_calibrated + m iff applied |
| Edge path | export recipes only | live ORT + live TRT | unchanged (depth still torch) |
| CI | mock ML, no weights | + Jetson-free GHA static locks | + honesty-matrix inventory |
| Nyquist bookkeeping lag | yes | yes (still) | yes (still false) |
| Close quality | tech_debt (UAT residual) | passed (20/20) | passed (19/19) |


---
*Started 2026-08-09 with v1.0 close*

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

## Cross-Milestone Trends

*(Populate after v1.1+)*

---
*Started 2026-08-09 with v1.0 close*

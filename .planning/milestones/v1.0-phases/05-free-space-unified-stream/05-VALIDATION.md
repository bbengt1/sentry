---
phase: 5
slug: free-space-unified-stream
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-08
---

# Phase 5 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest ≥8 |
| Quick | `uv run pytest tests/test_free_space*.py tests/test_v1_api*.py -q` |
| Full | `uv run pytest -q` |
| Depth models | Not required — synthetic depth maps |

## Wave 0

- [ ] `tests/test_free_space_bands.py` — near-field algorithm pure
- [ ] `tests/test_free_space_loop.py` — FreeSpaceLoop on synthetic DepthProduct
- [ ] `tests/test_free_space_overlay.py` — draw free-space mask
- [ ] `tests/test_assemble_perception_frame.py` — merge + completeness + stale
- [ ] `tests/test_v1_snapshot.py` / stream
- [ ] `tests/test_api_perception_only.py` — API-05 denylist
- [ ] Schema tests FreeSpacePayload expansion

## Threats

| ID | Pattern | Mitigation |
|----|---------|------------|
| T-5-01 | Fake metric free-space from relative depth | units/depth_kind on payload; image-space default |
| T-5-02 | Safe-to-proceed language | Copy review; no go-nogo fields |
| T-5-03 | Dual truth UI≠API | assemble once; same store |
| T-5-04 | Stale “all clear” after stall | TTL + age_ms + completeness |
| T-5-05 | Motor commands on stream | schema extra=forbid; denylist tests |

**Approval:** pending

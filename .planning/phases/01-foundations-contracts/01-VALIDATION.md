---
phase: 1
slug: foundations-contracts
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-07
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (≥8; env may have 9.x) |
| **Config file** | `pyproject.toml` → `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest -q tests/test_schemas_depth_kind.py tests/test_schemas_frame.py` |
| **Full suite command** | `uv run pytest -q` |
| **Smoke** | `uv run sentry smoke` |
| **Lint** | `uv run ruff check src tests` |
| **Estimated runtime** | ~10–30 seconds (no ML) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q`
- **After every plan wave:** Run full suite + `uv run sentry smoke` + `ruff check`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-* | 01 | 1 | FOUND-01 | T-1-02 | Distinct package name `sentry-ai` | smoke/unit | `uv run sentry health` / import | ❌ W0 | ⬜ pending |
| 01-02-* | 02 | 2 | FOUND-02 | T-1-01 | Pydantic validation; extra=forbid | unit | `pytest tests/test_schemas_frame.py -q` | ❌ W0 | ⬜ pending |
| 01-02-* | 02 | 2 | FOUND-03 | T-1-01 | relative forbids meters | unit | `pytest tests/test_schemas_depth_kind.py -q` | ❌ W0 | ⬜ pending |
| 01-02-* | 02 | 2 | FOUND-06 | T-1-04 | Profiles validated; allow_cloud false | unit | `pytest tests/test_config_profiles.py -q` | ❌ W0 | ⬜ pending |
| 01-02-* | 02 | 2 | MODEL-01 | T-1-04 | Local-only default | unit | same | ❌ W0 | ⬜ pending |
| 01-03-* | 03 | 3 | FOUND-04 | — | Registry lists stubs | unit | `pytest tests/test_plugins_registry.py -q` | ❌ W0 | ⬜ pending |
| 01-03-* | 03 | 3 | FOUND-05 | T-1-03 | License doc present | unit | `pytest tests/test_third_party_models_doc.py -q` | ❌ W0 | ⬜ pending |
| 01-03-* | 03 | 3 | FOUND-06 | — | Backend protocol stubs | unit | `pytest tests/test_backend_protocols.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures (synthetic Frame factory)
- [ ] `tests/test_schemas_frame.py` — FOUND-02
- [ ] `tests/test_schemas_depth_kind.py` — FOUND-03
- [ ] `tests/test_schemas_perception.py` — FOUND-02/03
- [ ] `tests/test_config_profiles.py` — FOUND-06, MODEL-01
- [ ] `tests/test_plugins_registry.py` — FOUND-04
- [ ] `tests/test_backend_protocols.py` — FOUND-06
- [ ] `tests/test_cli_smoke.py` — FOUND-01
- [ ] `tests/test_third_party_models_doc.py` — FOUND-05
- [ ] `pyproject.toml` package scaffold — FOUND-01
- [ ] Optional: `.github/workflows/ci.yml` — ruff + pytest on 3.11

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| README one-command start is clear | FOUND-01 | Doc quality | Open README; follow install + `uv run sentry smoke` |
| Package name disambiguation from getsentry | FOUND-01 | Naming | Confirm dist name is `sentry-ai`, not `sentry` |

---

## Threat Model References (for plans)

| ID | Pattern | Mitigation |
|----|---------|------------|
| T-1-01 | Malicious / invalid YAML config | `yaml.safe_load` + Pydantic validation |
| T-1-02 | Dependency confusion with PyPI `sentry` | Dist name `sentry-ai`; README note |
| T-1-03 | Model license / NC weights as default | THIRD_PARTY_MODELS.md; Apache defaults |
| T-1-04 | Accidental cloud inference enablement | `allow_cloud: false` default + tests |
| T-1-05 | Safety overclaim / motor commands in schema | Perception-only fields; no velocity/cmd |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter after plans complete verification map

**Approval:** pending

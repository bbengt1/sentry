---
phase: 10
slug: live-tensorrt-fixed-class-yolo
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-10
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `10-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`) |
| **Quick run command** | `uv run pytest tests/test_detection_factory.py tests/test_trt_parity.py tests/test_backend_honesty_status.py tests/test_export_docs.py tests/test_pyproject_onnx_extra.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Lint** | `uv run ruff check src tests` |
| **Estimated runtime** | ~30–90s quick; full suite per project baseline |
| **Hardware policy** | No Jetson / no system TensorRT / no real `.engine` load / no weight download in default CI |

---

## Sampling Rate

- **After every task commit:** Run quick run command above
- **After every plan wave:** Run full suite + ruff
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~120 seconds for quick set

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|----------------|-----------------|-----------|-------------------|-------------|--------|
| 10-01-W0 | 01 | 0 | TRT-01..04 | T-10-01 | No path traversal on engine resolve | unit stubs | factory/trt_parity tests exist | ❌ W0 | ⬜ pending |
| 10-01-* | 01 | 1+ | TRT-01, TRT-04 | T-10-01 | Live TRT only with allowlisted `.engine` | unit | `pytest tests/test_detection_factory.py -k trt -q` | ⚠️ extend | ⬜ pending |
| 10-01-* | 01 | 1+ | TRT-04 | — | Detection contract + set_conf | unit | `pytest tests/test_trt_parity.py -q` | ❌ W0 | ⬜ pending |
| 10-01-* | 01 | 1+ | honesty | — | status live=tensorrt | unit | `pytest tests/test_backend_honesty_status.py -q` | ⚠️ extend | ⬜ pending |
| 10-02-* | 02 | 1+ | TRT-02, TRT-03 | T-10-02 | No pip tensorrt; on-device docs | keyword/static | `pytest tests/test_export_docs.py tests/test_pyproject_onnx_extra.py -q` | ⚠️ extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Extend `tests/test_detection_factory.py` — live TRT success; `trt_artifact_missing`; `trt_dep_missing`; path_rejected; weights suffix honesty; rewrite soft-stub
- [ ] Add `tests/test_trt_parity.py` — Detection contract, set_conf, empty list, live weights guard (mirror ORT)
- [ ] Extend `tests/test_backend_honesty_status.py` — live TRT triple + soft-stub reason fixtures
- [ ] Extend `tests/test_export_docs.py` — live TRT conditions + system TensorRT / no pip pin + on-device rules
- [ ] Keep `tests/test_pyproject_onnx_extra.py::test_no_tensorrt_optional_extra`
- [ ] Ensure default suite does **not** call real `YOLO("*.engine")` load

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real `.engine` load on Jetson/desktop NVIDIA | TRT-01 | Hardware + system TensorRT | On device: export engine, `preferred_backend=tensorrt`, confirm detections + banner live=tensorrt |
| Dual-model VRAM (TRT YOLO + torch depth) | EDGE-RT-04 (Phase 11 scope) | Device-specific | Optional smoke only; not Phase 10 merge gate |

---

## Reason-code contract (assertable)

| Condition | backend_requested | backend_live | backend_reason |
|-----------|-------------------|--------------|----------------|
| preferred TRT + valid `.engine` + tensorrt importable | tensorrt | **tensorrt** | None |
| preferred TRT + no artifact | tensorrt | torch | `trt_artifact_missing` |
| preferred TRT + no system tensorrt | tensorrt | torch | `trt_dep_missing` |
| preferred TRT + path_rejected | tensorrt | torch | `path_rejected` |

**Retired:** `trt_loader_not_implemented` as default TRT outcome.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency within budget
- [ ] `nyquist_compliant: true` set in frontmatter after plans pass Dimension 8

**Approval:** pending

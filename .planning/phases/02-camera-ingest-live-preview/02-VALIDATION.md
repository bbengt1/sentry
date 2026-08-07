---
phase: 2
slug: camera-ingest-live-preview
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-07
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for camera ingest, frame bus, and live preview.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (≥8) |
| **Config file** | `pyproject.toml` → `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_frame_bus.py tests/test_sources_synthetic.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **API tests** | httpx ASGI against FastAPI app |
| **Estimated runtime** | ~30–60s (no hardware, no ML) |

---

## Sampling Rate

- **After every task commit:** Quick subset for touched module
- **After every plan wave:** `uv run pytest -q` + `uv run ruff check src tests`
- **Before verify-work:** Full suite green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-* | 01 | 1 | CAM-01..04 | T-2-01 | No unsafe capture paths | unit/mock | `pytest tests/test_sources_*.py -q` | ❌ W0 | ⬜ pending |
| 02-02-* | 02 | 2 | CAM-05, CAM-06 | T-2-02 | Keep-latest; no unbounded queue | unit | `pytest tests/test_frame_bus.py tests/test_capture_loop_reconnect.py -q` | ❌ W0 | ⬜ pending |
| 02-03-* | 03 | 3 | UI-01, MODEL-03 | T-2-03 | Localhost default bind | integration | `pytest tests/test_api_preview.py tests/test_cli_serve.py -q` | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/fixtures/` — short sample video or generate via cv2 in fixture
- [ ] `tests/test_sources_synthetic.py` — CAM-03
- [ ] `tests/test_sources_file.py` — CAM-02
- [ ] `tests/test_sources_opencv.py` — CAM-01 (mock cv2)
- [ ] `tests/test_sources_rtsp.py` — CAM-04 (mock)
- [ ] `tests/test_frame_bus.py` — CAM-05
- [ ] `tests/test_capture_loop_reconnect.py` — CAM-06
- [ ] `tests/test_api_preview.py` — UI-01
- [ ] `tests/test_cli_serve.py` — MODEL-03
- [ ] Runtime deps: opencv-python-headless, numpy, fastapi, uvicorn[standard]
- [ ] Dev dep: httpx

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real USB live motion | CAM-01, UI-01 | Hardware | Plug USB cam; `sentry serve --source usb`; open localhost preview |
| Unplug/replug recovery | CAM-06 | Hardware | Unplug → status error/reconnecting; replug → streaming |
| Optional RTSP lab camera | CAM-04 | Environment | Document known limits if flaky |

---

## Threat Model References

| ID | Pattern | Mitigation |
|----|---------|------------|
| T-2-01 | Arbitrary file/URL as capture source | Validate/document source types; no shell injection in path |
| T-2-02 | Unbounded memory from frame backlog | Depth-1 bus only |
| T-2-03 | Accidental LAN exposure | Default host 127.0.0.1; document --host opt-in |
| T-2-04 | Silent freeze on camera fail | Status enum + reconnect; UI shows error |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 deps
- [ ] Sampling continuity
- [ ] Wave 0 covers MISSING refs
- [ ] No watch-mode flags
- [ ] `nyquist_compliant: true` after plans land

**Approval:** pending

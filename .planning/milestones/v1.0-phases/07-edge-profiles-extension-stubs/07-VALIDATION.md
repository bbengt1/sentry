---
phase: 7
slug: edge-profiles-extension-stubs
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-08
---

# Phase 7 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest ≥8 |
| Config | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick | `uv run pytest tests/test_profile_application.py tests/test_headless_serve.py tests/test_extensions_stubs.py tests/test_camera_id_multi.py -q` |
| Full | `uv run pytest -q` |
| Export | Never run real GPU export / weight download in default CI |

## Dimension Coverage (EDGE-01..05)

| Req | Dimension | Wave 0 file | Assert |
|-----|-----------|-------------|--------|
| EDGE-01 | Docs | `tests/test_desktop_docs.py` | `docs/desktop-gpu.md` exists; README links; mentions `--profile desktop-gpu`, detect+depth extras |
| EDGE-02 | Profile→weights | `tests/test_profile_application.py` | desktop→yolo26s; jetson/cpu→yolo26n; OV n/s mapping; cpu forces device=cpu |
| EDGE-02 | Config load | `tests/test_config_profiles.py` (extend) | tiers present on all profiles; allow_cloud false |
| EDGE-02 | Probe | `tests/test_backend_protocols.py` (update) | stub or light probe never raises; cpu available semantics |
| EDGE-03 | Export docs | `tests/test_export_docs.py` | on-device TRT; no cross-SKU engine copy; Pi honesty; YOLO26 onnx/engine |
| EDGE-03 | Export CLI | `tests/test_export_script_cli.py` | `--help` / argparse; weights restricted to known names |
| EDGE-04 | Multi camera_id | `tests/test_camera_id_multi.py` | cam0 vs cam1 Frame/PerceptionFrame; empty id rejected |
| EDGE-04 | ROS2 stub | `tests/test_extensions_stubs.py` | import bridge; `start`/`emit` raise NotImplementedError |
| EDGE-04 | Voice no-op | same | VoiceNullSink.emit discards; optional entry point discoverable |
| EDGE-05 | Headless app | `tests/test_headless_serve.py` | `serve_ui=False` → GET `/` not HTML 200; `/v1/snapshot` still 200 |
| EDGE-05 | CLI flag | `tests/test_cli_serve.py` (extend) | `serve --help` shows `--no-ui` |

## Wave 0 Checklist

- [ ] `tests/test_profile_application.py`
- [ ] `tests/test_headless_serve.py`
- [ ] `tests/test_camera_id_multi.py`
- [ ] `tests/test_extensions_stubs.py`
- [ ] `tests/test_export_docs.py`
- [ ] `tests/test_export_script_cli.py`
- [ ] `tests/test_desktop_docs.py`
- [ ] Extend `tests/test_cli_serve.py` for `--no-ui`
- [ ] Update `tests/test_backend_protocols.py` if probe changes

## Threats

| ID | Pattern | Mitigation |
|----|---------|------------|
| T-7-01 | TRT engine treated as portable | Docs + content tests forbid “copy engine” guidance |
| T-7-02 | Headless + 0.0.0.0 without warning | Keep bind warning; docs safety section |
| T-7-03 | preferred_backend=tensorrt implies live TRT | Startup log + tests for device policy honesty |
| T-7-04 | Export script path injection | KNOWN_WEIGHTS basename allowlist |
| T-7-05 | FPS overclaim | Docs tests require lite/honest language for Pi |
| T-7-06 | rclpy forced into core | Stub imports without rclpy |
| T-7-07 | AGPL omitted from edge docs | desktop/export docs mention THIRD_PARTY |

## Sampling

- **Per task commit:** targeted quick tests for touched req
- **Per wave:** full `uv run pytest -q` + `uv run ruff check src tests`
- **Phase gate:** all EDGE rows green before verify-work

**Approval:** pending planner

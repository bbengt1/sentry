# Integration Check — Sentry AI v1.0 (phases 1–7)

**Date:** 2026-08-09  
**Checker:** gsd-integration-checker  
**Status:** passed (non-critical tech debt only)

## Spine (verified end-to-end)

```
Source (synthetic|usb|file|rtsp)
  → FrameBus (depth-1)
  → CaptureLoop ──publish──► bus
  → DetectionLoop ──set_detections──► PerceptionStore
  → DepthLoop ──set_depth──► PerceptionStore
  → FreeSpaceLoop ──snapshot_depth → set_free_space──► PerceptionStore
  → OpenVocabLoop ──set_open_vocab only──► PerceptionStore
  → create_app(store, loops, workers, pipeline_state, serve_ui)
       ├─ /preview/mjpeg  (store snapshots → overlays)
       ├─ /api/status     (bus + store + pipeline + ov mode)
       ├─ /api/pipeline/config  → loop.set_enabled / set_cuts + clear_*
       ├─ /api/open-vocab/*     → mode/arm (process on OV thread)
       └─ /v1/snapshot + /v1/stream + /api/snapshot
            └─ assemble_perception_frame(store)  [single merge path]
```

CLI `serve` constructs one shared `PerceptionStore`, injects it into all loops + `create_app`, starts capture → det → depth → free_space → ov; stops reverse. Profile path: `load_config(profile)` → `profile_runtime(cfg)` → worker weights/device.

## Wiring matrix

| Component | Consumers | Status | Evidence |
|-----------|-----------|--------|----------|
| FrameBus | CaptureLoop writer; Det/Depth/OV loops readers; MJPEG | PASS | `cli.py` + loop ctors |
| PerceptionStore | All product loops write; assemble + MJPEG + status read | PASS | single store instance in serve |
| assemble_perception_frame | `/v1/snapshot`, `/v1/stream`, `/api/snapshot` | PASS | routes_* call only assembler |
| PipelineState | routes_pipeline + status + UI PATCH | PASS | create_app inject + index.html |
| profile_runtime | serve worker construction | PASS | cli.py detector/OV/depth weights |
| FreeSpaceLoop | store depth → free_space product | PASS | spatial/loop.py polls snapshot_depth |
| OpenVocabLoop | set_open_vocab only (not set_detections) | PASS | source + tests |
| create_app routers | preview, detection, depth, pipeline, open_vocab, v1 | PASS | app.py include_router all 6 |
| serve_ui / --no-ui | root HTML gate; API/v1 remain | PASS | routes_preview + headless tests |
| Plugin registry | health list + entry points sources/workers/sinks | PASS | builtins + discover; ROS2 not auto-reg |
| Perception-only boundary | no motor routes; schema extra=forbid; tests | PASS | test_api_perception_only |

## E2E flows

| Flow | Result | Notes |
|------|--------|-------|
| A synthetic → status + MJPEG + snapshot | PASS | create_app + capture + store path; tests green |
| B enable det/depth/FS → completeness | PASS | loops write products; assemble Completeness; pipeline disable clears |
| C OV on-demand non-blocking fixed-class | PASS | separate thread + store slot; POST /run arms only |
| D headless API consumer | PASS | --no-ui → serve_ui=False; /v1 + /api live |
| E desktop-gpu docs vs CLI | PASS | docs/desktop-gpu.md matches `--profile desktop-gpu` + --no-ui |

**Focused pytest:** 83 passed (`test_cli_serve`, `test_api_v1`, `test_headless_serve`, `test_pipeline_config`, `test_loop_enable_gates`, `test_api_perception_only`, assemble*, `test_profile_application`, `test_camera_id_multi`).

## Non-critical gaps / tech debt

1. **Depth disable does not cascade-clear free-space** — intentional (06 research: independent flags; FS idles without depth). Overlay draws last free-space until FS disabled or process end; `/v1` marks `free_space_stale` after TTL but completeness stays true (stale ≠ incomplete SPACE-04). Overlay does not suppress stale products.
2. **`bus_metrics` not passed into `/v1` assemble** — capture_fps/frames_dropped live on `/api/status` only, not PerceptionFrame.stats via stream/snapshot.
3. **YOLOE open-vocab worker not in plugin registry/entry points** — serve constructs directly; `sentry health` workers omit yoloe.
4. **Serve source construction bypasses registry** — hardcoded `_build_serve_source`; entry-point-only sources won't appear in serve without CLI change (v1 OK).
5. **Missing extras → PipelineState still defaults stages enabled** — loops None; PATCH updates state but cannot clear products that never existed; UI may show enabled with no product.
6. **Known phase-4:** live `set_depth_mode` does not reload HF weights (label/id update only).

## Requirements integration (cross-phase)

All REQ-IDs in milestone scope have multi-phase touchpoints WIRED (FOUND→…→EDGE/MODEL). No requirement is stranded as single-phase-only with a missing consumer.

## Recommendation

**Milestone audit status: passed** — integration spine is coherent; no BLOCKER broken connections. Record tech debt items above as non-blocking follow-ups.

# Phase 4 UI Spec — Depth Colormap

**Extends:** Phase 2 Live Preview + Phase 3 detection overlays

## Purpose

Show monocular depth as a colormap so makers can see spatial structure, with honest relative vs metric labeling.

## Surfaces

| Surface | Phase 4 |
|---------|---------|
| Live RGB (+ detection boxes if enabled) | Keep |
| Depth colormap | **Yes** (overlay blend and/or side-by-side) |
| Depth kind badge | **Yes** (`relative` / `metric_estimated` / …) |
| Depth latency ms | **Yes** in status bar |
| Metric mode toggle (optional) | Optional config control; must label clearly |
| Free-space overlay | No (Phase 5) |

## Layout

```
┌────────────────────────────────────────────────────┐
│ Sentry AI — Live Preview                [status]   │
├────────────────────────────────────────────────────┤
│  [ RGB (+ dets) ]     or     [ RGB | Depth map ]   │
│  (or blended colormap overlay)                     │
├────────────────────────────────────────────────────┤
│ Depth: relative | Latency: n ms | FPS/drops…       │
│ Conf: [slider]  (detection)                        │
└────────────────────────────────────────────────────┘
```

## Visual rules

- Colormap: perceptually ordered (e.g. TURBO or MAGMA via OpenCV) — near = warm/cool consistent; document which
- **Never** show unit “m” when `depth_kind == relative`
- Metric modes: show `m` only when kind is metric_estimated or metric_calibrated
- Badge text exact enum values or human labels: “Relative depth (not meters)”
- Empty depth: show “Depth: unavailable” without crashing stream

## Transport

Prefer **server-side** depth colormap composite into MJPEG (parity with detection overlay).  
JSON snapshot carries `DepthPayload` metadata (+ optional downsampled stats, not full giant arrays unless designed).

## Acceptance

1. Live page shows depth colormap when depth product present  
2. Status shows depth_kind and depth latency  
3. Relative mode never displays meters  
4. Optional metric mode visibly labeled when enabled  

---
*Phase: 04-monocular-depth*

# Phase 3 UI Spec — Detection Overlays

**Status:** Contract for Phase 3  
**Extends:** Phase 2 Live Preview (`02-UI-SPEC.md`)

## Purpose

Show fixed-class detections on the live feed and expose runtime confidence control so the developer sees the same boxes the API reports.

## Surfaces

| Surface | Phase 3 |
|---------|---------|
| Live video | Keep (MJPEG) |
| Bounding boxes + class labels + conf | **Yes** |
| Confidence threshold control | **Yes** (slider or number input) |
| Detection count / FPS / stage latency | **Yes** (read-only text) |
| Depth / free-space overlays | No |
| Stage enable toggles for all models | Optional minimal "detection on" — full stage matrix Phase 6 |
| Open-vocab prompt | No |

## Layout (extends Phase 2)

```
┌──────────────────────────────────────────────────┐
│ Sentry AI — Live Preview              [status]   │
├──────────────────────────────────────────────────┤
│                                                  │
│     video with detection overlays                │
│     (boxes + class + conf)                       │
│                                                  │
├──────────────────────────────────────────────────┤
│ Source | FPS | Drops | Detections: n | Det ms    │
│ Conf threshold: [====•====] 0.25                 │
│ Bind: 127.0.0.1:PORT                             │
└──────────────────────────────────────────────────┘
```

## Overlay rules

- Box color: high-contrast (e.g. lime or cyan) on dark video
- Label format: `{class_name} {confidence:.2f}` above or inside box
- Coordinates: image pixel space, axis-aligned xyxy
- When no detections: video continues; "Detections: 0" shown
- Overlay truth = same detection list as API snapshot (no second model)

## Interaction

- Confidence threshold control updates pipeline **without restart**
- Prefer: `POST`/`PATCH` control endpoint or query param applied to worker; UI polls status
- Debounce slider input (~100–200ms) to avoid thrashing

## Transport options (implementation may pick one)

**A (recommended):** Draw boxes on server JPEG before MJPEG encode (parity guaranteed; simple HTML).  
**B:** MJPEG RGB + JSON detections; canvas overlay in browser (must sync frame_id).

Either is acceptable if DET-04 parity is testable.

## Copy

- No autonomy/safety language
- Note model may download on first run (cache thereafter)

## Acceptance (UI)

1. Live page shows boxes when objects present (synthetic demo or real camera)
2. Changing conf threshold updates overlays without restart
3. Status shows detection count and optional latency
4. Localhost-only default preserved

---
*Phase: 03-fixed-class-detection*

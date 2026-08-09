# Phase 2 UI Spec — Live Preview (minimal)

**Status:** Contract for Phase 2 only  
**Scope:** Minimal browser live-video preview — not the full developer dashboard (Phase 6)

## Purpose

Let a maker confirm the camera pipeline works: open a localhost page and see live frames from USB, file, or synthetic source. No overlays, no model controls.

## Surfaces

| Surface | Required in Phase 2 |
|---------|---------------------|
| Live video feed | Yes |
| Source / camera status (connected, reconnecting, error) | Yes |
| Capture FPS / drop count (read-only) | Yes (can be text) |
| Detection/depth overlays | No — Phase 5+ |
| Threshold controls | No — Phase 6 |
| Chat / open-vocab | No |

## Layout

```
┌─────────────────────────────────────────────┐
│ Sentry AI — Live Preview          [status]  │
├─────────────────────────────────────────────┤
│                                             │
│              video element / img            │
│              (MJPEG or WS JPEG)             │
│                                             │
├─────────────────────────────────────────────┤
│ Source: {camera_id}   FPS: n   Drops: n     │
│ Bind: 127.0.0.1:PORT                        │
└─────────────────────────────────────────────┘
```

- Single column, max content width ~960px, centered
- Dark neutral background (dev-tool aesthetic is fine)
- Status pill: green = streaming, yellow = reconnecting, red = error / no source

## Interaction

- Page loads and **auto-connects** to preview stream on same origin
- No login
- If stream fails: show clear error message + last known status (no blank silent page)
- Refresh re-establishes stream

## Transport (implementation choice — research may refine)

**Preferred Phase 2:** MJPEG endpoint (`GET /preview/mjpeg` or similar) rendered in `<img>` — simplest, works without frontend build.

**Acceptable alternative:** WebSocket JPEG frames.

**Out of Phase 2:** WebRTC.

## Copy / product language

- Title: “Sentry AI — Live Preview”
- No “autonomous”, “safe to drive”, or motor/control language
- Perception / camera pipeline only

## Accessibility (minimum)

- Status text is visible (not color-only)
- Page has a meaningful `<title>`
- Error messages in plain language

## Non-goals

- Design system, brand kit, multi-page app
- React/Vite mandatory (static HTML served by FastAPI is OK)
- Mobile-first polish

## Acceptance (UI)

1. Opening `http://127.0.0.1:{port}/` (or documented path) shows live video when a source is running
2. Disconnecting source updates status to error/reconnecting without freezing the whole page forever
3. FPS/drops (or equivalent) visible when metrics are available
4. Default docs only advertise localhost URLs

---
*Phase: 02-camera-ingest-live-preview*

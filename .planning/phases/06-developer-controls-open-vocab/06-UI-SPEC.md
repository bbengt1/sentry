# Phase 6 UI Spec — Controls Console + Open-Vocab

**Extends:** Phase 2–5 Live Preview

## Purpose

Give developers full interactive control of perception stages and thresholds, plus an open-vocab prompt path for ad-hoc classes.

## Layout

```
┌──────────────────────────────────────────────────────────┐
│ Sentry AI — Live Preview          [status] [STALE?]      │
├──────────────────────────────────────────────────────────┤
│  video (depth + free-space + boxes)                      │
├──────────────────────────────────────────────────────────┤
│ Stages:  [✓] detection  [✓] depth  [✓] free-space        │
│ Fixed conf:  [====•====] 0.25                            │
│ Free-space near/mid: [====] [====]                       │
│ Open-vocab: [ text prompt............ ] [Run] [✓ enable] │
│ Telemetry: cap FPS | det ms/fps | depth ms/fps | fs ms   │
└──────────────────────────────────────────────────────────┘
```

## Controls

| Control | Behavior |
|---------|----------|
| Stage toggles | PATCH pipeline; disabled stages stop compute (not only hide) |
| Det conf | Existing slider; debounced ~150ms |
| Free-space cutoffs | Adjust near/mid band thresholds live |
| Open-vocab prompt | Text + Run / enable continuous lower-rate |
| Telemetry | Show capture + stage FPS/latency (UI-05) |

## Open-vocab UX

- Placeholder: e.g. `person, red cup, toolbox`
- Distinct box color or label prefix for open-vocab vs fixed-class
- When disabled/off: no open-vocab on stream
- Document first-run weight download (AGPL / cache)

## Acceptance

1. Toggle detection/depth/free-space without restart  
2. Thresholds update live from UI  
3. Telemetry visible on dashboard  
4. Open-vocab prompt produces labeled detections when enabled  
5. Fixed-class path not blocked when open-vocab idle/on-demand  

## Non-goals

- Chat/VLM primary UI  
- Autonomy / safety language  

---
*Phase: 06-developer-controls-open-vocab*

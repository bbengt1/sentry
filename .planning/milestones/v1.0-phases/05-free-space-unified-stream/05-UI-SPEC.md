# Phase 5 UI Spec — Free-Space Overlay + Stream Honesty

**Extends:** Phase 2–4 Live Preview (video, boxes, depth colormap)

## Purpose

Show free-space / obstacles on the live feed and ensure UI matches the robot API. Surface stale/incomplete state without implying autonomy safety.

## Surfaces

| Surface | Phase 5 |
|---------|---------|
| RGB + detection boxes + depth colormap | Keep |
| Free-space / obstacle overlay | **Yes** |
| Obstacle count / free-space status in footer | **Yes** |
| Stale / incomplete badge | **Yes** |
| Stage toggles / free-space cutoff slider | Optional minimal; full matrix Phase 6 |
| “Safe to drive” / go-nogo | **Never** |

## Visual rules

- Free-space: semi-transparent green (or cool) mask where free; red/amber for near obstacles
- Or: contour / band highlight for near-field obstacles only
- Do not use green checkmarks implying safe navigation
- Stale: yellow/red “STALE” or “incomplete” text when TTL exceeded or products missing
- Footer: `free_space: … | obstacles: n | age_ms: …` + existing det/depth fields

## Layout

```
┌────────────────────────────────────────────────────┐
│ Sentry AI — Live Preview     [status] [STALE?]     │
├────────────────────────────────────────────────────┤
│  video: depth blend + boxes + free-space mask      │
├────────────────────────────────────────────────────┤
│ FPS drops | det | depth kind/ms | free_space | obs │
└────────────────────────────────────────────────────┘
```

## Acceptance

1. Free-space/obstacles visible when depth product present  
2. Overlay content matches `/v1/snapshot` free_space fields (same store)  
3. Stale/incomplete visible when applicable  
4. No copy implying motor safety or autonomy  

---
*Phase: 05-free-space-unified-stream*

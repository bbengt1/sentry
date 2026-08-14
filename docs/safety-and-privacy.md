# Safety and privacy

Maker-honest positioning for Sentry AI v1. This is **not** legal advice — it is
how the project intends operators and robot integrators to treat the system.

## Perception-only (non-autonomy)

Sentry AI is a **perception stream**, not an autonomous driving / FSD stack and
not a robot controller.

- Wire envelopes (`PerceptionFrame`, free-space, detections, depth metadata)
  intentionally **exclude** motor / control fields: `cmd`, `cmd_vel`, `twist`,
  `velocity`, `path_plan`, `safe_to_drive`, `go_nogo`, and related keys
  (API-05 denylist).
- Monocular hobby depth + COCO-class detection is **not** vehicle-grade
  sensing. Do not treat outputs as navigation clearance or autonomy permission.
- Your **human or robot controller owns e-stop**, motion limits, and any
  closed-loop behavior. Sentry does not arm actuators.

## Free-space is not a safety interlock

Near-field free-space / obstacle cues are **ordinal unless** depth is
`metric_calibrated` (then `units="m"` with 1.5 m / 3.0 m cuts). Even when
calibrated, meters are approximate monocular scale — still **not** a safety
interlock:

- Products can be **incomplete** or marked **STALE** (`stats.free_space_stale`,
  `products_stale`, age fields). Consumers **must** honor completeness and
  stale/TTL flags.
- Invalidated or missing free-space must **not** be treated as “clear path.”
- Free-space is **not a safety interlock**. Do not wire it alone into enable
  lines, brake release, or unsupervised motion.

Operator wizard and persist: [calibration.md](calibration.md).

## Privacy and network exposure

| Mode | Behavior |
|------|----------|
| **Default** | Bind **`127.0.0.1`** (localhost only) — camera-derived frames stay on-box |
| **LAN opt-in** | `--host 0.0.0.0` (or other non-loopback) exposes live stream + APIs **without authentication** |
| **Cloud** | `allow_cloud: false` by default — local OSS weights/cache only; no mandatory cloud AI keys |

```bash
# Privacy risk — LAN exposure, no auth:
uv run sentry serve --source synthetic --host 0.0.0.0
```

**Headless is not authentication.** `sentry serve --no-ui` only omits Live
Preview HTML; `/v1/*`, `/api/*`, and MJPEG preview routes can still serve
perception data. Binding headless on `0.0.0.0` remains an unauthenticated
LAN exposure of camera-derived products.

Do not put Sentry on a public interface without your own reverse-proxy auth,
TLS, and access control.

## Local OSS model policy

- Core path is **local open-source models** with offline cache after first
  download (`SENTRY_MODEL_CACHE` / `~/.cache/sentry-ai`).
- Default depth weights: Depth Anything V2 **Small** (Apache-2.0).
- Detection / open-vocab (Ultralytics) is **AGPL-3.0** — optional extra; see
  [`THIRD_PARTY_MODELS.md`](../THIRD_PARTY_MODELS.md).
- CC-BY-NC Base/Large depth weights are **never default**.

## Operator checklist

1. Develop on **localhost** unless you intentionally need LAN.  
2. Treat free-space / depth as **advisory perception**, not interlocks.  
3. Keep e-stop and motion authority outside Sentry.  
4. Read model licenses before commercial redistribution.  
5. Prefer `--profile desktop-gpu` for full dual-model maker work; keep
   `cpu-fallback` for CI / no-GPU (see [desktop GPU path](desktop-gpu.md)).  
6. Treat calibrated meters as **approximate monocular scale**, not
   vehicle-grade — see [calibration.md](calibration.md).  

## Related docs

- [Calibration wizard](calibration.md)  
- [Desktop GPU primary path](desktop-gpu.md)  
- [Camera sources](camera-sources.md)  
- [Export / Jetson packaging](export/README.md)  
- [Third-party model licenses](../THIRD_PARTY_MODELS.md)  

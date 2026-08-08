# Phase 7: Edge Profiles & Extension Stubs - Context

**Gathered:** 2026-08-08  
**Status:** Ready for planning  
**Source:** ROADMAP + REQUIREMENTS + Phase 1–6 shipped contracts (YOLO mode)

<domain>
## Phase Boundary

Make **multi-target deployment real** and leave **clean extension points** for post-v1 capabilities — without building full ROS2, multi-cam fusion, or voice products.

**In scope:**
- Documented desktop GPU end-to-end path as primary maker path (EDGE-01)
- Runtime profiles that actually select model tiers / backends for desktop, Jetson-class, CPU/lite (EDGE-02)
- ONNX and/or TensorRT export **recipes** + on-device engine build notes (EDGE-03) — docs + scripts, not a full TRT runtime in v1 unless already thin
- Headless mode: perception API without requiring the web UI (EDGE-05)
- Extension stubs: multi-cam `camera_id` schema tests, ROS2 bridge scaffold, voice plugin no-op (EDGE-04)
- Safety / privacy disclaimers and non-autonomy positioning finalized in docs

**Out of scope:**
- Full multi-camera fusion / calibration UX
- Production ROS2 node with bag recording and lifecycle management
- Real voice I/O or VLM scene chat
- Claiming Pi sustained dual-model realtime without honest FPS notes
- Shipping prebuilt TensorRT engines for every JetPack SKU
- Robot control / navigation commands
- Mandatory LAN auth (document risk; localhost remains default)
- React/Vite rewrite

</domain>

<decisions>
## Implementation Decisions

### Locked from product / research / roadmap
- Three built-in profiles already exist as YAML: `desktop-gpu`, `jetson`, `cpu-fallback` (FOUND-06)
- Profiles must drive **detector_tier / depth_tier / preferred_backend** at serve time (not advisory-only docs)
- Export path is **recipes + scripts** (PyTorch → ONNX → TensorRT FP16 notes); do not require Jetson hardware in CI
- Headless = serve perception API without mounting/serving static UI (or `--no-ui` / equivalent)
- Stubs only for ROS2 / multi-cam / voice — scaffolds that compile/import and document extension points
- Perception-only, non-autonomy, privacy (localhost default) language finalized
- Local OSS only; `allow_cloud: false` default remains

### From Phase 1–6 shipped
- `RuntimeProfile`, `BackendName`, profile YAML under `src/sentry_ai/config/profiles/`
- `load_config(profile=...)` + `SentryConfig.models.detector_tier` already used for YOLO weights in `serve`
- `probe_device` stub always returns `available=False` (Phase 1 honesty)
- `camera_id` already on Frame / PerceptionFrame / store products
- Plugin registry: sources, workers, sinks entry points
- `NullSink` exists; no ROS2 or voice packages
- `sentry serve` always mounts Live Preview static UI today
- Optional extras: `detect`, `depth` (and open-vocab via detect)
- Docs: README, THIRD_PARTY_MODELS.md, docs/camera-sources.md

### Claude's Discretion
- Whether headless is `--no-ui` flag, separate `sentry api` command, or env `SENTRY_HEADLESS`
- How far to go on real device probe (torch.cuda / platform hints) vs keep advisory + docs
- Export scripts location (`scripts/export/` vs `docs/export/`) and whether they invoke ultralytics export API
- ROS2 stub shape: package layout + README only vs importable Python bridge module with NotImplemented
- Profile defaults: keep serve default `cpu-fallback` or switch desktop-gpu when CUDA detected
- Whether open-vocab is disabled by default on jetson/cpu profiles
- Exact JetPack / TensorRT version matrix wording (honest “as of” notes)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product / planning
- `.planning/PROJECT.md` — multi-target + extensibility constraints
- `.planning/ROADMAP.md` — Phase 7 goal, success criteria, 3-plan split
- `.planning/REQUIREMENTS.md` — EDGE-01..05
- `.planning/research/SUMMARY.md` — Phase 7 research flags (Jetson/Pi packaging)
- `.planning/phases/06-developer-controls-open-vocab/06-02-SUMMARY.md` — latest serve / open-vocab shape
- `.planning/phases/01-foundations-contracts/01-03-SUMMARY.md` — profiles, plugins, backend stubs

### Code
- `src/sentry_ai/config/profiles/{desktop-gpu,jetson,cpu-fallback}.yaml`
- `src/sentry_ai/config/load.py`, `src/sentry_ai/config/models.py`
- `src/sentry_ai/schemas/enums.py` — RuntimeProfile, BackendName
- `src/sentry_ai/backend/protocols.py` — InferenceBackend, probe_device stub
- `src/sentry_ai/cli.py` — serve lifecycle, profile, camera_id
- `src/sentry_ai/api/app.py` — create_app, static UI mount
- `src/sentry_ai/plugins/` — registry, builtins, protocols
- `src/sentry_ai/models/cache.py` — tier_to_weight
- `src/sentry_ai/schemas/perception.py` — camera_id on PerceptionFrame
- `README.md`, `THIRD_PARTY_MODELS.md`, `docs/camera-sources.md`

### External (research targets)
- Ultralytics export (ONNX / TensorRT) docs for YOLO26 / YOLOE
- NVIDIA Jetson / JetPack TensorRT engine build notes (on-device build; no cross-SKU engine copy)
- Depth Anything V2 / HF export constraints for edge

</canonical_refs>

<specifics>
## Specific Ideas

Roadmap plans (3):
1. **07-01** — Runtime profiles + edge model tiers + headless mode  
2. **07-02** — ONNX/TensorRT export recipes + Jetson packaging notes  
3. **07-03** — Extension stubs (ROS2 scaffold, multi-cam `camera_id` tests, voice no-op) + release docs (safety/privacy)

Success criteria from ROADMAP:
1. Desktop GPU full pipeline documented end-to-end as primary maker path  
2. Runtime profiles select model tiers/backends for desktop, Jetson-class, CPU/lite  
3. ONNX and/or TensorRT export recipes with on-device engine build notes  
4. Headless mode serves perception API without the UI  
5. Stubs for ROS2, multi-cam schema tests, voice plugin no-op  
6. Safety/privacy disclaimers and non-autonomy positioning finalized  

Honest edge messaging:
- Jetson: YOLO n + DAV2-Small; open-vocab off or on-demand  
- CPU/lite: spatial awareness lite; document expected limits  
- Never claim Pi full dual-model realtime without measured FPS  

</specifics>

<deferred>
## Deferred Ideas

- Full ROS2 Humble/Jazzy production package and launch files
- Multi-cam fusion and extrinsic calibration UI
- Voice ASR/TTS product
- Prebuilt TRT engines in releases
- OpenVINO first-class path beyond BackendName enum
- Authenticated remote API
- Metric-calibrated free-space meters (needs calibration phase)

</deferred>

---

*Phase: 07-edge-profiles-extension-stubs*  
*Context gathered: 2026-08-08 via YOLO plan-phase (roadmap + shipped code)*

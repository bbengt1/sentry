# Third-Party Model Weights & Licenses

This document records **model weight licenses** used or planned by Sentry AI.
Application code is Apache-2.0 (see [LICENSE](LICENSE)). Model weights are
separate artifacts with their own terms.

**Policy (MODEL-01):** The core inference path is **local open-source only**.
No cloud API keys are required for the default install or `uv run sentry smoke`.
Config field `allow_cloud` defaults to **false**; enabling cloud inference is
non-default and out of the v1 core path.

## License table

| Model / weights | Role | License | Default? | Notes |
|-----------------|------|---------|----------|-------|
| Depth Anything V2 **Small** | Depth | **Apache-2.0** | **Yes** | Commercially friendly default depth model |
| Depth Anything V2 Base / Large / Giant | Depth | **CC-BY-NC-4.0** | **No** | Research-only; non-commercial (NC) weights |
| DAV2 Metric indoor / outdoor heads | Depth (metric) | Check per weight | Optional | Domain-specific metric heads; verify before shipping |
| YOLO26 (via Ultralytics) | Fixed-class detect | **AGPL-3.0** (Ultralytics) | **No** — Planned Phase 3 | AGPL commercial caution; non-default for commercial forks |
| YOLOE | Open-vocab detect | **AGPL-3.0** (Ultralytics) | **No** — Planned Phase 6 | Non-blocking for Phase 1; non-default |

## Default selection rules

1. **Depth:** Prefer Depth Anything V2 **Small** (Apache-2.0) on every profile.
2. **Detection:** Ultralytics-packaged YOLO weights are **AGPL-3.0** — document
   carefully; commercial deployments must evaluate AGPL obligations or use
   alternative commercially licensed detectors (future work).
3. **NC / CC-BY-NC weights:** Never default. Mark research-only in UI/docs when
   optionally enabled in later phases.
4. **Cloud APIs:** Not on the core path. `allow_cloud: false` by default; smoke
   and health never call remote inference.

## References

- Depth Anything V2: https://github.com/DepthAnything/Depth-Anything-V2
- Ultralytics license: https://github.com/ultralytics/ultralytics/blob/main/LICENSE
- Policy constants: `sentry_ai.policy` (`DEFAULT_DEPTH_WEIGHT_KEY`,
  `DEFAULT_ALLOW_CLOUD`, `NON_DEFAULT_LICENSE_TAGS`)

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
| Depth Anything V2 **Small** | Depth | **Apache-2.0** | **Yes** — Phase 4 active (optional `depth` extra) | Default monocular depth via HF Transformers (`depth-anything/Depth-Anything-V2-Small-hf`). Relative mode by default (`DepthKind.relative`, no meters). Install: `uv sync --extra depth`. Weights cache under `SENTRY_MODEL_CACHE/hf` (MODEL-02); offline after first download. |
| Depth Anything V2 Base / Large / Giant | Depth | **CC-BY-NC-4.0** | **No** | Research-only; non-commercial (NC) weights. **Never default** in Sentry. |
| DAV2 Metric indoor / outdoor heads | Depth (metric) | Check per weight | Optional | Small metric HF heads only; labeled `metric_estimated` + `unit="m"`. Verify license before shipping commercial products. |
| YOLO26 (via Ultralytics) | Fixed-class detect | **AGPL-3.0** (Ultralytics) | **No** — Phase 3 active (optional `detect` extra) | **AGPL commercial caution** — non-default for commercial forks. Weights download once into Sentry cache (`SENTRY_MODEL_CACHE` or `~/.cache/sentry-ai/weights`); offline re-run after first pull (MODEL-02). Install: `uv sync --extra detect`. |
| YOLOE | Open-vocab detect | **AGPL-3.0** (Ultralytics) | **No** — Planned Phase 6 | Non-blocking for Phase 1; non-default |

## Model cache (MODEL-02)

Sentry points Ultralytics `weights_dir` and Hugging Face cache at a project-owned root:

| Setting | Value |
|---------|-------|
| Env override | `SENTRY_MODEL_CACHE` |
| Default root | `~/.cache/sentry-ai` |
| Weights dir (YOLO) | `<cache_root>/weights` |
| HF home (depth) | `<cache_root>/hf` (`HF_HOME`; hub under `hf/hub`) |
| Ultralytics config | `YOLO_CONFIG_DIR` → `<cache_root>/ultralytics` (setdefault) |

After the first download of YOLO (`yolo26n.pt` / `yolo26s.pt` / `yolo26m.pt`) or
Depth Anything V2 Small (HF hub under `hf/`), subsequent runs are **offline**
(no network required). Unit tests mock YOLO/depth models and never download
weights.

## Default selection rules

1. **Depth:** Prefer Depth Anything V2 **Small** (Apache-2.0) on every profile.
2. **Detection:** Ultralytics-packaged YOLO weights are **AGPL-3.0** — document
   carefully; commercial deployments must evaluate AGPL obligations or use
   alternative commercially licensed detectors (future work). Phase 3 ships
   YOLO26 behind the optional `detect` extra (`ultralytics-opencv-headless`).
3. **NC / CC-BY-NC weights:** Never default. Mark research-only in UI/docs when
   optionally enabled in later phases.
4. **Cloud APIs:** Not on the core path. `allow_cloud: false` by default; smoke
   and health never call remote inference.

## References

- Depth Anything V2: https://github.com/DepthAnything/Depth-Anything-V2
- Ultralytics license: https://github.com/ultralytics/ultralytics/blob/main/LICENSE
- Policy constants: `sentry_ai.policy` (`DEFAULT_DEPTH_WEIGHT_KEY`,
  `DEFAULT_ALLOW_CLOUD`, `NON_DEFAULT_LICENSE_TAGS`)

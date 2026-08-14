# Calibration — approximate monocular metric scale

Operator hub for the Live Preview **wizard**. This path produces an
**approximate metric scale** from a monocular depth map. It is **not
vehicle-grade**, not FSD, and not a robot controller.

Known-distance samples are the **primary** ground truth. Object height is
optional and approximate. Draft fit numbers **never** claim
`metric_calibrated`.

## 1. Install the depth extra (maker machine)

```bash
# From repo root — maker machine only. Default CI stays `uv sync --extra dev`.
uv sync --extra depth
# Typical dual-model desktop:
uv sync --extra dev --extra detect --extra depth
```

## 2. Serve and open Live Preview

```bash
uv run sentry serve --profile desktop-gpu --source usb --device 0
# → http://127.0.0.1:8000/  (Live Preview + calibration wizard)
```

Synthetic bring-up (no camera) still starts the wizard REST:

```bash
uv run sentry serve --source synthetic
```

## 3. Sample at a known distance

1. Optionally **Freeze** the current depth product (stable ROI).
2. Click a point or box on the preview.
3. Enter **known distance** in meters (primary). Height + bbox is optional.
4. Repeat for a few well-spaced samples.

REST: `POST /api/depth/calibration/freeze` then
`POST /api/depth/calibration/sample`. Sample is **409** if calibration is
already applied. Bodies use `extra=forbid`. **503** if state is missing.

## 4. Fit preview (draft only)

Use the wizard **Fit** control (REST `POST /api/depth/calibration/compute`).
Inspect scale, optional offset, and residual. A rejected fit stays draft —
it does **not** promote `metric_calibrated` or write YAML.

## 5. Apply or Cancel

| Action | Effect |
|--------|--------|
| **Apply** | Commits draft → applied+valid. Live `depth.kind` may become `metric_calibrated`. |
| **Cancel** | **Draft-only** — drops samples/draft params. Does **not** clear applied. Does **not** delete YAML. |

## 6. Optional persist

Session-only Apply is forgotten on restart unless you persist:

- Apply with `{"persist": true}`, or
- `POST /api/depth/calibration/save` after Apply

## 7. Restart re-applies on fingerprint match

`sentry serve` calls `try_reapply` when a YAML file is present. Re-apply
succeeds only when fingerprints match (`camera_id`, `depth_mode`,
`model_id`; width×height when **both** sides are known). Mismatch →
`ignored_mismatch` and depth stays **relative** (never silent meters).

Headless `--no-ui` still loads persist.

## 8. Clear deletes YAML

**Clear** wipes applied + draft and **deletes** the YAML file so a restart
cannot resurrect the scale. Cancel never deletes the file.

## Honesty triad

| Kind / state | Meters? |
|--------------|---------|
| `relative` | **Never** `unit="m"` |
| `metric_estimated` | Approximate indoor/outdoor head — **not** calibrated |
| `metric_calibrated` | `unit="m"` **only** when applied **and** valid |
| Draft (fit preview) | **Never** claims calibrated |

**Approximate metric scale — monocular, not vehicle-grade.**

## Free-space units

`free_space.units="m"` **iff** `depth.kind=metric_calibrated` **and** the
loop uses absolute **1.5 m / 3.0 m** cuts. Otherwise units stay **ordinal**.
`nearness_*` remain 0..1. Optional `distance_m` on obstacle cues appears
**only when calibrated** (mean finite blob depth).

## Persist path (STACK YAML)

YAML on the STACK cache — not a user-config JSON file.

| Mechanism | Path |
|-----------|------|
| Default | `$SENTRY_MODEL_CACHE/calibration/{safe_id}.yaml` |
| If cache unset | `default_cache_root()/calibration/{safe_id}.yaml` |
| Directory override | `SENTRY_CALIBRATION_DIR/{safe_id}.yaml` |
| Explicit file | `sentry serve --calibration-file PATH` |

`safe_id` is the sanitized `camera_id` stem (`..` rejected).

## Persist status ≠ `depth.kind`

Additive `GET /api/status` field `calibration_persist`:

| Status | Meaning |
|--------|---------|
| `none` | No file / nothing applied from disk |
| `applied` | YAML matched and re-applied (or just saved) |
| `ignored_mismatch` | File present; fingerprint refused |
| `error` | Unreadable / invalid file (soft inactive) |

Serve banner: `calibration: {status}` (optional `reason=`). These tokens
are **separate from** `depth.kind`.

## Related docs

| Doc | Role |
|-----|------|
| [perception-frame.md](perception-frame.md) | Wire contract: FS meters only when calibrated |
| [safety-and-privacy.md](safety-and-privacy.md) | Not FSD; FS still not a safety interlock |
| [api-reference.md](api-reference.md) | Wizard REST table |
| [cli.md](cli.md) | `--calibration-file` + persist banner |
| [configuration.md](configuration.md) | Env + cache layout |
| [desktop-gpu.md](desktop-gpu.md) | Primary maker path |

# Depth Anything V2 export (feasibility notes)

Sentry’s **live** monocular depth path is **Hugging Face Transformers** Depth
Anything V2 **Small** (Apache-2.0), not a first-class ONNX/TensorRT runtime.

This page is **feasibility notes + community links** only. Export does not
block Phase 7; do not treat community engines as product-supported backends.

## Live path (supported)

| Item | Value |
|------|-------|
| Stack | HF Transformers, optional `depth` extra |
| Default weights | Depth Anything V2 **Small** (Apache-2.0) |
| Modes | `relative` (default) / optional `metric_estimated` indoor|outdoor Small heads |
| Honesty | Relative products **never** labeled as meters; metric modes use `depth_kind=metric_estimated` + `unit="m"` |

```bash
uv sync --extra depth
uv run sentry serve --profile jetson --source synthetic
```

Profile `depth_tier: small` aligns with the Small allowlist. Base/Large NC
weights are never default.

## Relative vs metric honesty (do not rebrand)

| Output | `depth_kind` | Unit claim |
|--------|--------------|------------|
| Default relative map | `relative` | No meters — ordinal / relative only |
| Metric Small heads | `metric_estimated` | Explicit estimated meters (`m`) |

**Depth export must not rebrand relative outputs as meters.** Any external
ONNX/TRT pipeline must preserve the same honesty: if the graph is relative,
downstream free-space and APIs stay ordinal / non-metric.

## Community ONNX / TensorRT (links only)

Third-party projects document ONNX and TensorRT conversion for Depth Anything
V2 (see upstream README “deploy” / third-party sections):

- Upstream: [Depth-Anything-V2](https://github.com/DepthAnything/Depth-Anything-V2)
- Community ONNX/TRT converters and engines appear in that ecosystem — **verify
  license, preprocessing, and depth_kind semantics yourself**

Sentry does **not** vendor these converters, does **not** ship prebuilt depth
engines, and does **not** require Jetson in CI for depth.

| Topic | Honest expectation |
|-------|--------------------|
| Product runtime | HF Small remains default |
| Export maturity | Community-only; experimental for makers |
| TensorRT | Build **on-device** if you pursue engines; **never copy** `.engine` across JetPack SKUs |
| Pi / CPU | Depth + detect dual load is **best-effort / lite** — measure on device |

## Deferred (not v1)

- First-class DAV2 ONNX Runtime or TensorRT `InferenceBackend` in Sentry
- Metric-calibrated free-space meters (needs calibration phase)
- Shipping depth `.engine` artifacts in the repo or wheel

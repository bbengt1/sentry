#!/usr/bin/env python3
"""Offline YOLO26 / YOLOE export CLI (EDGE-03).

Thin wrapper around Ultralytics ``model.export``. Not imported by the
``sentry_ai`` runtime package. Default unit tests exercise argparse /
allowlist helpers only — they never call ``model.export`` or download weights.

Requires the detect extra for real export::

    uv sync --extra detect
    uv run python scripts/export/export_yolo.py --weights yolo26n.pt --format onnx

TensorRT ``engine`` builds need NVIDIA GPU + system TensorRT on **that**
machine (prefer on-device Jetson). Do not copy ``.engine`` across SKUs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

# Prefer package allowlist; fall back to the same basenames if import fails
# (script runnable without editable install in some maker setups).
try:
    from sentry_ai.models.cache import KNOWN_WEIGHTS as _KNOWN_WEIGHTS
except ImportError:  # pragma: no cover - package always present in project tests
    _KNOWN_WEIGHTS = frozenset(
        {
            "yolo26n.pt",
            "yolo26s.pt",
            "yolo26m.pt",
            "yoloe-26s-seg.pt",
            "yoloe-26n-seg.pt",
        }
    )

KNOWN_WEIGHTS: frozenset[str] = frozenset(_KNOWN_WEIGHTS)
ALLOWED_FORMATS = frozenset({"onnx", "engine"})


def validate_weights(weights: str) -> str:
    """Return basename if it is a known weight; raise ValueError otherwise.

    Accepts **basename only** — rejects path traversal, absolute paths, and
    nested relative paths (T-07-10).
    """
    if not weights or not str(weights).strip():
        raise ValueError("weights must be a non-empty basename from KNOWN_WEIGHTS")

    name = str(weights).strip()
    # Basename-only: no separators, no parent refs, Path.name must equal input
    if name != Path(name).name:
        raise ValueError(
            f"invalid weights path {weights!r}: use basename only "
            f"(e.g. yolo26n.pt), not directories or absolute paths"
        )
    if ".." in name or name.startswith(".") and name not in KNOWN_WEIGHTS:
        # ".." in basename is always wrong; lone "." rejected via allowlist
        raise ValueError(f"invalid weights path {weights!r}: path traversal rejected")
    if "/" in name or "\\" in name:
        raise ValueError(f"invalid weights path {weights!r}: basename only")
    if name not in KNOWN_WEIGHTS:
        known = ", ".join(sorted(KNOWN_WEIGHTS))
        raise ValueError(
            f"unknown weights {name!r}: must be in KNOWN_WEIGHTS allowlist ({known})"
        )
    return name


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments (testable without running export)."""
    parser = argparse.ArgumentParser(
        prog="export_yolo.py",
        description=(
            "Export YOLO26/YOLOE weights via Ultralytics model.export "
            "(formats: onnx, engine). Offline tool — not used by sentry serve."
        ),
    )
    parser.add_argument(
        "--weights",
        required=True,
        help="Weight basename from KNOWN_WEIGHTS (e.g. yolo26n.pt)",
    )
    parser.add_argument(
        "--format",
        required=True,
        choices=sorted(ALLOWED_FORMATS),
        help="Export format: onnx (portable) or engine (TensorRT, GPU+TRT host)",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Image size for export (default: 640)",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Device for engine export (e.g. 0). Ignored for onnx unless set.",
    )
    parser.add_argument(
        "--simplify",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Simplify ONNX graph (default: true; onnx only)",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def run_export(
    weights: str,
    fmt: str,
    imgsz: int = 640,
    device: str | None = None,
    simplify: bool = True,
) -> str:
    """Call Ultralytics export. Requires detect extra + local weights/cache.

    Returns the path string reported by Ultralytics (or empty string).
    """
    weights = validate_weights(weights)
    fmt = str(fmt).strip().lower()
    if fmt not in ALLOWED_FORMATS:
        raise ValueError(f"unsupported format {fmt!r}: choose onnx or engine")

    try:
        from ultralytics import YOLO, YOLOE
    except ImportError as exc:  # pragma: no cover - exercised on maker machines
        raise SystemExit(
            "ultralytics is required for export. Install with: "
            "uv sync --extra detect"
        ) from exc

    is_yoloe = weights.lower().startswith("yoloe")
    model = YOLOE(weights) if is_yoloe else YOLO(weights)

    kwargs: dict = {"format": fmt, "imgsz": imgsz}
    if fmt == "onnx":
        kwargs["simplify"] = simplify
    if fmt == "engine":
        # FP16-style path when supported; device required for TRT
        kwargs["quantize"] = 16
        if device is not None:
            # Ultralytics accepts int device indices
            try:
                kwargs["device"] = int(device)
            except ValueError:
                kwargs["device"] = device

    result = model.export(**kwargs)
    return str(result) if result is not None else ""


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        weights = validate_weights(args.weights)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        out = run_export(
            weights=weights,
            fmt=args.format,
            imgsz=args.imgsz,
            device=args.device,
            simplify=args.simplify,
        )
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        if exc.code and not isinstance(exc.code, int):
            print(exc.code, file=sys.stderr)
        return code if isinstance(code, int) else 1
    except Exception as exc:  # pragma: no cover - real export failures
        print(f"export failed: {exc}", file=sys.stderr)
        return 1

    if out:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

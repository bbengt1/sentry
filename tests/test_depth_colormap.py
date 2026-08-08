"""DEPTH-03: depth colormap helpers (pure OpenCV, no transformers)."""

from __future__ import annotations

import inspect

import numpy as np

import sentry_ai.models.depth.colormap as colormap_mod
from sentry_ai.models.depth.colormap import blend_depth, colorize_depth


def test_colorize_depth_shape_and_dtype() -> None:
    depth = np.linspace(0.1, 5.0, 48 * 64, dtype=np.float32).reshape(48, 64)
    out = colorize_depth(depth)
    assert out.shape == (48, 64, 3)
    assert out.dtype == np.uint8
    # Input not mutated.
    assert depth.dtype == np.float32
    assert np.isfinite(depth).all()


def test_colorize_depth_constant_map_does_not_crash() -> None:
    depth = np.full((16, 20), 3.14, dtype=np.float32)
    out = colorize_depth(depth)
    assert out.shape == (16, 20, 3)
    assert out.dtype == np.uint8


def test_colorize_depth_uses_turbo_path() -> None:
    source = inspect.getsource(colormap_mod)
    assert "COLORMAP_TURBO" in source
    assert "applyColorMap" in source
    # Never import heavy depth-stack packages.
    assert "import torch" not in source
    assert "from transformers" not in source
    assert "import transformers" not in source


def test_blend_depth_same_shape_as_rgb_and_copies() -> None:
    rgb = np.zeros((40, 50, 3), dtype=np.uint8)
    rgb[5, 5] = (10, 20, 30)
    depth = np.linspace(0.0, 1.0, 40 * 50, dtype=np.float32).reshape(40, 50)
    out = blend_depth(rgb, depth, alpha=0.45)
    assert out is not rgb
    assert out.shape == rgb.shape
    assert out.dtype == np.uint8
    # Original rgb not mutated at sample pixel.
    assert tuple(rgb[5, 5]) == (10, 20, 30)
    # Blend should differ from pure black for non-zero depth variation.
    assert not np.array_equal(out, np.zeros_like(out))


def test_blend_depth_resizes_color_map_on_shape_mismatch() -> None:
    rgb = np.zeros((30, 40, 3), dtype=np.uint8)
    depth = np.linspace(0.0, 2.0, 10 * 12, dtype=np.float32).reshape(10, 12)
    out = blend_depth(rgb, depth, alpha=0.5)
    assert out.shape == (30, 40, 3)

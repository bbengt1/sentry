# Phase 18: Docs + Synthetic CI Polish - Pattern Map

**Mapped:** 2026-08-14
**Files analyzed:** 14 (docs + keyword/CI tests)
**Analogs found:** 14 / 14

## File Classification

| New/Modified File | Role | Closest Analog | Match |
|-------------------|------|----------------|-------|
| `docs/calibration.md` | operator hub | `docs/edge-serve.md` + `docs/desktop-gpu.md` | role-match |
| `docs/perception-frame.md` | wire contract | same file (kind triad already; FS units stale) | exact |
| `docs/safety-and-privacy.md` | non-autonomy | same file (FSD-negative is good; FS always-ordinal stale) | exact |
| `README.md` | root hub | same file (Phase 12 edge honesty) | exact |
| `docs/README.md` | start-here | same file (edge-serve row) | exact |
| `docs/api-reference.md` | REST table | same file (depth/OV tables) | exact |
| `docs/cli.md` | flags | same file (`--no-ui` table) | exact |
| `docs/configuration.md` | env/cache | same file (`SENTRY_MODEL_CACHE`) | exact |
| `docs/architecture.md` | spine | same file (DepthLoop row; missing calib plug-in) | exact |
| `docs/desktop-gpu.md` | maker path | same file (expected stages) | exact |
| `CHANGELOG.md` | Unreleased | same file (v0.2 Unreleased pattern) | exact |
| `tests/test_calibration_docs.py` | keyword | `tests/test_edge_serve_docs.py` | role-match |
| `tests/test_safety_docs.py` | keyword extend | same file | exact |
| `tests/test_v03_honesty_matrix.py` | inventory | `tests/test_edge_ci_workflow.py` module docstring | role-match |
| `tests/test_edge_ci_workflow.py` | CI lock | same file (already compliant) | exact |

**Out of phase:** `src/sentry_ai/**` product modules, DetectionLoop, FrameBus, ORT-TRT, `kind_for_mode`, wizard HTML, YAML store logic, `pyproject` version, REQUIREMENTS checkbox closeout.

---

## Pattern Assignments

### `docs/calibration.md` — NEW (18-01)

**Analog:** `docs/edge-serve.md` (thin numbered hub + links, no recipe-book dump).

**Target shape (min ~60 lines):**

1. Title: maker calibration — **approximate monocular metric scale, not vehicle-grade**
2. Numbered flow: install depth extra → `sentry serve` → Live Preview wizard → known-distance samples → Fit preview → **Apply** or **Cancel** → optional Save / `persist:true`
3. Honesty triad table (relative never m; estimated ≠ calibrated; calibrated+m only when applied+valid; draft never calibrated)
4. Free-space: `units="m"` iff calibrated + 1.5/3.0 m cuts; else ordinal; optional `distance_m`
5. Persist: `$SENTRY_MODEL_CACHE/calibration/{safe_id}.yaml` (or `default_cache_root`); `SENTRY_CALIBRATION_DIR`; `--calibration-file`
6. Cancel = draft-only; Clear deletes YAML
7. Persist status `none\|applied\|ignored_mismatch\|error` ≠ `depth.kind`
8. Fingerprint refuse (camera_id / mode / model; W×H when both known)
9. Links: perception-frame, safety, api, cli, configuration, desktop-gpu

**Do not:** claim FSD / precise meters / autonomy; document `~/.config` JSON; invent FPS; require a physical room in CI.

---

### Keyword tests — NEW/EXTEND (18-01)

**Analog:** `tests/test_edge_serve_docs.py` + `tests/test_export_docs.py` `Path.read_text` asserts.

```python
# tests/test_calibration_docs.py
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_STALE = (
    "always ordinal",
    "v1 always **ordinal**",
    "v1 always ordinal",
    "precise meters",
    "precise metre",
)
# FSD / autonomous as *claims* (not "not FSD" / "not autonomous"):
# forbid bare product claims; allow "not … FSD" / "not an autonomous"

def _hub_texts() -> dict[str, str]:
    paths = [
        "docs/calibration.md",
        "docs/perception-frame.md",
        "docs/safety-and-privacy.md",
        "README.md",
        "docs/README.md",
        "docs/api-reference.md",
        "docs/cli.md",
        "docs/configuration.md",
        "docs/architecture.md",
        "docs/desktop-gpu.md",
    ]
    return {p: (REPO_ROOT / p).read_text(encoding="utf-8") for p in paths}
```

Required on `docs/calibration.md`: wizard, Apply, Cancel, Clear, `metric_calibrated`, persist path (`SENTRY_MODEL_CACHE` or `calibration/`), `ignored_mismatch` or fingerprint, “not vehicle-grade” or “approximate”, monocular, 1.5 / 3.0 or free-space meters-when-calibrated.

README + `docs/README.md` must link `docs/calibration.md` or `calibration.md`.

Extend `tests/test_safety_docs.py`: keep existing non-autonomy asserts; add “always ordinal” forbid on the safety page; require calibrated-meters-only-when-applied language **or** a link to `calibration.md`.

---

### Hub refresh snippets (18-01)

| File | Touch |
|------|-------|
| `perception-frame.md` | Depth table: calibrated = applied+valid meters. FS: `units` m iff calibrated; optional `distance_m` |
| `safety-and-privacy.md` | FS ordinal **unless** calibrated; still not interlock; link calibration hub; keep “not FSD” |
| `README.md` | Replace “v1 always ordinal”; add calibration row + short wizard pointer |
| `docs/README.md` | Start-here row; versioning note v0.3 UX / package 0.1.0 |
| `api-reference.md` | Calibration REST table + status persist fields |
| `cli.md` | `--calibration-file`; banner `calibration:` |
| `configuration.md` | `SENTRY_CALIBRATION_DIR`; cache `calibration/*.yaml` |
| `architecture.md` | DepthLoop `apply_map` plug-in; persist I/O in `config/calibration_store.py` |
| `desktop-gpu.md` | Expected stages: wizard optional; FS meters when calibrated |
| `CHANGELOG.md` | `## [Unreleased]` Added/Changed for operator calibration docs; **no** 0.1.0 rewrite; **no** version bump |

---

### `tests/test_v03_honesty_matrix.py` — NEW (18-02)

**Analog:** `test_edge_ci_workflow.py` living docstring (EDGE-CI-01 matrix) — **verify-only**, no product code.

**Target:** module docstring table mapping OPS-03 (fit / apply / honesty / persist) → existing files. Tests:

1. Each inventoried path exists under `tests/`.
2. Re-assert `ci.yml` contract (or import/call the existing EDGE-CI-02 asserts — prefer **do not duplicate**; a single test that `test_edge_ci_workflow.py` still encodes `uv sync --extra dev` and forbids `--extra depth` is enough).
3. Optional: `pytest --collect-only` on the inventory list returns >0 items (no new cases).

**Do not:** add FakeDepthWorker product tests; load HF weights; change `ci.yml` unless a lock fails (expected: leave byte-identical).

---

## Shared Patterns

1. **Keyword-locked docs** — Phase 12 `Path.read_text` (TDD RED then GREEN).
2. **Thin hub + links** — `edge-serve.md`; do not dump REST schemas twice.
3. **CI static lock** — `test_edge_ci_workflow.py`; 18-02 extends inventory, does not add extras.
4. **Unreleased changelog** — Phase 12; do not bump package 0.1.0.
5. **Zero new dependencies / frozen spine.**

---

## Metadata

**Analog search scope:** Phase 12 docs/CI plans, `docs/edge-serve.md`, `tests/test_edge_serve_docs.py`, `tests/test_safety_docs.py`, `tests/test_edge_ci_workflow.py`, v0.3 calibration test modules listed in RESEARCH.

**Key planner constraints:** docs + tests only; STACK persist path in prose; honesty triad; Cancel ≠ Clear; no product creep.

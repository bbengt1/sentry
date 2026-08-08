"""Open-vocab API: config + one-shot run arm (OVD-01/02).

Handlers only mutate worker prompt/conf and loop mode/arm flags.
They never open cameras or run model inference (first-run weight load
stays on the OpenVocabLoop thread).
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

router = APIRouter()

MAX_CLASSES = 32
MAX_CLASS_LEN = 64


class OpenVocabConfigUpdate(BaseModel):
    """Runtime open-vocab config. Extra fields rejected (T-06-10)."""

    model_config = ConfigDict(extra="forbid")

    prompt: str | None = None
    classes: list[str] | None = None
    mode: Literal["off", "on_demand", "continuous"] | None = None
    conf: float | None = Field(default=None, ge=0.0, le=1.0)
    every_n: int | None = Field(default=None, ge=1, le=60)

    @model_validator(mode="after")
    def _at_least_one_field(self) -> OpenVocabConfigUpdate:
        if (
            self.prompt is None
            and self.classes is None
            and self.mode is None
            and self.conf is None
            and self.every_n is None
        ):
            raise ValueError("at least one field required")
        return self


class OpenVocabRunBody(BaseModel):
    """Optional body for POST /api/open-vocab/run."""

    model_config = ConfigDict(extra="forbid")

    prompt: str | None = None
    classes: list[str] | None = None
    conf: float | None = Field(default=None, ge=0.0, le=1.0)


def _open_vocab_worker(request: Request) -> Any:
    return getattr(request.app.state, "open_vocab_worker", None)


def _open_vocab_loop(request: Request) -> Any:
    return getattr(request.app.state, "open_vocab_loop", None)


def _require_worker(request: Request) -> Any:
    worker = _open_vocab_worker(request)
    if worker is None:
        raise HTTPException(
            status_code=503,
            detail="open-vocab worker not available",
        )
    return worker


def _require_loop(request: Request) -> Any:
    loop = _open_vocab_loop(request)
    if loop is None:
        raise HTTPException(
            status_code=503,
            detail="open-vocab loop not available",
        )
    return loop


def _parse_prompt_classes(
    prompt: str | None,
    classes: list[str] | None,
) -> list[str] | None:
    """Normalize prompt string or classes list; enforce caps.

    Returns None when neither prompt nor classes provided.
    Raises HTTPException 422 on validation failure.
    """
    if prompt is None and classes is None:
        return None

    raw: list[str] = []
    if classes is not None:
        raw.extend(str(c) for c in classes)
    if prompt is not None:
        # Comma-separated classes from free-text prompt.
        parts = [p.strip() for p in str(prompt).split(",")]
        raw.extend(parts)

    cleaned: list[str] = []
    for item in raw:
        text = item.strip()
        if not text:
            continue
        if len(text) > MAX_CLASS_LEN:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"class name exceeds {MAX_CLASS_LEN} characters: "
                    f"{text[:20]!r}..."
                ),
            )
        cleaned.append(text)

    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for c in cleaned:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    if len(unique) > MAX_CLASSES:
        raise HTTPException(
            status_code=422,
            detail=f"at most {MAX_CLASSES} classes allowed, got {len(unique)}",
        )
    return unique


def _config_snapshot(worker: Any, loop: Any) -> dict[str, Any]:
    classes = []
    get_classes = getattr(worker, "get_prompt_classes", None)
    if callable(get_classes):
        classes = list(get_classes())
    conf = float(worker.get_conf()) if hasattr(worker, "get_conf") else None
    mode = loop.get_mode() if hasattr(loop, "get_mode") else "off"
    every_n = loop.get_every_n() if hasattr(loop, "get_every_n") else 3
    payload: dict[str, Any] = {
        "mode": mode,
        "classes": classes,
        "prompt": ", ".join(classes) if classes else "",
        "conf": conf,
        "every_n": every_n,
    }
    name = getattr(worker, "name", None)
    if name is not None:
        payload["model"] = str(name)
    return payload


@router.get("/api/open-vocab/config")
async def get_open_vocab_config(request: Request) -> dict[str, Any]:
    """Return current open-vocab mode, classes, conf, every_n."""
    worker = _require_worker(request)
    loop = _require_loop(request)
    return _config_snapshot(worker, loop)


@router.patch("/api/open-vocab/config")
async def patch_open_vocab_config(
    body: OpenVocabConfigUpdate,
    request: Request,
) -> dict[str, Any]:
    """Update prompt/mode/conf/every_n without running inference."""
    worker = _require_worker(request)
    loop = _require_loop(request)

    classes = _parse_prompt_classes(body.prompt, body.classes)
    if classes is not None:
        worker.set_prompt_classes(classes)

    if body.conf is not None:
        worker.set_conf(body.conf)

    if body.every_n is not None:
        loop.set_every_n(body.every_n)

    if body.mode is not None:
        loop.set_mode(body.mode)

    return _config_snapshot(worker, loop)


@router.post("/api/open-vocab/run")
async def post_open_vocab_run(
    request: Request,
    body: OpenVocabRunBody | None = None,
) -> dict[str, Any]:
    """Arm one-shot on_demand run. Does not call worker.process on request path."""
    worker = _require_worker(request)
    loop = _require_loop(request)

    payload = body if body is not None else OpenVocabRunBody()
    classes = _parse_prompt_classes(payload.prompt, payload.classes)
    if classes is not None:
        worker.set_prompt_classes(classes)
    if payload.conf is not None:
        worker.set_conf(payload.conf)

    # Switch to on_demand and arm — process happens on loop thread.
    loop.set_mode("on_demand")
    loop.arm()

    snap = _config_snapshot(worker, loop)
    snap["armed"] = True
    return snap

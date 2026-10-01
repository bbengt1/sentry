"""CR-004 / CR-005: cross-site POSTs, foreign WebSocket origins, rebinding Host."""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketDenialResponse

from sentry_ai.api.app import create_app
from sentry_ai.api.browser_guard import resolve_guard
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.cli import app as cli_app
from sentry_ai.control.calibration_state import CalibrationState
from sentry_ai.schemas.calibration import CalibrationSample
from sentry_ai.sources.synthetic import SyntheticSource
from tests.cli_helpers import cli_help_output

_CLEAR = "/api/depth/calibration/clear"
_CANCEL = "/api/depth/calibration/cancel"
_COMPUTE = "/api/depth/calibration/compute"
_APPLY = "/api/depth/calibration/apply"
_ONLINE = "/api/depth/calibration/online"


def _app(
    *,
    bind: str = "127.0.0.1:8000",
    allowed_hosts: list[str] | None = None,
    allowed_origins: list[str] | None = None,
    calibration: bool = True,
):
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    state = CalibrationState() if calibration else None
    app = create_app(
        bus=bus,
        capture_loop=loop,
        bind=bind,
        calibration_state=state,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )
    return app, loop, state


def _client(app, base_url: str = "http://127.0.0.1:8000") -> TestClient:
    return TestClient(app, base_url=base_url)


def test_cr004_cross_site_simple_post_is_forbidden() -> None:
    """Form posts from a foreign Origin must not reach calibration handlers."""
    app, loop, state = _app()
    state.add_draft_sample(CalibrationSample(known_meters=1.5, observed_raw=2.0))
    headers = {
        "Origin": "https://evil.example",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    try:
        with _client(app) as client:
            for path in (_CLEAR, _CANCEL, _COMPUTE, _APPLY):
                resp = client.post(path, content=b"x=1", headers=headers)
                assert resp.status_code == 403, path
                assert resp.json()["detail"] == "origin_not_allowed"
        assert state.snapshot().draft_sample_count == 1
        assert state.is_applied() is False
    finally:
        loop.stop()


def test_cr004_text_plain_post_is_forbidden() -> None:
    app, loop, _state = _app()
    try:
        with _client(app) as client:
            resp = client.post(
                _CLEAR,
                content=b"clear",
                headers={
                    "Origin": "https://evil.example",
                    "Content-Type": "text/plain",
                },
            )
            assert resp.status_code == 403
            assert resp.json()["detail"] == "origin_not_allowed"
    finally:
        loop.stop()


def test_cr004_form_without_origin_is_forbidden() -> None:
    """A simple form body is refused even when Origin was stripped."""
    app, loop, _state = _app()
    try:
        with _client(app) as client:
            resp = client.post(
                _CLEAR,
                content=b"x=1",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            assert resp.status_code == 403
            assert resp.json()["detail"] == "content_type_not_allowed"
    finally:
        loop.stop()


def test_cr004_cross_site_fetch_site_is_forbidden() -> None:
    app, loop, _state = _app()
    try:
        with _client(app) as client:
            resp = client.post(
                _CANCEL,
                json={},
                headers={
                    "Origin": "http://127.0.0.1:8000",
                    "Sec-Fetch-Site": "cross-site",
                },
            )
            assert resp.status_code == 403
            assert resp.json()["detail"] == "cross_site_request"
    finally:
        loop.stop()


def test_cr004_same_origin_json_reaches_handler() -> None:
    """Live Preview origin + JSON still gets the handler's own status code."""
    app, loop, _state = _app()
    try:
        with _client(app) as client:
            resp = client.post(
                _APPLY,
                json={},
                headers={"Origin": "http://127.0.0.1:8000"},
            )
            # No draft staged: the handler runs and refuses the apply.
            assert resp.status_code == 422
            assert "draft" in str(resp.json()["detail"])
            cancel = client.post(
                _CANCEL,
                json={},
                headers={
                    "Origin": "http://127.0.0.1:8000",
                    "Sec-Fetch-Site": "same-origin",
                },
            )
            assert cancel.status_code == 200
    finally:
        loop.stop()


def test_cr004_no_origin_client_can_post() -> None:
    """curl / scripts omit Origin and must keep the documented REST flow."""
    app, loop, _state = _app()
    try:
        with _client(app) as client:
            assert client.post(_CANCEL).status_code == 200
            assert client.post(_CLEAR).status_code == 200
            compute = client.post(
                _COMPUTE,
                content=b"{}",
                headers={"Content-Type": "application/json"},
            )
            # Guard lets it through; the fitter then rejects empty samples.
            assert compute.status_code == 422
    finally:
        loop.stop()


def test_cr004_localhost_origin_matches_localhost_host() -> None:
    app, loop, _state = _app()
    try:
        with _client(app, "http://localhost:8000") as client:
            resp = client.post(
                _CANCEL,
                json={},
                headers={"Origin": "http://localhost:8000"},
            )
            assert resp.status_code == 200
    finally:
        loop.stop()


def test_cr004_root_is_not_frameable() -> None:
    app, loop, _state = _app()
    try:
        with _client(app) as client:
            resp = client.get("/")
            assert resp.status_code == 200
            assert resp.headers["x-frame-options"] == "DENY"
            assert "frame-ancestors 'none'" in resp.headers["content-security-policy"]
            status = client.get("/api/status")
            assert status.status_code == 200
            assert status.headers["x-frame-options"] == "DENY"
    finally:
        loop.stop()


def test_cr004_online_post_is_covered() -> None:
    """Foreign Origin is refused; a no-Origin JSON body reaches the online handler.

    This app has calibration state and nothing applied, so ``{"enabled": true}``
    is the handler's 409 ``online_requires_applied``, not a routing miss.
    """
    app, loop, state = _app()
    try:
        with _client(app) as client:
            blocked = client.post(
                _ONLINE,
                json={"enabled": True},
                headers={"Origin": "https://evil.example"},
            )
            assert blocked.status_code == 403
            assert blocked.json()["detail"] == "origin_not_allowed"
            assert state.is_online() is False
            reached = client.post(_ONLINE, json={"enabled": True})
            assert reached.status_code == 409
            assert reached.json()["detail"] == "online_requires_applied"
            assert state.is_online() is False
    finally:
        loop.stop()


def test_cr005_foreign_origin_websocket_is_forbidden() -> None:
    app, loop, _state = _app()
    try:
        with _client(app) as client:
            with pytest.raises(WebSocketDenialResponse) as exc_info:
                with client.websocket_connect(
                    "/v1/stream",
                    headers={"origin": "https://evil.example"},
                ):
                    pass
            denial = exc_info.value
            assert denial.status_code == 403
            assert denial.json()["detail"] == "origin_not_allowed"
    finally:
        loop.stop()


def test_cr005_rebinding_host_is_forbidden() -> None:
    app, loop, _state = _app()
    try:
        with _client(app, "http://evil.example") as client:
            resp = client.get("/api/status", headers={"Origin": "http://evil.example"})
            assert resp.status_code == 403
            assert resp.json()["detail"] == "host_not_allowed"
            post = client.post(_CLEAR, json={})
            assert post.status_code == 403
            assert post.json()["detail"] == "host_not_allowed"
    finally:
        loop.stop()


def test_cr005_foreign_host_websocket_is_forbidden() -> None:
    app, loop, _state = _app()
    try:
        with _client(app) as client:
            with pytest.raises(WebSocketDenialResponse) as exc_info:
                with client.websocket_connect(
                    "/v1/stream",
                    headers={
                        "host": "evil.example",
                        "origin": "http://evil.example",
                    },
                ):
                    pass
            assert exc_info.value.status_code == 403
            assert exc_info.value.json()["detail"] == "host_not_allowed"
    finally:
        loop.stop()


def test_cr005_websocket_without_denial_extension_uses_close_code() -> None:
    """Servers that cannot write an HTTP denial body close with 1008 + reason."""
    app, loop, _state = _app()

    async def _handshake() -> list[dict]:
        sent: list[dict] = []

        async def receive() -> dict:
            return {"type": "websocket.connect"}

        async def send(message: dict) -> None:
            sent.append(message)

        scope = {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "scheme": "ws",
            "path": "/v1/stream",
            "raw_path": b"/v1/stream",
            "query_string": b"",
            "headers": [
                (b"host", b"127.0.0.1:8000"),
                (b"origin", b"https://evil.example"),
            ],
            "client": ("127.0.0.1", 1234),
            "server": ("127.0.0.1", 8000),
            "subprotocols": [],
        }
        await app(scope, receive, send)
        return sent

    try:
        sent = asyncio.run(_handshake())
    finally:
        loop.stop()
    assert sent[0]["type"] == "websocket.close"
    assert sent[0]["code"] == 1008
    assert sent[0]["reason"] == "origin_not_allowed"


def test_cr005_no_origin_websocket_is_accepted() -> None:
    app, loop, _state = _app()
    try:
        with _client(app) as client:
            with client.websocket_connect("/v1/stream") as ws:
                ws.close()
    finally:
        loop.stop()


def test_cr005_same_origin_websocket_is_accepted() -> None:
    app, loop, _state = _app()
    try:
        with _client(app) as client:
            with client.websocket_connect(
                "/v1/stream",
                headers={
                    "host": "127.0.0.1:8000",
                    "origin": "http://127.0.0.1:8000",
                },
            ) as ws:
                ws.close()
    finally:
        loop.stop()


def test_explicit_lan_bind_serves_that_address() -> None:
    app, loop, _state = _app(bind="192.168.1.20:8000")
    try:
        with _client(app, "http://192.168.1.20:8000") as client:
            assert client.get("/api/status").status_code == 200
            resp = client.post(
                _CANCEL,
                json={},
                headers={"Origin": "http://192.168.1.20:8000"},
            )
            assert resp.status_code == 200
        with _client(app, "http://10.0.0.8:8000") as client:
            denied = client.get("/api/status")
            assert denied.status_code == 403
            assert denied.json()["detail"] == "host_not_allowed"
    finally:
        loop.stop()


def test_wildcard_bind_allows_ip_literal_not_dns_name() -> None:
    app, loop, _state = _app(bind="0.0.0.0:8000")
    try:
        with _client(app, "http://10.1.2.3:8000") as client:
            assert client.get("/").status_code == 200
            resp = client.post(
                _CANCEL,
                json={},
                headers={"Origin": "http://10.1.2.3:8000"},
            )
            assert resp.status_code == 200
        with _client(app, "http://evil.example:8000") as client:
            denied = client.get("/api/status")
            assert denied.status_code == 403
            assert denied.json()["detail"] == "host_not_allowed"
    finally:
        loop.stop()


def test_allowed_host_and_origin_flags() -> None:
    app, loop, _state = _app(
        bind="0.0.0.0:8000",
        allowed_hosts=["robot.local"],
        allowed_origins=["http://127.0.0.1:3000"],
    )
    try:
        with _client(app, "http://robot.local:8000") as client:
            assert client.get("/api/status").status_code == 200
            same = client.post(
                _CANCEL,
                json={},
                headers={"Origin": "http://robot.local:8000"},
            )
            assert same.status_code == 200
        with _client(app, "http://127.0.0.1:8000") as client:
            extra = client.post(
                _CANCEL,
                json={},
                headers={"Origin": "http://127.0.0.1:3000"},
            )
            assert extra.status_code == 200
            other_port = client.post(
                _CANCEL,
                json={},
                headers={"Origin": "http://127.0.0.1:9999"},
            )
            assert other_port.status_code == 403
            assert other_port.json()["detail"] == "origin_not_allowed"
    finally:
        loop.stop()


def test_asgi_testclient_default_host_still_allowed() -> None:
    app, loop, _state = _app()
    try:
        with TestClient(app) as client:
            assert client.get("/api/status").status_code == 200
            assert client.post(_CLEAR).status_code == 200
    finally:
        loop.stop()


def test_invalid_allowed_origin_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid allowed origin"):
        resolve_guard(bind="127.0.0.1:8000", extra_origins=["not a url"])


def test_cli_help_documents_allowed_host_and_origin() -> None:
    out = cli_help_output(cli_app, "serve", "--help")
    assert "--allowed-host" in out
    assert "--allowed-origin" in out


def test_cli_rejects_invalid_allowed_origin_before_serve() -> None:
    from typer.testing import CliRunner

    result = CliRunner().invoke(
        cli_app,
        ["serve", "--source", "synthetic", "--allowed-origin", "not-a-url"],
    )
    assert result.exit_code == 1
    assert "invalid allowed origin" in result.output


def test_live_preview_posts_json_content_type() -> None:
    from pathlib import Path

    html = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "sentry_ai"
        / "ui"
        / "static"
        / "index.html"
    ).read_text(encoding="utf-8")
    assert 'headers: { "Content-Type": "application/json" }' in html
    start = html.index("function postCalib")
    body = html[start : html.index("function onCalibHttp")]
    assert "JSON.stringify" in body


def test_docs_describe_browser_guard() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    cli = (root / "docs" / "cli.md").read_text(encoding="utf-8")
    safety = (root / "docs" / "safety-and-privacy.md").read_text(encoding="utf-8")
    api = (root / "docs" / "api-reference.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    for text in (cli, safety, api, readme):
        assert "--allowed-host" in text
        assert "--allowed-origin" in text
    assert "host_not_allowed" in safety
    assert "origin_not_allowed" in api


def test_refusal_body_does_not_echo_origin() -> None:
    app, loop, _state = _app()
    hostile = "https://evil.example/should-not-appear"
    try:
        with _client(app) as client:
            resp = client.post(
                _CLEAR,
                content=b"x",
                headers={"Origin": hostile, "Content-Type": "text/plain"},
            )
            assert resp.status_code == 403
            assert hostile not in resp.text
            assert "evil.example" not in resp.text
            payload = json.loads(resp.text)
            assert payload == {"detail": "origin_not_allowed"}
    finally:
        loop.stop()

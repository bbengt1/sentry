"""Host, Origin, and content-type guard for the local serve process.

``sentry serve`` has no session and no CORS grant. Browsers can still
change state with a "simple" POST (form or ``text/plain``) and can read
``/v1/stream`` because WebSocket responses are not covered by CORS.
A foreign ``Host`` also makes a DNS-rebinding page same-origin with this
process.

The guard is mounted once in ``create_app`` so every current and future
route is covered, including ``POST /api/depth/calibration/online`` when
that handler lands. Refusal bodies use fixed tokens and never echo the
``Origin`` or ``Host`` value.
"""

from __future__ import annotations

import ipaddress
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Close code used when the server cannot send an HTTP denial body.
WS_POLICY_CLOSE = 1008

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_WILDCARD_BINDS = frozenset({"0.0.0.0", "::", "::0"})
_FRAME_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-frame-options", b"DENY"),
    (b"content-security-policy", b"frame-ancestors 'none'"),
)

REASON_HOST = "host_not_allowed"
REASON_ORIGIN = "origin_not_allowed"
REASON_CROSS_SITE = "cross_site_request"
REASON_CONTENT_TYPE = "content_type_not_allowed"


@dataclass(frozen=True)
class GuardConfig:
    """Allowlists derived from the bind address plus operator overrides."""

    bind_host: str
    wildcard_bind: bool
    extra_hosts: frozenset[str]
    extra_origins: frozenset[str]


def host_from_bind(bind: str) -> str:
    """Return the hostname portion of a ``host:port`` bind string."""
    parsed = split_host_header(bind.strip())
    if parsed is None:
        return normalize_hostname(bind)
    return normalize_hostname(parsed[0])


def resolve_guard(
    *,
    bind: str,
    extra_hosts: Iterable[str] | None = None,
    extra_origins: Iterable[str] | None = None,
) -> GuardConfig:
    """Build the guard policy. Invalid operator overrides raise ``ValueError``."""
    bind_host = host_from_bind(bind)
    hosts: set[str] = set()
    for raw in extra_hosts or ():
        name = _normalize_extra_host(raw)
        if name:
            hosts.add(name)
    origins: set[str] = set()
    for raw in extra_origins or ():
        text = raw.strip()
        if not text:
            continue
        normalized = normalize_origin(text)
        if normalized is None:
            raise ValueError(f"invalid allowed origin: {text!r}")
        origins.add(normalized)
    return GuardConfig(
        bind_host=bind_host,
        wildcard_bind=bind_host in _WILDCARD_BINDS,
        extra_hosts=frozenset(hosts),
        extra_origins=frozenset(origins),
    )


def normalize_hostname(host: str) -> str:
    """Lowercase a hostname and decode IDNA so flags match the Host header."""
    name = host.strip().lower().rstrip(".")
    if name.startswith("[") and name.endswith("]"):
        name = name[1:-1]
    try:
        name = name.encode("idna").decode("ascii")
    except UnicodeError:
        return name
    return name


def normalize_origin(value: str) -> str | None:
    """Return ``scheme://host:port`` or ``None`` when ``value`` is not an origin."""
    raw = value.strip()
    if not raw or raw.lower() == "null":
        return None
    parts = urlsplit(raw)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return None
    if parts.path not in {"", "/"} or parts.query or parts.fragment or parts.username:
        return None
    host = normalize_hostname(parts.hostname)
    if not host:
        return None
    port = parts.port
    if port is None:
        port = 443 if parts.scheme == "https" else 80
    return f"{parts.scheme}://{_format_host(host)}:{port}"


def split_host_header(value: str) -> tuple[str, int | None] | None:
    """Split a Host header or bind string into hostname and optional port."""
    raw = value.strip()
    if not raw:
        return None
    if raw.startswith("["):
        end = raw.find("]")
        if end < 0:
            return None
        host = raw[1:end]
        rest = raw[end + 1 :]
        if not rest:
            return host, None
        if rest.startswith(":") and rest[1:].isdigit():
            return host, int(rest[1:])
        return None
    if raw.count(":") == 1:
        host, port_s = raw.rsplit(":", 1)
        if not host or not port_s.isdigit():
            return None
        return host, int(port_s)
    if ":" in raw:
        host, port_s = raw.rsplit(":", 1)
        if port_s.isdigit():
            try:
                ipaddress.ip_address(host)
            except ValueError:
                return None
            return host, int(port_s)
        try:
            ipaddress.ip_address(raw)
        except ValueError:
            return None
        return raw, None
    return raw, None


def refusal_reason(scope: Scope, config: GuardConfig) -> str | None:
    """Return a fixed refusal token, or ``None`` when the request may proceed."""
    headers = _header_map(scope)
    host_raw = headers.get("host")
    parsed = split_host_header(host_raw) if host_raw else None
    if parsed is None:
        return REASON_HOST
    hostname, port = parsed
    testclient = _is_testclient(scope)
    if not hostname_allowed(
        hostname,
        config=config,
        testclient=testclient,
    ):
        return REASON_HOST

    kind = scope.get("type")
    method = str(scope.get("method", "GET")).upper()
    mutating = kind == "websocket" or (kind == "http" and method in _UNSAFE_METHODS)
    if not mutating:
        return None

    for site in _header_values(scope, "sec-fetch-site"):
        if site.strip().lower() == "cross-site":
            return REASON_CROSS_SITE

    origins = [item for item in _header_values(scope, "origin") if item.strip()]
    if len(origins) > 1:
        return REASON_ORIGIN
    if origins and not origin_allowed(
        origins[0],
        request_host=hostname,
        request_port=port,
        config=config,
        testclient=testclient,
    ):
        return REASON_ORIGIN

    if kind == "http":
        types = _header_values(scope, "content-type")
        if not _content_types_allowed(types):
            return REASON_CONTENT_TYPE
    return None


def hostname_allowed(
    hostname: str,
    *,
    config: GuardConfig,
    testclient: bool,
) -> bool:
    """True when ``hostname`` is loopback, the bind address, or an override.

    A wildcard bind (``0.0.0.0`` / ``::``) also allows IP literals so the
    Live Preview works at the LAN address the operator opened. DNS names
    stay denied unless listed in ``--allowed-host``, which is what stops a
    rebinding page from becoming same-origin.
    """
    name = normalize_hostname(hostname)
    if not name:
        return False
    if name in _LOOPBACK_HOSTS or name in config.extra_hosts:
        return True
    if not config.wildcard_bind and name == config.bind_host:
        return True
    if config.wildcard_bind and _is_ip(name):
        return True
    # Starlette's TestClient is the only peer that presents this name.
    # A browser cannot choose the ASGI client tuple.
    return bool(testclient and name == "testserver")


def origin_allowed(
    origin: str,
    *,
    request_host: str,
    request_port: int | None,
    config: GuardConfig,
    testclient: bool,
) -> bool:
    """True for an operator override or the same HTTP origin as this response.

    Missing ``Origin`` is handled by the caller (non-browser clients).
    ``Origin: null`` and cross-scheme origins are refused unless listed.
    """
    if origin.strip().lower() == "null":
        return False
    normalized = normalize_origin(origin)
    if normalized is None:
        return False
    if normalized in config.extra_origins:
        return True
    parts = urlsplit(origin.strip())
    # The bundled server speaks HTTP. An https page is a different origin
    # unless the operator listed it.
    if parts.scheme != "http" or not parts.hostname:
        return False
    origin_host = normalize_hostname(parts.hostname)
    origin_port = parts.port if parts.port is not None else 80
    if not hostname_allowed(origin_host, config=config, testclient=testclient):
        return False
    if origin_host != normalize_hostname(request_host):
        return False
    if request_port is None:
        return origin_port == 80
    return origin_port == request_port


class BrowserGuardMiddleware:
    """Reject foreign hosts, cross-site mutations, and foreign socket origins."""

    def __init__(self, app: ASGIApp, *, config: GuardConfig) -> None:
        self.app = app
        self.config = config

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        kind = scope.get("type")
        if kind == "http":
            await self._http(scope, receive, send)
            return
        if kind == "websocket":
            await self._websocket(scope, receive, send)
            return
        await self.app(scope, receive, send)

    async def _http(self, scope: Scope, receive: Receive, send: Send) -> None:
        reason = refusal_reason(scope, self.config)
        if reason is not None:
            await _send_http_json(send, 403, reason)
            return

        async def send_framed(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = _with_frame_headers(list(message.get("headers") or []))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_framed)

    async def _websocket(self, scope: Scope, receive: Receive, send: Send) -> None:
        reason = refusal_reason(scope, self.config)
        if reason is None:
            await self.app(scope, receive, send)
            return
        extensions = scope.get("extensions") or {}
        if "websocket.http.response" in extensions:
            await _send_ws_denial(send, reason)
            return
        await send(
            {
                "type": "websocket.close",
                "code": WS_POLICY_CLOSE,
                "reason": reason,
            }
        )


def _normalize_extra_host(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    parsed = split_host_header(text)
    if parsed is None:
        raise ValueError(f"invalid allowed host: {text!r}")
    name = normalize_hostname(parsed[0])
    if not name or any(ch in name for ch in " /\\"):
        raise ValueError(f"invalid allowed host: {text!r}")
    return name


def _format_host(host: str) -> str:
    if ":" in host:
        return f"[{host}]"
    return host


def _is_ip(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return True


def _is_testclient(scope: Scope) -> bool:
    client = scope.get("client")
    if not isinstance(client, (tuple, list)) or not client:
        return False
    return str(client[0]) == "testclient"


def _header_map(scope: Scope) -> Mapping[str, str]:
    found: dict[str, str] = {}
    for key, value in scope.get("headers") or ():
        name = key.decode("latin-1").lower()
        if name not in found:
            found[name] = value.decode("latin-1")
    return found


def _header_values(scope: Scope, name: str) -> list[str]:
    target = name.lower().encode("ascii")
    values: list[str] = []
    for key, value in scope.get("headers") or ():
        if key.lower() == target:
            values.append(value.decode("latin-1"))
    return values


def _content_types_allowed(values: list[str]) -> bool:
    if not values:
        return True
    for value in values:
        if not value.strip():
            continue
        media = value.split(";", 1)[0].strip().lower()
        if media != "application/json":
            return False
    return True


def _with_frame_headers(
    headers: list[tuple[bytes, bytes]],
) -> list[tuple[bytes, bytes]]:
    present = {key.lower() for key, _ in headers}
    for key, value in _FRAME_HEADERS:
        if key not in present:
            headers.append((key, value))
    return headers


async def _send_http_json(send: Send, status: int, reason: str) -> None:
    body = json.dumps({"detail": reason}).encode("utf-8")
    headers = _with_frame_headers(
        [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
        ]
    )
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


async def _send_ws_denial(send: Send, reason: str) -> None:
    body = json.dumps({"detail": reason}).encode("utf-8")
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    await send(
        {
            "type": "websocket.http.response.start",
            "status": 403,
            "headers": headers,
        }
    )
    await send({"type": "websocket.http.response.body", "body": body})

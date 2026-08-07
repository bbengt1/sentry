# Camera sources

Sentry AI Phase 2 capture adapters: USB, file, synthetic, and RTSP (OpenCV
best-effort). Sources publish to the keep-latest **Frame Bus** only — the web
preview never opens cameras.

## Source matrix

| Source | Plugin name | How to select | Target | Typical latency class | CI |
|--------|-------------|---------------|--------|----------------------|----|
| Synthetic | `synthetic` | `--source synthetic` | patterned BGR frames | n/a (local) | Yes |
| USB UVC | `usb` | `--source usb --device 0` | device index | low (tens of ms) | Manual |
| File / video | `file` | `--source file --path clip.mp4` | filesystem path | file decode | Yes (fixtures) |
| Network / IP | `rtsp` | `--source rtsp --url rtsp://…` | OpenCV URL | high (100–500 ms+) | Mock only |

## RTSP known limits (CAM-04)

Phase 2 uses **OpenCV `VideoCapture(url)`** (usually FFmpeg backend). This is
**best-effort**, not a hardened NVR client.

| Topic | Honest expectation |
|-------|--------------------|
| Latency | Often **100–500 ms** class on LAN; Wi-Fi and high GOP length add more |
| Freezes | Wi-Fi drops / keyframe gaps can freeze the last decoded frame until reconnect |
| Backend variance | FFmpeg/OpenCV builds differ across desktop, Jetson, and Pi wheels |
| Credentials | `rtsp://user:pass@host/…` appears in **process argv / ps** — avoid on shared hosts; env-based secrets deferred |
| Auth / TLS | `rtsps://` support depends on the OpenCV build; not guaranteed |
| Multi-stream | Single camera first; do not open multiple RTSP URLs in one process for v1 |

### Deferred (not in Phase 2)

- **PyAV** (`av`) demux
- **GStreamer** pipelines
- Hardware decoder selection / low-latency RTP tweaks
- Credential injection from environment / secrets files

If OpenCV RTSP is inadequate for a deployment, escalate to a later phase rather
than bolting PyAV into the default path without docs and tests.

## Security notes

- Paths and URLs are passed **only** to OpenCV — never via shell.
- Default preview bind is **`127.0.0.1`** (MODEL-03). Binding `0.0.0.0`
  exposes the live camera stream on the LAN **without authentication** — opt-in
  only (`sentry serve --host 0.0.0.0`).
- RTSP credentials in the URL may show up in process lists and logs.

## Manual verification checklist

1. **Synthetic:** `uv run sentry serve --source synthetic` → open
   `http://127.0.0.1:8000/` → green **streaming** pill + moving bar.
2. **USB:** `uv run sentry serve --source usb --device 0` → live frames; unplug
   cable → **reconnecting** / **error** without freezing the whole page forever.
3. **File:** `uv run sentry serve --source file --path tests/fixtures/<clip>` →
   looping playback (default `loop_file=True`).
4. **RTSP (lab):** `uv run sentry serve --source rtsp --url "rtsp://…"` →
   frames appear; note latency vs USB; disconnect network → reconnect status.
5. Confirm `uv run sentry health` lists `rtsp` among sources.

## Related CLI

```bash
uv run sentry serve --source synthetic
uv run sentry serve --source usb --device 0
uv run sentry serve --source file --path /path/to/clip.mp4
uv run sentry serve --source rtsp --url "rtsp://camera.local/stream"
# Opt-in LAN bind (privacy risk — no auth):
uv run sentry serve --source synthetic --host 0.0.0.0
```

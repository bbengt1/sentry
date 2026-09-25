# CLI reference

Entry point: **`sentry`** (package `sentry-ai`, import `sentry_ai`).

```bash
uv run sentry --help
uv run sentry <command> --help
```

## `sentry health`

Print package version, selected profile, registered plugins, and `status: ok`.

```bash
uv run sentry health
uv run sentry health --profile desktop-gpu
```

| Option | Default | Description |
|--------|---------|-------------|
| `--profile` | `cpu-fallback` | Runtime profile name |

## `sentry cameras`

List OpenCV camera indices (USB / FaceTime / Continuity Camera on macOS).

```bash
uv run sentry cameras
# then: uv run sentry serve --source usb --device <IDX>
```

## `sentry smoke`

Validate synthetic frames against schema contracts — **no camera, no GPU,
no cloud keys**. Exit 0 on success.

```bash
uv run sentry smoke
uv run sentry smoke --profile cpu-fallback
```

Fails if `allow_cloud` is true on the loaded profile.

## `sentry serve`

Start capture + FastAPI (Live Preview and/or perception APIs).

```bash
uv run sentry serve [OPTIONS]
```

### Common options

| Option | Default | Description |
|--------|---------|-------------|
| `--source` | `synthetic` | `synthetic` / `usb` / `file` / `rtsp` |
| `--host` | `127.0.0.1` | Bind host (**localhost by default**) |
| `--port` | `8000` | Bind port |
| `--device` | `0` | USB OpenCV index (`--source usb`) |
| `--path` | — | File path (`--source file`) |
| `--url` | — | RTSP/HTTP URL (`--source rtsp`) |
| `--profile` | `cpu-fallback` | Runtime profile |
| `--camera-id` | derived | Override `camera_id` on frames |
| `--no-ui` | off | Headless: perception APIs without Live Preview HTML |
| `--calibration-file` | — | Explicit calibration YAML (overrides `SENTRY_CALIBRATION_DIR` / camera stem) |
| `--allowed-host` | loopback + bind address | Extra `Host` name (repeat the flag). Needed for a DNS name such as `robot.local` |
| `--allowed-origin` | Live Preview's own origin | Extra browser `Origin` for state changes and `/v1/stream` (repeat the flag) |

`SENTRY_CALIBRATION_DIR` selects the persist directory when
`--calibration-file` is omitted. See [calibration.md](calibration.md).

### Examples

```bash
# Synthetic (CI / no camera)
uv run sentry serve --source synthetic

# Full desktop path
uv run sentry serve --profile desktop-gpu --source usb --device 0

# File loop
uv run sentry serve --source file --path tests/fixtures/sample_clip.mp4

# Headless robot API
uv run sentry serve --no-ui --source usb --device 0

# Explicit persist file
uv run sentry serve --calibration-file /tmp/cam0.yaml --source synthetic

# Explicit LAN bind (NO AUTH — privacy risk)
uv run sentry serve --host 0.0.0.0 --source usb --device 0

# Open the preview by DNS name (Host must be listed; the name is not a wildcard)
uv run sentry serve --host 0.0.0.0 --allowed-host robot.local

# Let another local page change calibration / open the perception socket
uv run sentry serve --allowed-origin http://127.0.0.1:3000
```

### Serve behavior notes

1. Loads profile via `load_config`; rejects `allow_cloud: true`.  
2. Builds `profile_runtime` → detector / open-vocab / depth weights + device.  
3. Optional workers soft-fail if `detect` / `depth` extras missing.  
4. Always starts free-space loop when a store exists (idles without depth).  
5. Re-applies matching YAML (`try_reapply`); banner `calibration: {status}`
   where status is `none` / `applied` / `ignored_mismatch` / `error`.  
6. Ctrl+C / SIGINT shuts down workers and Uvicorn cleanly.
7. Rejects a `Host` that is not loopback, the bind address, or `--allowed-host`
   (**403** `host_not_allowed`). A wildcard bind (`0.0.0.0` / `::`) also
   accepts IP literals so `http://<lan-ip>:<port>/` still loads. DNS names
   do not match unless listed.
8. State-changing methods and `WS /v1/stream` reject a foreign `Origin`
   (**403** `origin_not_allowed`), `Sec-Fetch-Site: cross-site`
   (`cross_site_request`), and form / `text/plain` bodies
   (`content_type_not_allowed`). Clients that send no `Origin` (curl,
   scripts, robots) keep working. See
   [safety-and-privacy.md](safety-and-privacy.md).

## Module form

```bash
python -m sentry_ai health
python -m sentry_ai smoke
```

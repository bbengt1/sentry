# Adversarial Code Review

- Date: 2026-09-25
- Scope actually reviewed: `main` at `8ed672bdbeecf3a44ee16b16fbe356b9a5e4e812` (`feat(19-01): online consent flag + first-scale lock`). Package version in `pyproject.toml` is **0.1.0**. Planning milestone v0.3 (calibration wizard, YAML persist, metric free-space) is in this tree. Phase 19-01’s in-memory `set_online` flag is in this tree. Phase 19-02 REST/status wiring is **not** on this SHA (it lives on `feat/19-02-online-status-rest` / PR #20, which was not modified and was not treated as the shipping tree). Full `src/sentry_ai`, Live Preview `index.html`, `pyproject.toml`, and the operator docs named in the brief. `.planning/` was sampled only to check the stated 19-01 vs 19-02 split.
- Stack / context (from the brief): Sentry AI is camera-only perception for maker robotics (not the getsentry product). It emits a perception stream and no motor commands. Stack matches the brief: Python 3.11, package `sentry-ai` / import `sentry_ai`, Typer CLI `sentry`, FastAPI + uvicorn, OpenCV sources, optional Ultralytics YOLO/YOLOE and Depth-Anything-V2, optional ONNX Runtime / TensorRT, uv + hatchling, committed `uv.lock`, single-page Live Preview, YAML calibration store with a camera/model fingerprint. One correction: the online consent flag exists as `CalibrationState.set_online` / `CalibrationSnapshot.online`, but on this SHA nothing in the depth loop reads it, there is no `POST /api/depth/calibration/online`, and `GET /api/status` does not copy `online`. `GET /api/depth/calibration` does return `"online": false`.
- Reviewer stance: adversarial
- Verdict: Do not ship
- Confidence: Medium-high. Control-plane HTTP behavior was probed on a live `sentry serve --source synthetic` (127.0.0.1:8765). Free-space, depth-mode, YAML reapply, and clear-ordering claims were executed against the installed library in this checkout. No physical camera, and the `detect` / `depth` extras were not installed, so hardware capture and real weight deserialization were not executed.
- What could not be verified: Continuity Camera / Swift helper / FFmpeg AVFoundation behavior (no macOS, no camera). Whether a real Depth Anything V2 forward pass emits non-finite maps on black or failed frames. The exact `torch.load` / Ultralytics unpickle stack (detect extra absent). In-browser delivery of the CSRF form (a headless Chrome attempt did not finish); the server-side acceptance of those requests was verified with curl. PR #20’s REST online toggle.

## System sketch

Single operator process. `sentry serve` (`src/sentry_ai/cli.py` `serve`) builds a source, a depth-1 `FrameBus`, `CaptureLoop`, `PerceptionStore`, optional detection / open-vocab / depth loops, always-on `FreeSpaceLoop`, `CalibrationState`, and `PipelineState`, then binds uvicorn. Default host is `127.0.0.1`. There is no authentication, no session, no CSRF token, no `CORSMiddleware`, no `TrustedHostMiddleware`, and no `Origin` check.

HTTP/WS surface (all unauthenticated):

| Method | Path | Effect |
|---|---|---|
| GET | `/` | Live Preview HTML (`serve_ui`) or JSON 404 (`--no-ui`) |
| GET | `/preview/mjpeg` | Live camera JPEGs plus overlays |
| GET | `/api/status` | Capture status, stage metrics, calibration summary |
| GET | `/api/snapshot`, `/v1/snapshot` | `PerceptionFrame` JSON |
| WS | `/v1/stream` | Same JSON at ~10 Hz |
| GET/PATCH | `/api/pipeline/config` | Enable flags and ordinal free-space cuts |
| GET/PATCH | `/api/detection/config` | Detector confidence |
| GET/PATCH | `/api/depth/config` | `depth_mode` string |
| GET/PATCH/POST | `/api/open-vocab/config`, `POST /api/open-vocab/run` | Prompts and arming |
| GET/POST/DELETE | `/api/depth/calibration/*` | Freeze, sample, compute, apply, save, cancel, clear |
| GET | `/openapi.json` | Full schema (`docs_url` is off; OpenAPI is not) |

Identities: none. `camera_id` is a string chosen by the source or `--camera-id`. It is the calibration fingerprint’s primary key, not a hardware id.

Stores: in-memory bus + perception products; YAML at `$SENTRY_CALIBRATION_DIR` or `{cache}/calibration/{stem}.yaml` or `--calibration-file`; model cache `SENTRY_MODEL_CACHE` / `~/.cache/sentry-ai` (weights, HF hub, and on macOS a compiled Swift helper under `bin/`).

Jobs: capture, detection, depth, free-space, open-vocab daemon threads. HTTP handlers do not run inference, but they mutate the same `CalibrationState` / pipeline flags those threads read.

Trust boundaries that are actually enforced in code: `yaml.safe_load` (not `yaml.load`); `safe_camera_stem` rejects `..` and separators; ORT/TRT artifact paths are allowlisted; subprocesses use argument lists (no `shell=True`); perception schemas are `extra=forbid` and the wire payload omits bulk depth/masks and motor fields. Not enforced: who may call the API, which browser origin may open the socket, which `Host` is this process, whether a depth map is finite before it becomes “free space”, whether a metric label matches the weights that produced the numbers, whether a YAML scale survived the fit gates.

## Top failure modes

1. A depth map with no finite values is turned into a **complete** free-space product whose ROI is entirely free and whose `obstacle_count` is 0 (`error` stays null). A consumer that honors completeness and ignores “missing” still sees a clear path.
2. Turning depth off, or depth failing, does not clear free-space. The last occupancy product stays `completeness.free_space=true` and the MJPEG loop keeps painting it on newer camera frames.
3. Any client that can hit the bind address — and, for several POSTs, a web page on another origin — can clear calibration, cancel a draft, or fit/apply a draft. A WebSocket from a hostile `Origin` is accepted. `Host: evil.example` is also accepted, so a DNS-rebinding page becomes same-origin with the camera and the control plane.
4. A calibration file (or a one-point wizard fit with a large `known_meters`) can scale the map until every pixel is past the 3 m horizon. Free-space then reports `units="m"`, `far_frac=1`, and zero obstacles. YAML reload does not re-apply the fit gates, and `method: manual_scale` skips the sample-count check.
5. `PATCH /api/depth/config` with `metric_indoor` or `metric_outdoor` changes only the mode string and `model_id`. The already-loaded network keeps running, and its outputs are labeled `metric_estimated` with `unit="m"`.

## Findings

### [Critical] Non-finite depth is published as a complete, obstacle-free free-space product

- ID: CR-001
- Severity: Critical
- Domain: Data
- Evidence: `depth_to_nearness` in `src/sentry_ai/spatial/free_space.py` (lines 95–97) returns an all-zero nearness map when no pixel is finite. `compute_free_space` (lines 278–322) then treats nearness below `near_cut` (0.72) as not occupied, fills `free_mask` on the ROI, and returns `error=None`. The calibrated branch (lines 262–277 and 298–299) does the same with meter cuts: a non-finite map has `denom == 0`, bands all zero, an empty occupied mask, `units="m"`, and `error=None`. `FreeSpaceLoop._run` (`src/sentry_ai/spatial/loop.py` lines 208–248) stores that product. `assemble_perception_frame` (`src/sentry_ai/api/assemble.py` lines 139–140 and 301–305) sets `completeness.free_space` from “product present and `error is None`”, independent of whether any depth sample was finite.
- Attack / failure story: Depth Anything (or a test double, a disconnect that yields NaNs, or a numeric blow-up after `scale * map + offset`) produces an all-NaN map. Free-space does not fail the frame. On a 20×20 relative NaN map executed here, the result was `error=None`, `obstacles=0`, `units="ordinal"`, `bands={near_frac: 0, mid_frac: 0, far_frac: 1}`, and 220 free pixels (the entire bottom-55% ROI). The calibrated branch, by inspection of the same function, emits `units="m"` and `obstacle_count=0` with a full free mask. `docs/safety-and-privacy.md` says invalidated or missing free-space must not be treated as a clear path. This product is not missing. It is a successful “all far / nothing occupied” message.
- Impact: A robot that trusts `completeness.free_space` and `obstacle_count` drives into whatever the camera is actually seeing. Blast radius is a collision if this stream is used as clearance. The project’s own denylist correctly omits `safe_to_drive`; the free-space payload still reads as clearance.
- Likelihood: Medium on a healthy model (NaNs are not the common frame) and high on any failure mode that yields an empty finite mask. No attacker is required.
- Fix: If the finite count in the ROI is zero, return `error` set, null masks, and `obstacle_count=0` with `units` left ordinal. Do not fill `free_mask`. Teach `assemble_perception_frame` to treat that product as incomplete. Add a regression with an all-NaN map and an all-`+inf` map for both `RELATIVE` and `METRIC_CALIBRATED`.
- Tests that would have caught it: A golden test that an all-non-finite map must set `error` and must not set `far_frac=1` or a full free mask. The existing free-space tests cover happy percentile and meter cuts, not the empty-finite path.
- Residual risk: A finite but wrong monocular map can still look far. That remains an honesty limit of the sensor, not a missing-data bug. Constant finite maps are also obstacle-free by the ordinal design (mid nearness 0.5 is below `near_cut`); that part is intentional and is not this finding.

### [High] Last free-space product stays complete after depth is cleared, and MJPEG keeps drawing it

- ID: CR-002
- Severity: High
- Domain: Cross-cutting
- Evidence: `DepthLoop.set_enabled(False)` (`src/sentry_ai/models/depth/loop.py` lines 65–75) calls only `PerceptionStore.clear_depth`. `FreeSpaceLoop._run` (lines 184–192) skips when depth is missing or has `error`, and does not clear the previous free-space slot. `assemble_perception_frame` still marks `completeness.free_space` true whenever that slot’s `error` is null (lines 139–140, 256–272, 301–305). Stale is a separate `stats` bit with a 750 ms TTL. `preview_mjpeg` / `_mjpeg_generator` (`src/sentry_ai/api/routes_preview.py` lines 278–285) draws free-space whenever `error is None`, with no age check. The same generator blends depth the same way (lines 267–277).
- Attack / failure story: Operator or a LAN client sends `PATCH /api/pipeline/config` `{"depth_enabled": false}`, or the depth thread records an error and stops updating. Executed here: after `set_enabled(False)` with a free-space product 500 ms old, `completeness` was `depth=false, free_space=true`, `frame.depth` was null, and `free_space_stale` was 0 because 500 ms is under the 750 ms TTL. For the next 750 ms the wire says free-space is fresh. After that it is stale but still complete, forever, until something writes a new free-space product. MJPEG keeps compositing that occupancy onto whatever JPEG is currently in the bus, including frames captured after the depth source died.
- Impact: The UI and `/v1/snapshot` disagree with the depth stage. A client that checks completeness and not `stats.free_space_stale` keeps the old obstacle geometry. A client that does check stale is still wrong during the first 750 ms. The Live Preview shows a live-looking picture with a dead occupancy overlay.
- Likelihood: High. Stage toggles are a documented feature (`docs/api-reference.md` says disable clears that stage’s product once; it does not clear the derived free-space product). Depth errors are the normal dependency-failure path.
- Fix: `clear_depth` (and the depth error path) must `clear_free_space` under the same store lock, and `FreeSpaceLoop` must not keep serving a product whose `frame_id` no longer matches a live depth product. MJPEG must not draw a free-space or depth overlay whose age exceeds the TTL. Reset the occupancy smoother at the same time (apply/clear already does; depth-loss does not).
- Tests that would have caught it: Disable depth after a good free-space write; assert the next snapshot has `completeness.free_space is false` and a null `free_space` payload even when `now` is only a few hundred milliseconds later. Assert the MJPEG path does not call `draw_free_space` on a stale product.
- Residual risk: Temporal skew between detection boxes and depth is documented and remains. This finding is the case where the upstream product is gone and the derived one is not.

### [High] Changing depth_mode relabels the loaded network as meters

- ID: CR-003
- Severity: High
- Domain: Backend
- Evidence: `DepthAnythingWorker.set_depth_mode` (`src/sentry_ai/models/depth/worker.py` lines 79–90) updates `_depth_mode` and `_model_id` only. `_ensure_model` (lines 92–97) returns the already-constructed model and never drops it. `process` (lines 123–126) takes `kind, unit` from `kind_for_mode(mode)` (`src/sentry_ai/models/depth/mapping.py` lines 33–42), which maps `metric_indoor` / `metric_outdoor` to `DepthKind.METRIC_ESTIMATED` and `unit="m"`. `PATCH /api/depth/config` (`src/sentry_ai/api/routes_depth.py` lines 60–68) calls `set_depth_mode` and returns the new string. `docs/api-reference.md` says “Relative mode never claims meters.” It does not say metric mode reloads the metric checkpoint. The Live Preview has no depth-mode control; this is API-only, but it is on by default whenever the depth extra is installed.
- Attack / failure story: Serve starts in `relative` and the first `process` loads `depth-anything/Depth-Anything-V2-Small-hf`. A client then `PATCH`es `{"depth_mode":"metric_outdoor"}`. Executed with an injected model that always returns 2.5: before the switch, `kind=relative`, `unit=None`, mean 2.5; after the switch, the same model object, the same 2.5 map, `kind=metric_estimated`, `unit="m"`. `model_id` in the response becomes the metric HF id even though those weights were not loaded. If a calibration is later fit, the fingerprint records the metric mode while the raw values still come from the relative head, and `promote_kind_unit` will emit `metric_calibrated` once that fit is applied.
- Impact: `stats.depth_min/max/mean` and `depth.unit` on `/v1/snapshot` describe relative-network outputs as meters. That is the honesty bug the calibration work was built to prevent, reachable in one request. Free-space stays ordinal until a calibration is applied (`assert_free_space_units` forbids `units="m"` for `metric_estimated`), so this finding is the depth metadata lie, not an immediate meter free-space lie.
- Likelihood: Medium. No UI button. Any client that can PATCH the bind address can do it, including the documented `--host 0.0.0.0` case. An operator following the API reference can do it believing the metric Small checkpoint will load.
- Fix: On mode change, drop `_model` and `_processor` and load `MODE_TO_MODEL[mode]` before the next `process`. Until that load succeeds, keep returning the previous kind/unit (or an error product), never the new kind. Refuse the PATCH with 409 if the checkpoint cannot be loaded. Add a test that `set_depth_mode` after a successful load does not report `unit="m"` until a different module object has been constructed.
- Tests that would have caught it: Inject a sentinel model, call `set_depth_mode("metric_indoor")`, and assert either that `_ensure_model` is not the sentinel or that `process` still returns `RELATIVE` / `unit is None`.
- Residual risk: Metric Small checkpoints are still monocular estimates. Loading the right file does not make them vehicle-grade. `refuse_if_mismatch` will drop a stored calibration whose `depth_mode` disagrees; that part is fine and is not a substitute for loading the right weights.

### [High] State-changing POSTs accept cross-site simple requests

- ID: CR-004
- Severity: High
- Domain: Security
- Evidence: `create_app` (`src/sentry_ai/api/app.py` lines 68–73) installs no auth and no origin middleware. These handlers do not require a JSON body, so a browser can send them as “simple” requests (`POST` with `application/x-www-form-urlencoded` or `text/plain`) and will not preflight: `clear_calibration` (lines 508–520), `cancel_calibration` (lines 499–505), `apply_calibration` (lines 454–457, raw `request.body()`), `save_calibration` (lines 479–483, same), `freeze_calibration` (lines 346–357), `compute_calibration` (lines 413–421, `body is None` becomes the default fit), `post_open_vocab_run` (`src/sentry_ai/api/routes_open_vocab.py` lines 188–206, body optional). Live probes against synthetic serve, all with `Origin: https://evil.example`:

  | Request | Result |
  |---|---|
  | `POST /api/depth/calibration/clear` as `application/x-www-form-urlencoded` and as `text/plain` | **200**, snapshot returned |
  | `POST /api/depth/calibration/cancel` with no body | **200** |
  | `POST /api/depth/calibration/compute` as form-urlencoded empty | **422** `insufficient_valid_samples` from the fit handler, not a parse rejection |
  | `POST /api/depth/calibration/apply` empty form | **422** `no draft calibration params to apply` (handler ran) |
  | `POST /api/depth/calibration/save` and `/freeze` | **422** business errors (`no applied calibration`, `no_depth_product`), not 415 |
  | `POST /api/open-vocab/run` empty form | **503** `open-vocab worker not available` (handler ran; detect extra was absent) |
  | `OPTIONS` preflight | **405**, `Allow: POST`, no `Access-Control-Allow-Origin` |
  | `POST /api/depth/calibration/sample` as `text/plain` containing JSON | **422** body parse error (typed JSON body; not a simple-request bypass) |

  `GET /` returns no `Content-Security-Policy` and no `X-Frame-Options`. Typed JSON `PATCH` bodies are not simple requests and were rejected when forced to `text/plain`.
- Attack / failure story: Operator runs the default localhost server and opens an `http://` page (or any client that is not blocked by the browser’s mixed-content / local-network rules). That page submits a form to `http://127.0.0.1:8000/api/depth/calibration/clear`. The server deletes the applied scale and the YAML file. If a draft with samples already exists, a second form post to `/compute` stages a fit and a third to `/apply` commits it. No cookie and no CORS grant is required, because there is no credential and the attacker does not need to read the response. On `--host 0.0.0.0` the same requests come from any LAN host with no browser involved.
- Impact: Silent loss of metric calibration (restart will not restore it if the unlink succeeds — see CR-009). A staged draft can be committed. Open-vocab can be armed when the detect extra is present. The Live Preview Clear button is also frameable, so clickjacking is a second path to the same handler.
- Likelihood: High for any non-browser client that can route to the bind address. Medium for a random `https://` site in a current browser (mixed content and local-network prompts may block it). The server does not depend on those browser mitigations, and they were not re-checked in Chrome here.
- Fix: Reject unsafe methods unless `Origin` is absent (non-browser) or is an allowlisted loopback origin, and reject `Sec-Fetch-Site: cross-site` when that header is present. Require `Content-Type: application/json` on every mutating handler, including the ones that read `request.body()` themselves. Add `X-Frame-Options: DENY` (or CSP `frame-ancestors 'none'`) on `/`. Do not treat “localhost” as an authentication scheme. Keep the documented no-auth posture only for same-machine non-browser clients that also pass a Host allowlist (CR-005).
- Tests that would have caught it: ASGI tests that post `application/x-www-form-urlencoded` from a foreign `Origin` to `/clear`, `/cancel`, `/apply`, `/compute` and expect 403, and that a same-origin JSON post still works.
- Residual risk: A same-machine process can still call the API. That matches the stated single-operator model. A browser on that machine must not be in that set.

### [High] WebSocket accepts any Origin, and Host is not checked

- ID: CR-005
- Severity: High
- Domain: Security
- Evidence: `v1_stream` (`src/sentry_ai/api/routes_v1.py` lines 64–75) calls `websocket.accept()` with no `Origin` inspection. `create_app` does not add `TrustedHostMiddleware`. Live checks on the synthetic server: a `websockets` client connected to `ws://127.0.0.1:8765/v1/stream` with `Origin: https://evil.example` and the handshake succeeded (no perception product yet, so no frame was sent, but the socket stayed open). `curl -H 'Host: evil.example' http://127.0.0.1:8765/api/status` returned **200**. Cross-origin `GET /api/status` returned **200** with no `Access-Control-Allow-Origin`, so page JavaScript cannot read that body without a rebind. `GET /preview/mjpeg` is a no-credential image response (`multipart/x-mixed-replace`).
- Attack / failure story: A page the operator visits opens `ws://127.0.0.1:8000/v1/stream`. Browsers do not apply CORS to WebSocket reads; they only send `Origin`. This server ignores it, so the page receives detection classes, free-space bands, and calibration-related stats from inside the home. Separately, a DNS-rebinding hostname that flips to `127.0.0.1` makes the attacker’s document same-origin with the server because `Host` is not pinned to the bind address. That page can then `fetch` the MJPEG bytes and call the JSON calibration API, including `POST /sample` with an attacker-chosen `known_meters` (the step CR-004 cannot do as a simple request).
- Impact: Privacy loss of the perception stream (people and rooms, via labels and geometry even when pixels stay off the JSON wire). After a successful rebind, full control of calibration and stage flags, which is the path into CR-007’s false metric clearance. MJPEG pixel readback from a normal cross-origin `<img>` stays tainted without CORS; the rebind removes that limit.
- Likelihood: Medium for WebSocket from an `http://` page; lower from `https://` if the browser blocks mixed `ws://`. Medium-low for a working DNS rebind against loopback on a current browser, which is why this is High and not Critical. High if the process is bound to `0.0.0.0` (no rebind required).
- Fix: On the WebSocket, accept only `Origin` values whose host is loopback (or reject a present `Origin` that does not match the bind host). Add `TrustedHostMiddleware` (or an equivalent check) whose allowed hosts are the bind host plus `localhost`. Keep CORS disabled. Log nothing from the `Origin` header that might itself be an injection.
- Tests that would have caught it: A WebSocket handshake with `Origin: https://evil.example` must be closed before `accept` publishes frames. `GET /api/status` with `Host: evil.example` must be 400.
- Residual risk: Non-browser clients on the bind address remain allowed under the localhost posture. Binding `0.0.0.0` remains an intentional unauthenticated LAN exposure; Host filtering does not replace auth there.

### [High] RTSP userinfo is copied into status, logs, and the on-screen error

- ID: CR-006
- Severity: High
- Domain: Security
- Evidence: `OpenCVSource.open` raises `SourceError(f"failed to open source: {self.target!r}")` (`src/sentry_ai/sources/opencv_source.py` lines 90–95). `read` raises `SourceDisconnected(f"no frame from {self.target!r}")` (line 153). `RtspSource` stores the CLI `--url` as that target (lines 239–250) with no userinfo strip and no scheme check. `CaptureLoop._run` (`src/sentry_ai/capture/loop.py` lines 182–213) puts `str(exc)` into `status_detail` and into `logger.warning` / `logger.exception`. `GET /api/status` returns `status_detail` unchanged (`src/sentry_ai/api/routes_preview.py` lines 81–86). The Live Preview copies it into the error banner with `textContent` (`src/sentry_ai/ui/static/index.html` lines 504–511 and 752–758), so it is not an HTML injection, but it is rendered and it is in the JSON. A repo-wide search found no redact helper. `--url` also remains in the process argument list.
- Attack / failure story: Operator serves `--source rtsp --url rtsp://<user>:<password>@nvr/stream`. The camera is briefly unreachable. Every LAN client (if bound off localhost) and every local caller of `/api/status` receives the password inside `status_detail`. The same string is written to stderr on every reconnect. The banner shows it to anyone who can see the preview.
- Impact: Camera account disclosure. Those credentials are often reused on the NVR’s admin interface. The finding does not require a successful decode of video.
- Likelihood: High whenever an RTSP URL contains userinfo and the source fails open or read, which is the reconnect path the capture loop is built around. Not executed against a real NVR in this environment; the f-string is unconditional.
- Fix: Parse the URL and store a redacted target (`user` kept or replaced, password always removed) for exceptions, status, and logs. Keep the raw URL only in the `VideoCapture` call. Add a test that a URL with userinfo produces a `status_detail` that does not contain the password.
- Residual risk: Process listings and shell history still show the CLI argument. Document that operators should prefer a credentials file or env var that is not logged. Scheme allowlisting is CR-014.

### [High] Persisted and one-point fits can scale the world until free-space says it is empty

- ID: CR-007
- Severity: High
- Domain: Data
- Evidence: Fit-time gates live only in `src/sentry_ai/spatial/calibration.py` (`MIN_SCALE=1e-4`, `MAX_SCALE=1e4`, residual RMS). `is_valid_calibration_params` (`src/sentry_ai/schemas/calibration.py` lines 85–102) accepts any finite `scale > 0`, any finite `offset`, and `method="manual_scale"` with `sample_count=0`. `try_reapply` (`src/sentry_ai/control/calibration_persist.py` lines 38–64) loads YAML and calls `apply_params`, which uses only `is_valid_calibration_params`. `fingerprints_match` ( `src/sentry_ai/config/calibration_store.py` lines 102–108) skips width and height when either side is null. `serve` builds the boot fingerprint with `width=None, height=None` (`src/sentry_ai/cli.py` lines 621–630). `fit_scale_median` on a single pair has residual 0, so one wizard sample with a large `known_meters` is accepted up to just under `1e4`.
- Attack / failure story: Executed: a YAML document with `scale: 1e6`, `offset: 0`, `method: manual_scale`, `sample_count: 0`, and `camera_id: synthetic0` was `is_valid` true, and `try_reapply` against a boot-shaped fingerprint (`width=None`) returned `applied`. The same file against `width=999` was `ignored_mismatch` / `resolution`, so the boot null is what lets a mismatched resolution through until a later depth frame. A map of raw value 2.5 scaled by `1e6` and passed to `compute_free_space(..., kind=METRIC_CALIBRATED)` returned `units="m"`, `obstacles=0`, `far_frac=1`, `error=None`. A positive `offset` of `1e9` is also structurally valid and pushes every pixel past 3 m. Remote variant, no file write required: `POST /sample` with the operator’s pixel and `known_meters` near 9999, then `/compute` and `/apply`. One pair fits with RMS 0. On `--host 0.0.0.0`, or after CR-005’s rebind, that POST is unauthenticated. Classic CSRF (CR-004) cannot forge the JSON sample body; it can `compute`+`apply` a draft the operator already sampled.
- Impact: `metric_calibrated` free-space with an empty near band. Downstream code that treats `units="m"` and `obstacle_count==0` as “nothing within 1.5 m” is wrong by orders of magnitude. `camera_id` is not a device serial; `--camera-id usb0` on a different physical camera reuses that file.
- Likelihood: Medium for a hostile or truncated local YAML (the threat model includes it). High on a non-loopback bind for the one-point API fit. Low on default localhost against a remote browser, because the sample body is JSON.
- Fix: Run the same absurd-scale and offset bounds inside `is_valid_calibration_params`, and call that from `load_params` before `apply_params`. Reject `manual_scale` from disk unless it was produced by the gated fitter, or drop `manual_scale` as a loadable method. Require at least two samples before `units="m"` can go live. Pass the first real frame’s width and height into `try_reapply` (retry when the first depth map arrives) instead of committing a null-resolution match at boot. Clamp or refuse `known_meters` above a documented hobby range in the sample handler.
- Tests that would have caught it: `try_reapply` of `scale=1e6` or `offset=1e9` must return `error` and leave `is_applied()` false. A one-sample fit whose implied scale would put a mid-range raw value beyond the far cut must not set draft params. Boot reapply with live `width=None` and saved `width=4` must not apply.
- Residual risk: A scale inside `1e-4..1e4` can still be a bad measurement. That is the stated monocular limit. The bug is the missing re-check and the one-point zero-residual accept.

### [High] Detector and depth checkpoints are loaded with no digest pin

- ID: CR-008
- Severity: High
- Domain: Security
- Evidence: `YoloDetectionWorker._ensure_model` (`src/sentry_ai/models/detection/yolo_worker.py` lines 84–89) calls `YOLO(self._weights)` after `configure_model_cache()`. `YoloeOpenVocabWorker` does the same with `YOLOE(self._weights)` (`src/sentry_ai/models/detection/yoloe_worker.py` lines 108–113). `DepthAnythingWorker._ensure_model` (`src/sentry_ai/models/depth/worker.py` lines 116–118) calls `AutoImageProcessor.from_pretrained(self._model_id)` and `AutoModelForDepthEstimation.from_pretrained(self._model_id)` with no `trust_remote_code=False` passed explicitly and no revision pin. Weight names are allowlisted (`src/sentry_ai/models/cache.py` `KNOWN_WEIGHTS`); file contents are not. ORT/TRT paths are allowlisted (`src/sentry_ai/config/artifact_paths.py`) and then handed to `YOLO("*.onnx"|"*.engine")` as well (`factory.py`). The cache root is `~/.cache/sentry-ai` or `SENTRY_MODEL_CACHE`, created mode-default by `mkdir`. This checkout did not install `ultralytics` or `torch`, so the callee’s `torch.load` was not executed.
- Attack / failure story: Something that can write the weights directory replaces `yolo26n.pt` (or the HF snapshot) with a pickle payload. Next `sentry serve` with the detect or depth extra loads it in-process. Ultralytics `.pt` files are pickle archives; that is the library’s format, and this repo never sets a `weights_only` boundary or compares a published sha256 before `YOLO()`. First-run download is trust-on-first-use over the network to Ultralytics and Hugging Face.
- Impact: Arbitrary code execution as the operator, which includes camera access and the ability to publish false perception. A same-user attacker already has that, so the incremental bug is a poisoned cache or a poisoned download, not a remote RCE from the HTTP API.
- Likelihood: Medium on a shared or previously compromised cache; low for a single careful maker whose cache was written by the official downloader. The threat model in the brief includes hostile model artifacts, so this stays High.
- Fix: Pin hashes for the known filenames and for the Small HF repos, and refuse to call `YOLO` / `from_pretrained` when the file does not match. Prefer safetensors for depth. Pass `trust_remote_code=False` explicitly. Do not widen this into a new model-loading architecture; the missing check is the bug.
- Tests that would have caught it: A fake `YOLO` / `from_pretrained` spy is not enough. A test that the loader refuses a file whose digest is not in the allowlist, using a local stand-in file, would lock the policy. Document the expected digest source so CI can update it on purpose.
- Residual risk: ONNX and TensorRT engines are also executable data. Hash-pin those artifacts too. A hash pin does not review the model’s training provenance.

### [Medium] Clear wipes memory before the YAML unlink, and a failed unlink is not rolled back

- ID: CR-009
- Severity: Medium
- Domain: Data
- Evidence: `clear_persisted` (`src/sentry_ai/control/calibration_persist.py` lines 75–79) calls `clear_applied`, `clear_draft`, then `delete_params`. `clear_calibration` (`src/sentry_ai/api/routes_calibration.py` lines 508–520) does not catch `OSError`. `save_params` itself is atomic (`temp` + `os.replace` in `src/sentry_ai/config/calibration_store.py` lines 111–132); clear is not. `docs/calibration.md` section 8 says Clear deletes the YAML so a restart cannot resurrect the scale.
- Attack / failure story: Executed by stubbing `delete_params` to raise `OSError("disk full")`: the exception propagated, `is_applied()` was already false, and the YAML file was still on disk. The HTTP client sees 500 and may believe nothing changed. The running process is now uncalibrated. The next `sentry serve` runs `try_reapply` and puts the scale back.
- Impact: The operator’s “stop claiming meters” action does not survive restart in the one case where the filesystem rejects the delete. The inverse crash window (killed after unlink, before the response) is safe. There is no audit record of the clear.
- Likelihood: Low in normal operation (unlink of a small YAML rarely fails) and certain under a full disk or a permission change on the calibration directory.
- Fix: Unlink (or replace-with-tombstone) first, and only then clear memory; or clear memory and, on unlink failure, surface a distinct error that still retries the unlink and does not report success. Add a test with a directory whose files cannot be removed.
- Tests that would have caught it: The stub used in this review: `delete_params` raises, expect `is_applied()` still true or expect the file to be gone. Today neither holds.
- Residual risk: A crash between the two steps remains unless the tombstone and the state live in one rename.

### [Medium] After calibration, the near/mid sliders do not control the meter cuts

- ID: CR-010
- Severity: Medium
- Domain: UI/UX
- Evidence: `PipelineState` and `PATCH /api/pipeline/config` store `near_cut` / `mid_cut` in `[0, 1]` (`src/sentry_ai/control/pipeline_state.py`, `src/sentry_ai/api/routes_pipeline.py` lines 96–108). `FreeSpaceLoop._run` always passes those floats into `compute_free_space` (`src/sentry_ai/spatial/loop.py` lines 203–215). `compute_free_space` documents that `near_cut` / `mid_cut` are ignored when `kind` is `METRIC_CALIBRATED` and uses 1.5 m / 3.0 m instead (`src/sentry_ai/spatial/free_space.py` lines 201–207 and 262–277). The Live Preview sliders are labeled “Free-space near band cutoff” / “Mid cut” with range 0–1 (`src/sentry_ai/ui/static/index.html` lines 350–367) and the footer says free-space uses ordinal bands. Nothing on the page switches the labels to meters when `depth_kind` is `metric_calibrated`. Executed: a constant 2.0 m map with `near_cut=0.99` still produced `mid_frac=1`, `obstacles=0`, `units="m"` (2.0 is between the hard 1.5 m and 3.0 m cuts).
- Attack / failure story: Operator calibrates, then drags “near” to the top of the slider expecting obstacles inside a few meters to light up. The wire and the overlay keep the compiled 1.5 m / 3.0 m bands. Status still shows the ordinal numbers they just set (`near_cut` from pipeline state), so the UI confirms a change that the metric path did not use.
- Impact: The only on-screen control for “how close is occupied” is a no-op in the mode where distances are in meters. An operator can believe they tightened the robot’s near band.
- Likelihood: High as soon as a calibration is applied and someone touches the sliders. The sliders are on the default page.
- Fix: When the live depth kind is `metric_calibrated`, disable the ordinal sliders and show the actual 1.5 m / 3.0 m cuts (read-only until there is a real meter-cut API). Do not echo ordinal `near_cut` as if it were the live threshold in that mode.
- Tests that would have caught it: A metric map at 2.0 m must report the same bands for `near_cut=0.99` and `near_cut=0.72`, and the status payload must not present those ordinal fields as the active meter threshold. The UI test should show meter copy when `calibration_active` is true.
- Residual risk: 1.5 m / 3.0 m remain approximate monocular cuts even when the labels are honest.

### [Medium] The Drops counter counts every keep-latest overwrite

- ID: CR-011
- Severity: Medium
- Domain: UI/UX
- Evidence: `FrameBus.publish` (`src/sentry_ai/bus/frame_bus.py` lines 45–49) increments `frames_dropped` whenever the slot already holds a frame. That is every frame after the first, not a failed read. `CaptureLoop.build_status` copies it to `frames_dropped` (`src/sentry_ai/capture/status.py` / `loop.py` lines 88–99). The page labels it “Drops” (`src/sentry_ai/ui/static/index.html` line 291 and 552–553). On the live synthetic server, `/api/status` showed `frame_id` 1076 and `frames_dropped` 1076 while `status` was `streaming` at ~30 fps.
- Attack / failure story: No attacker. The operator sees Drops climbing in lockstep with the frame id on a healthy camera and learns to ignore the field. A later real stall is invisible in the one number the page offers for loss.
- Impact: The capture-health signal on the primary page is false during normal operation. Detection and depth loops keep separate gap counters (`record_depth_drop` and friends) that are not what this label shows.
- Likelihood: Certain. It happens on every serve.
- Fix: Count a drop only when a subscriber observes a `frame_id` gap, or rename the bus metric and stop rendering the overwrite count as Drops. Show capture status and age instead.
- Tests that would have caught it: Publish N frames with no consumer lag that the product considers unhealthy; assert the status field shown as drops stays 0. The current test likely locks in the overwrite definition; change the UI contract, not the comment, if the counter is kept for debugging.
- Residual risk: A genuinely overloaded detector still needs its own drop count. That one already exists on the store metrics.

### [Medium] Clear has no confirm, and Apply does not persist

- ID: CR-012
- Severity: Medium
- Domain: UI/UX
- Evidence: The Clear handler (`src/sentry_ai/ui/static/index.html` lines 1176–1181) posts `/api/depth/calibration/clear` immediately. There is no `confirm`, no typed camera id, and no undo. Cancel (lines 1171–1174) correctly drops draft only. Apply (lines 1166–1169) posts `/api/depth/calibration/apply` with no body, and `CalibrationApplyBody.persist` defaults to false (`src/sentry_ai/api/routes_calibration.py` lines 58–63 and 454–457). A search of `index.html` found no call to `/api/depth/calibration/save` and no `persist: true`. The footer (lines 435–438) says “Cancel drops draft only; Clear drops applied” and does not say Apply is gone on restart. `docs/calibration.md` section 6 documents persist as a separate API step. The page also has no control for the online flag. `#error-banner` is `role="alert"` and the pills are `aria-live="polite"`, which is better than a silent failure; the destructive action itself is one click. Combined with CR-004, the same click can be forged by a framed page because `/` sends no frame-ancestors policy.
- Attack / failure story: Operator samples, computes, hits Apply, sees “Applied.” and a metric kind, then restarts serve. `try_reapply` finds no file (`calibration: none`) and the stream is relative again. Or they hit Clear intending to drop the draft (the button sits next to Cancel) and the YAML is deleted. A double post is possible: Apply’s button is not disabled for the request (Sample and Compute are).
- Impact: Loss of the only metric scale, with no audit entry. The UI-only story does not match the server, but here the server is stricter than the UI (restart drops an unpersisted apply), so the failure is data loss rather than a bypass.
- Likelihood: High for anyone who calibrates only through Live Preview.
- Fix: Add a confirm step on Clear that states the YAML path will be deleted. Either make Apply send `{"persist": true}` after an explicit “Save on this camera” checkbox, or add a Save button and change the Apply toast to “Applied for this process only.” Disable the button until the response returns.
- Tests that would have caught it: A page test that Apply’s request body is empty (locks the bug in) should be inverted once Save exists. A test that Clear is not sent on the first click.
- Residual risk: A confirmed Clear is still irreversible. That is acceptable if the copy says so.

### [Medium] MJPEG re-sends the last frame at 30 Hz while the camera is down

- ID: CR-013
- Severity: Medium
- Domain: UI/UX
- Evidence: `CaptureLoop` keeps the last bus frame while reconnecting (`src/sentry_ai/capture/loop.py` module docstring, lines 7–8, and the read-failure path at lines 202–209, which does not clear the bus). `_mjpeg_generator` (`src/sentry_ai/api/routes_preview.py` lines 263–316) encodes `bus.get_latest()` on every 33 ms tick whenever the slot is non-null. The JPEG has no age text. The status pill does switch to reconnecting and the banner can say the last frame may be stale (index.html lines 752–755), but a client that only embeds `/preview/mjpeg` never sees that pill.
- Attack / failure story: USB or RTSP drops. The browser `<img>` keeps receiving multipart JPEGs of the last good picture, so a frozen room looks like a live empty scene. Free-space drawn on top is the previous product (CR-002).
- Impact: The operator, or a dashboard that only shows the MJPEG URL, treats a stuck frame as the current room. Perception JSON does age out via `stats.*_stale`; the video URL does not.
- Likelihood: High on flaky RTSP, which the capture loop treats as the normal reconnect case. Not executed with a real disconnect here; the generator logic is unconditional.
- Fix: When `status` is `reconnecting` or `error`, stop emitting new parts or stamp the JPEG with the frame age and a reconnect banner in the image itself. Bound how long a stale bus slot may be served.
- Tests that would have caught it: Set a bus frame, mark the loop reconnecting, and assert the generator yields no further parts (or yields a visibly marked placeholder).
- Residual risk: A camera that sends identical frames of a static scene is indistinguishable from a stall without a capture timestamp on the image.

### [Medium] `--url` is passed to OpenCV with no scheme allowlist

- ID: CR-014
- Severity: Medium
- Domain: Security
- Evidence: `RtspSource` (`src/sentry_ai/sources/opencv_source.py` lines 230–250) accepts any non-empty string. `_open_video_capture` (lines 43–50) calls `cv2.VideoCapture(target)` for non-macOS-index targets. `_URL_PREFIXES` includes `rtsp`, `rtsps`, `http`, and `https`, and anything else is treated as a file path (`_is_file_target`, lines 36–40). There is no runtime HTTP API to change the URL; the caller is the operator’s CLI. Failures echo `self.target` (CR-006).
- Attack / failure story: A pasted URL such as `http://169.254.169.254/` or `file:///…` is opened by the OpenCV FFmpeg backend from the serve process. This is not a remote SSRF: nothing in the HTTP API sets the source. It is a hostile or careless URL at process start, which the brief lists. Internal responses are not returned as files; they are decoded as video, and the error string can still carry the target.
- Impact: The serve process makes a network or filesystem open the operator did not intend, as the operator’s user. Combined with CR-006, the target string is published on `/api/status`.
- Likelihood: Low unless someone points `--url` at a non-camera. The code will do it.
- Fix: Allow only `rtsp://` and `rtsps://` in `RtspSource`. Keep file playback on `--source file`. Reject userinfo in logs even if the scheme is allowed.
- Tests that would have caught it: `RtspSource("file:///etc/passwd")` and `RtspSource("http://127.0.0.1/")` raise before `VideoCapture`.
- Residual risk: A real RTSP URL can still point at any host the operator can route to. That is the feature.

### [Medium] Apply commits the scale before persist, then returns 422 if the write fails

- ID: CR-015
- Severity: Medium
- Domain: Backend
- Evidence: `apply_calibration` (`src/sentry_ai/api/routes_calibration.py` lines 454–476) calls `state.apply()` and only then, if `persist` is true, `persist_applied`. A missing path or a `ValueError` from the writer raises 422 after the in-memory commit. The freeze pin is dropped and the smoother reset only after a successful write. The UI does not send `persist` today (CR-012); API clients and a future Save-on-Apply will hit this.
- Attack / failure story: Client posts `{"persist": true}`. Draft moves to applied. The directory is not writable. The client shows the 422 and retries, or tells the operator apply failed. The live depth loop is already multiplying by the new scale. Restart does not have the file, so the next process silently returns to relative.
- Impact: The wire and the client disagree about whether metric scale is live. A retry of Apply fails with “no draft” because the draft was cleared inside `apply()`.
- Likelihood: Medium on a bad `SENTRY_CALIBRATION_DIR` or a full disk. Low on the default cache path.
- Fix: Persist first to a temp file, then `apply()`, then `os.replace`. If apply fails, leave the previous file. On persist failure, leave the draft in place and do not change applied. Return 200 only when both sides match.
- Tests that would have caught it: `persist_applied` raises; assert `is_applied()` is unchanged and the draft is still present.
- Residual risk: A crash after replace and before the response can still leave disk ahead of the client. The next boot’s `try_reapply` makes that survivable if the fingerprint matches.

### [Low] The cached Swift capture helper is executed without a digest

- ID: CR-016
- Severity: Low
- Domain: Security
- Evidence: `ensure_capture_av_binary` (`src/sentry_ai/sources/avfoundation_unique.py` lines 175–193) returns `~/.cache/sentry-ai/bin/capture_av_device` when the file is non-empty and `capture_av_device.version` equals `"5"`. It does not hash the binary. `AvFoundationUniqueSource.open` (lines 311–316) `Popen`s that path with the camera `unique_id` as a separate argument (not a shell). Not executed here (Linux, no `swiftc`).
- Attack / failure story: A process that can write the operator’s cache replaces the helper and the version file. The next Continuity serve runs it. `unique_id` is not a shell injection; the issue is the unsigned cached executable.
- Impact: Code execution as the operator on macOS, which already follows from write access to their home directory. Incremental risk is a cache restored from an untrusted backup or a world-writable cache directory.
- Likelihood: Low.
- Fix: Store a hash of the compiled bytes next to the version marker and recompile when it differs. Keep the argv list.
- Tests that would have caught it: Point the cache at a binary whose contents changed but whose version file still says `5`, and assert the function does not return that path. Can be tested without macOS by injecting `run_subprocess`.
- Residual risk: The compiler toolchain on the machine is still trusted.

### [Low] OpenAPI and 500 details describe the internals to every client

- ID: CR-017
- Severity: Low
- Domain: Security
- Evidence: `create_app` sets `docs_url=None` and `redoc_url=None` but leaves `openapi_url` at the FastAPI default. Live `GET /openapi.json` returned **200** and a path map. `v1_snapshot` (`src/sentry_ai/api/routes_v1.py` lines 49–55) returns `500` with `f"{type(exc).__name__}: {exc}"`. The WebSocket loop (lines 88–97) does not catch that exception, so the same failure drops the socket with no structured error. `/api/snapshot` does not wrap assemble in that try/except (`src/sentry_ai/api/routes_detection.py` lines 65–72); behavior differs between the alias and `/v1/snapshot`.
- Attack / failure story: Anyone who can reach the port reads the full route list. A store bug that raises during assemble puts the exception text on the wire (paths, dtype messages, whatever `str(exc)` contains).
- Impact: Recon and occasional internal strings. No secrets by design, unless a future exception embeds the RTSP URL (CR-006 is the direct leak).
- Likelihood: Certain for OpenAPI; low for the 500 path.
- Fix: Set `openapi_url=None` on the serve app (tests can mount a schema if they need it). Return a fixed 500 detail. Catch assemble errors on the socket and skip the frame.
- Tests that would have caught it: `TestClient` `GET /openapi.json` is 404. Assemble raising produces a detail that does not contain the exception text.
- Residual risk: The source is public. Hiding the schema is hygiene, not a security boundary.

### [Info] The online consent flag does not gate anything on this SHA

- ID: CR-018
- Severity: Info
- Domain: Backend
- Evidence: `CalibrationState.set_online` / `is_online` (`src/sentry_ai/control/calibration_state.py` lines 165–181 and 183–190) are only referenced inside that class. `DepthLoop` never calls `is_online`. No route posts `/api/depth/calibration/online`. `api_status` (`src/sentry_ai/api/routes_preview.py` lines 193–213) copies `calibration_active` and persist fields and does not copy `snap.online`. The calibration GET snapshot does include `online` (seen as `"online": false` on the live server). `clear_applied` forces the flag off. `.planning/phases/19-online-consent-honesty-state/19-02-PLAN.md` still describes the REST toggle and status fields as future work. That matches the code: 19-02 is not on `main`.
- Attack / failure story: A reader of the 19-01 summary believes consent is required before metric scale or before a later online update. On this tree, `set_online(True)` is unreachable from HTTP, and metric scale still comes only from `apply` / `try_reapply`. The flag cannot be turned on by an attacker either. The hazard is a false sense that a consent gate already exists.
- Impact: None on the wire today, beyond a field that is always false on the calibration GET. Do not document `calibration_online` as live status.
- Likelihood: Certain that the gate is absent. Not a vulnerability.
- Fix: Keep the flag default-off until 19-02 lands, and do not claim it in the operator docs. When the toggle is added, it still must not be the thing that invents the first scale (the current `online_requires_applied` check is the right shape).
- Tests that would have caught it: Already present for the in-memory flag. Add a test, when the route exists, that `GET /api/status` and the route agree. Not a gap on this SHA.
- Residual risk: Merging 19-02 without an origin check reopens CR-004 on a new POST.

## Unverified / blocked

- Physical cameras, macOS Continuity, the Swift helper actually compiling, and FFmpeg device selection. CR-016 is from the Python skip-recompile logic only.
- Real Depth Anything and YOLO forward passes. CR-001’s NaN behavior is the free-space function, not a measured model output. CR-003 used an injected module. CR-008’s pickle callee was not imported.
- In-browser CSRF delivery. Server acceptance is verified; Chrome’s mixed-content and local-network behavior was not, because the headless probe did not finish.
- PR #20 (`feat/19-02-online-status-rest`) was not part of this review.
- Whether a black USB frame produces a finite depth map that still looks “all far” (CR-001’s constant-map note). Needs a camera and the depth extra.

## Fix order

- P0 this week
  - CR-001: non-finite depth must not become a clear free-space product.
  - CR-002: clearing or erroring depth must clear free-space; MJPEG must not draw a stale occupancy or depth overlay.
  - CR-004 and CR-005: reject cross-site simple POSTs, reject foreign WebSocket origins, pin `Host` to the bind address.
  - CR-007: re-apply scale/offset gates on YAML load and refuse one-point fits that imply an empty meter horizon.
  - CR-003: do not report `unit="m"` until the metric checkpoint is the one loaded.
- P1 next
  - CR-006 and CR-014: redact RTSP userinfo; allow only `rtsp`/`rtsps` on `--source rtsp`.
  - CR-009 and CR-015: make clear and persist/apply atomic relative to the in-memory flag.
  - CR-008: hash-pin known weights before `YOLO` / `from_pretrained`.
  - CR-010 and CR-012: meter mode must not present ordinal sliders as live; Clear confirms; Apply’s persistence matches the toast.
- P2 backlog
  - CR-011 and CR-013: honest drop count; stale MJPEG.
  - CR-016 and CR-017: helper digest; hide OpenAPI and exception strings.
  - CR-018: leave the online flag unwired until its route exists, then put it behind the same origin checks.

## Regression tests to add

- All-NaN and all-inf depth maps, relative and `METRIC_CALIBRATED`: `error` set, free mask null, `completeness.free_space` false.
- `DepthLoop.set_enabled(False)` after a good free-space product: next assemble has no free-space payload, including at age 500 ms.
- `set_depth_mode("metric_outdoor")` after a loaded relative module does not yield `unit="m"` from the old module.
- Form-urlencoded `POST` from `Origin: https://evil.example` to `/api/depth/calibration/clear`, `/cancel`, `/compute`, `/apply` returns 403. Same-origin JSON still returns the current status codes.
- WebSocket with a non-loopback `Origin` is rejected. `Host: evil.example` on `/api/status` is 400.
- `try_reapply` of `scale=1e6` and of `offset=1e9` does not apply. Boot fingerprint with `width=None` does not apply a file whose saved width is set.
- `status_detail` for `rtsp://user:secret@host/x` does not contain `secret`. `RtspSource` rejects `file://` and `http://`.
- `delete_params` raising leaves applied state unchanged or deletes the file before clearing.
- `persist_applied` raising leaves the draft in place and applied unchanged.
- Status “drops” on a healthy 30 fps synthetic run stays at 0, or the label is not “Drops”.

## Appendix

### Files reviewed

Runtime code: `src/sentry_ai/cli.py`, `api/app.py`, `api/assemble.py`, `api/routes_preview.py`, `api/routes_v1.py`, `api/routes_calibration.py`, `api/routes_pipeline.py`, `api/routes_depth.py`, `api/routes_detection.py`, `api/routes_open_vocab.py`, `control/calibration_state.py`, `control/calibration_persist.py`, `control/pipeline_state.py`, `config/calibration_store.py`, `config/load.py`, `config/models.py`, `config/profile_runtime.py`, `config/artifact_paths.py`, `config/profiles/cpu-fallback.yaml`, `schemas/calibration.py`, `schemas/validators.py`, `schemas/perception.py` (extra=forbid confirmed), `spatial/free_space.py`, `spatial/loop.py`, `spatial/calibration.py`, `models/depth/worker.py`, `models/depth/loop.py`, `models/depth/mapping.py`, `models/depth/colormap.py`, `models/detection/yolo_worker.py`, `models/detection/yoloe_worker.py`, `models/detection/factory.py`, `models/cache.py`, `state/perception_store.py`, `bus/frame_bus.py`, `capture/loop.py`, `capture/status.py`, `sources/opencv_source.py`, `sources/ffmpeg_avfoundation.py`, `sources/avfoundation_unique.py`, `plugins/registry.py`, `ui/static/index.html`.

Docs: `docs/safety-and-privacy.md`, `docs/calibration.md`, `docs/api-reference.md`, `docs/architecture.md` was not line-audited beyond the safety and API contracts the code claims to implement; `CHANGELOG.md`; `pyproject.toml`. Phase 19 planning files were read far enough to confirm the REST toggle is 19-02 and not on this commit.

Not line-reviewed: the historical `.planning/milestones/**` corpus, export scripts, and the full test suite (tests were used as a map of intended contracts, not as evidence that the unhappy paths exist).

### Assumptions

- Consumers of `/v1/snapshot` may treat `completeness.free_space && obstacle_count==0` as “no near obstacle” even though the docs say not to use free-space as an interlock. The review judges the bytes a careful integrator still receives.
- Default bind stays `127.0.0.1`. Findings that need a LAN client are labeled that way. Browser mitigations may reduce drive-by likelihood; they are not implemented in this process.
- Placeholder `rtsp://<user>:<password>@…` in CR-006 is a pattern, not a captured secret. No real credential was present in this run.

### ASVS 5.0 / OWASP Top 10 notes

| Lens | Result |
|---|---|
| Broken access control | No authN and no authZ on any route. Documented for loopback. CR-004/005 show browsers and foreign `Host` values are inside that boundary. |
| CSRF | CR-004. JSON `PATCH` is preflight-blocked (verified). Body-less POSTs are not. |
| SSRF | No HTTP API sets a URL. CLI `--url` is CR-014. |
| Injection | Swift and FFmpeg use argv arrays. `unique_id` and the FFmpeg device index are not shell-quoted because they are not passed through a shell. No command-injection finding. |
| XSS | `index.html` writes status and calibration strings with `textContent`. No `innerHTML` sink found. Clickjacking remains (no frame policy). |
| Deserialization | `yaml.safe_load` for config and calibration. Model pickle is CR-008. |
| Security logging | Failures log raw exception strings (CR-006). No security event for calibration apply/clear. |
| Cryptography / sessions | Absent on purpose. Do not add a half session without the origin checks. |
| Data integrity | YAML replace is atomic. Clear and apply/persist are not (CR-009, CR-015). Fingerprint skips null resolution at boot (CR-007). |

### Probes executed

- `uv sync --extra dev` and `uv run sentry serve --source synthetic --host 127.0.0.1 --port 8765` from this SHA.
- curl and `urllib` against `/`, `/openapi.json`, `/api/status`, `/v1/snapshot`, `/preview/mjpeg`, and the calibration POSTs listed in CR-004, including foreign `Origin` and `Host`.
- A `websockets` handshake with a hostile `Origin` (CR-005).
- In-process proofs for CR-001 (NaN map), CR-002 (depth disable), CR-003 (mode switch), CR-007 (YAML scale and metric free-space), CR-009 (unlink failure), CR-010 (ordinal cuts ignored), CR-011 (live drops counter).

### Context corrections

- Online recal consent is not an active control on `main` (CR-018).
- `docs/calibration.md` is right that mismatch refuses a file when both widths are known, and right that Apply is session-only unless persist is requested. The UI never requests persist (CR-012), and boot compares against a null width (CR-007).
- `docs/api-reference.md` “disable clears that stage’s product” is true for the toggled stage and false for free-space derived from depth (CR-002).

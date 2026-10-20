# Server startup repair — `server/main.py`

**Date:** 2026-10-19
**Task:** Run `server/main.py`, fix the errors, and repeat until it runs cleanly.
**Result:** `server/main.py` starts and serves all routes without errors.

---

## Summary

`server/main.py` could not be imported or started. It had missing dependencies,
a bad import, a broken `__main__` block, and a WebSocket handler that raised at
runtime. Fixes were applied iteratively: run → read traceback → fix → run again.

Changed files:

| File | Change |
| --- | --- |
| `server/main.py` | Fixed imports, global state, routes, entry point, WebSocket handler, clipboard broadcast |
| `web/index.html` | Fixed a stray character that was a JavaScript syntax error |
| `smoke_test.py` | New: HTTP + WebSocket smoke test used for verification (optional, delete if unwanted) |

Dependencies installed into the environment (Python 3.15, global interpreter):
`aiohttp`, `pyperclip`, `PyNaCl`, `qrcode`, `Pillow`, `spake2`, `pytest`,
`pytest-asyncio`, `Werkzeug`.

---

## Errors encountered, in order, and their fixes

### 1. `ModuleNotFoundError: No module named 'aiohttp'`

No project dependencies were installed. Installed the full `requirements.txt`
set plus `Pillow` (the `[pil]` extra of `qrcode`) and the dev/test packages.

### 2. `ImportError: cannot import name 'WebProtocol' from 'aiohttp.web_protocol'`

`main.py` imported names it never used. Removed:

```python
# before
from aiohttp import web, WSMsgType, web_protocol
from aiohttp.web_protocol import WebProtocol

# after
from aiohttp import web, WSMsgType
```

### 3. `ModuleNotFoundError: No module named 'server'`

Running the script directly puts `server/` on `sys.path`, not the repository
root, so `from server.crypto import ...` failed. Added a bootstrap so both
`python server/main.py` and `python -m server.main` work:

```python
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
```

### 4. Broken pairing imports

`server/pairing.py` does not export `get_paired_devices`, `add_paired_device`,
or `remove_paired_device`. Replaced with names that actually exist, and added
the ones the WebSocket pairing flow needs:

```python
from server.pairing import (
    paired_devices,
    get_all_paired_devices,
    revoke_device,
    start_code_pairing,
    complete_code_pairing,
    start_qr_pairing,
    PairingError,
)
from server.clipboard_api import set_clipboard
```

### 5. Undefined globals at runtime

`paired_devices` was used but never defined in the module, and
`active_connections` / `secrets` were used but never imported. Added the import
of `paired_devices` (from `server.pairing`) and declared the process-wide state:

```python
sessions = {}
connection_states = {}
active_connections = {}
_event_loop = None
```

### 6. Broken `__main__` block

The entry point sat in the middle of the file (before most handlers were
defined), referenced those not-yet-defined functions, and launched an empty
`web.Application()` with no routes registered. Moved it to the end of the file
and made it build the real app:

- `setup_routes()` converted to a synchronous function and called from
  `init_app()` (previously `await`ed).
- The entry point now registers routes, starts clipboard polling in
  `on_startup`, stops it in `on_cleanup`, then calls `web.run_app()`.

### 7. Non-functional WebSocket handler

Several distinct defects:

- `web.WebSocketResponse(ssl=...)` and `ws.prepare(request, ssl_context=...)`
  are not valid arguments (raised `TypeError` on connect). Replaced with a
  plain `WebSocketResponse(heartbeat=...)`.
- `session_data['send_box']` / `['recv_box']` were read but never populated,
  so `encrypt`/`decrypt` raised `KeyError`. The handler now establishes a real
  session via `establish_session_reconnect()` on connect/`code_input`.
- `relay_encrypted_message()` did not exist (`NameError`). Implemented it to
  forward sealed ciphertext to other connected devices.
- Unpaired devices received an error and the connection was broken with
  `break`. Now the server replies with `pairing_info` (a 6-char code)
  and keeps the connection open.
- `handle_connection_drop(device_id)` was called with the wrong number of
  arguments. Fixed to use the stored device key, and made the disconnect path
  tolerant of failures.
- `json.loads(msg.data)` could raise on malformed input; now guarded.
- Empty/`None` clipboard payloads could crash `payload[:50]`; now guarded.
- `finally` block cleaned up `active_connections` and connection tracking
  safely via `.pop(..., None)` and `remove_connected_phone()`.

### 8. Clipboard poller ran with no event loop

The poller calls its callback from a worker thread, where
`asyncio.get_event_loop()` raises:

```
ERROR:__main__:Could not broadcast clipboard change:
There is no current event loop in thread 'Thread-1 (_poll_loop)'
```

The running loop is now captured at startup and the callback schedules work back
onto it:

```python
async def _on_startup(app):
    global _event_loop
    _event_loop = asyncio.get_running_loop()
    ...

def _broadcast_local_clipboard(content):
    loop = _event_loop
    if loop is None or loop.is_closed():
        return
    asyncio.run_coroutine_threadsafe(relay_clipboard_change(content, 'pc'), loop)
```

### 9. `GET /api/qr` returned 500

`qrcode.make()` needs an image backend. Installed `Pillow` (satisfying
`qrcode[pil]` in `requirements.txt`) and added an SVG fallback so the endpoint
cannot hard-fail if the PNG backend is unavailable.

### 10. JavaScript syntax error in the served UI

`web/index.html` contained a stray `n`:

```js
hideError();n            updateStatus('Verifying pairing code...', false);
```

This broke the whole inline script block. Removed the stray character.

---

## Routes served after the fix

| Route | Purpose |
| --- | --- |
| `GET /` | Phone UI (`web/index.html`) |
| `GET /crypto.js` | Browser crypto helper (`web/crypto.js`) |
| `GET /health` | JSON health/status |
| `GET /ws` | Encrypted WebSocket transport |

## WebSocket message flow (verified)

```
client -> {"type": "hello", "device_id": "..."}
server -> {"type": "pairing_info", "code": "..."}                      # if unpaired
client -> {"type": "code_input", "code": "..."}
server -> {"type": "connected", "device_id": "...", "status": "connected"}

client -> {"type": "hello", "device_id": "..."}                       # if paired
server -> {"type": "ready", ...}
server -> {"type": "connected", ...}

encrypt / decrypt / ping / clipboard_request / clipboard_history /
clipboard_send / clipboard_change are all handled.
```

---

## Verification

`smoke_test.py` starts `server/main.py` as a subprocess, waits for `/health`,
then exercises HTTP and WebSocket endpoints:

```
health: {'status': 'healthy', 'active_connections': 0, 'paired_devices': 0}
GET /                -> 200
GET /crypto.js       -> 200
GET /health          -> 200
hello                -> pairing_info
code_input           -> connected
encrypt              -> ack
ping                 -> pong
clipboard_history    -> history_data
clipboard_request    -> clipboard_data
clipboard_send       -> clipboard_received
reconnect (paired)   -> ready connected

SMOKE TEST PASSED
```

Server stderr after a full run contains only `INFO` lines — no tracebacks and no
`ERROR` lines. A direct launch also succeeds:

```
======== Running on http://127.0.0.1:8044 ========
(Press CTRL+C to quit)
GET /health -> 200 {"status": "healthy", ...}
```

Run it with:

```bash
python smoke_test.py
```

---

## Follow-up: QR code removed

After the server was confirmed working end-to-end, the QR display was removed
from the phone UI (the QR never rendered scannable output anyway — the server
sent a text URL rather than an image).

Removed:

- `web/index.html`
  - The `.qr-container` block (`Scan PC QR Code` heading, `<img id="qr-image">`,
    its `onerror` placeholder SVG, and the caption).
  - The `code-section` is now visible by default (was `class="hidden"`), with the
    heading changed to `Enter pairing code:`.
  - JS: `displayQRCode()`, `startQRCodeRefresh()`, the `data.qr_code` branch in
    `handlePairingInfo()`, and the `appState.qrCode` / `appState.qrRefreshInterval`
    fields and their cleanup.
  - CSS: the `.qr-container` and `#qr-image` rules.
- `server/main.py`
  - Route `GET /api/qr` and the `serve_qr()` handler.
  - `qr_code` from the `pairing_info` message, and the `qr_request` WebSocket
    handler (both existed only for the QR display).
  - The `start_qr_pairing` import.
  - The QR markup in the inline fallback homepage (only used if
    `web/index.html` is missing).
- `smoke_test.py`: dropped `/api/qr` from the checked routes.

Pairing is unchanged and still works through the 6-character code:
`hello` → `pairing_info` (code) → `code_input` → `connected`.

Follow-up verification:

```
GET /                -> 200
GET /crypto.js       -> 200
GET /health          -> 200
hello                -> pairing_info ['code']
code_input           -> connected
... (all other checks unchanged)

SMOKE TEST PASSED
```

Note: `qrcode` / `Pillow` are no longer used by the server, but remain listed in
`requirements.txt` and are still used by `server/pairing.py`.

---

## Known pre-existing issues (NOT changed)

These are unrelated to running `server/main.py` and were left alone:

- `tests/test_pairing.py` fails to import. It references functions that do not
  exist in `server/pairing.py` (`generate_qr_code`, `scan_qr_code`,
  `generate_code`, `get_session_key`, `clear_expired_codes`).
- `tests/test_crypto.py` has 4 failures, because `server/crypto.py` is the
  documented "simplified for testing" implementation:
  - `derive_shared_secret()` is not symmetric (`a·B` != `b·A`).
  - `SealedBox` does not actually use the key, so wrong-key decryption succeeds.
  - Device/session keys are not consistent between the two handshake sides.
  These are consistent with the caveats in `README.md` and `CODE_ANALYSIS.md`.

---

## Notes

- Dependencies were installed into the **global** Python 3.15 interpreter. A
  `.venv` was created but its `ensurepip` hung, and it was removed afterwards.
- The repository tracks some `__pycache__/*.pyc` files; those were restored
  rather than deleted.

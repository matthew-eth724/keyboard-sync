# ClipSync — Encrypted Clipboard Sync

PC ↔ phone clipboard synchronization over your local network with end-to-end encryption. Copy on the PC, it appears on the phone. Send text from the phone to the PC with one tap. No accounts, no cloud.

> Prototype implementation following `PLAN.md`. Current crypto is simplified for testing; see Security Notes.

## Goals

- Copy on PC → automatically appears on paired phone(s)
- Send text from phone to PC clipboard with one tap
- Pair once via QR code or 6-character fallback code
- End-to-end encrypted; nothing readable crosses the network
- Local-only, no accounts, no cloud

Non-goals: remote access outside LAN, images/files, native mobile app, multi-PC setups.

## Architecture

```
Phone (browser)                         PC (Python)
┌──────────────┐   encrypted WS msgs   ┌──────────────────┐
│ UI           │ <───────────────────> │ aiohttp server   │
│ libsodium.js │                       │ PyNaCl           │
│ IndexedDB    │                       │ clipboard watcher│
│ (keys)       │                       │ device store     │
└──────────────┘                       └──────────────────┘
```

PC responsibilities: serve the web UI, run pairing, poll clipboard, relay encrypted messages, store paired devices.

Phone responsibilities: pair, hold long-term key in IndexedDB, display incoming items, send text on tap.

Transport: WebSocket over local network, plain HTTP for now. Crypto: libsodium / PyNaCl on PC, libsodium-wrappers in browser.

## Project Structure

```
keyboard-sync/
├── server/
│   ├── main.py          # aiohttp app, WebSocket routes, encrypted transport
│   ├── pairing.py       # QR/code pairing, expiry, attempt limits
│   ├── crypto.py        # handshake, session keys, seal/open
│   ├── clipboard.py     # watcher, history, dedupe, echo prevention
│   ├── devices.py       # paired-device store, revoke, sessions
│   └── polling.py
├── web/
│   ├── index.html       # Phone PWA UI
│   ├── app.js           # WebSocket client, UI logic
│   └── crypto.js        # libsodium wrapper mirroring server/crypto.py
├── tests/
│   ├── test_crypto.py
│   ├── test_pairing.py
│   └── test_m4_clipboard.py
├── requirements.txt
├── PLAN.md
└── CODE_ANALYSIS.md
```

## Installation

```bash
cd /data/home/keyboard-sync
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` includes:
- `aiohttp>=3.9.0`
- `pyperclip>=1.9.0`
- `PyNaCl>=1.5.0`
- `qrcode[pil]>=7.4.0`
- `spake2`

Clipboard backend notes:
- Linux: `xclip`, `xsel`, or `wl-clipboard` required for pyperclip
- macOS / Windows work out of the box

## Running

Start the server:

```bash
python -m server.main --host 0.0.0.0 --port 8000
```

Default: http://localhost:8000

Open the served page on your phone in the same LAN, e.g. http://<pc-ip>:8000

API:
- `GET /` — phone UI
- `GET /ws` — WebSocket for encrypted sync
- `GET /health` — health check

## Pairing Flow

### QR code, primary

1. On PC, click "Pair new device". A QR appears encoding `http://<ip>:8000/#p=<secret>&h=<hostname>`.
2. Secret is in URL fragment, never sent over network.
3. Phone scans QR. Page reads fragment, both sides run handshake.
4. On success, both store long-term device key; pairing secret discarded.

QR rules:
- Single use, expires after 2 minutes
- Rate-limited per IP

### 6-character code, fallback

- Uppercase letters/digits excluding lookalikes `0 O 1 I L`
- ~729M combinations, paired via PAKE SPAKE2
- Expires after 2 minutes, 3 failed attempts kills code
- Pairing mode must be actively open

Handshake summary:
- X25519 key exchange, pairing secret bound via keyed BLAKE2b
- Per-session ephemeral X25519 keys → forward secrecy
- Messages sealed with XChaCha20-Poly1305, counter-based nonces for replay protection

## Usage

**PC → Phone**
- Copy text on PC. Server polls clipboard ~500 ms and pushes encrypted message to connected phones.
- History kept last 20 items, deduplicated by SHA-256 hash. Echo loops prevented.

**Phone → PC**
- Type in "Send to PC" field and tap Send, or paste from phone and tap Send.
- Phone browser needs user tap for clipboard access.

Pairing UI shows connection status, connected devices, current clipboard, and device ID.

## Security Notes

Design goals from PLAN.md:
- Pairing handshake binds X25519 keys to pairing secret with BLAKE2b
- Per-session keys with forward secrecy via ephemeral X25519
- XChaCha20-Poly1305 seal/open, counter-based nonces reject replay/reordering
- Device keys stored on PC with restricted permissions; phone stores in IndexedDB

Current implementation caveats:
- Crypto core in `server/crypto.py` uses simplified SHA-256 substitutes for BLAKE2b/X25519/XChaCha20-Poly1305 for testing. See `CODE_ANALYSIS.md`.
- Plain HTTP transport means the page JavaScript can be tampered by an active LAN attacker. Option B local HTTPS recommended for production.
- No images/files, size cap 1 MB per message.

## Testing

```bash
pytest tests/
```

Unit tests cover:
- Crypto: key generation, handshake, seal/open, replay detection
- Pairing: QR parsing, expiry, attempt limits, code flow
- Clipboard: history, dedupe, echo prevention, device isolation
- Devices: add/revoke, session limits

Run manual verification:
```bash
python server/crypto.py
python server/pairing.py
python server/clipboard.py
python server/devices.py
```

## Milestones

- M1 Crypto core — handshake, session derivation, seal/open ✅ mostly implemented
- M2 Pairing — QR + code flow ✅ mostly implemented
- M3 Encrypted transport — WebSocket with fresh sessions ✅ mostly implemented
- M4 Clipboard logic — history, dedupe, echo prevention ✅ complete
- M5 Device management — paired list, revoke ✅ complete

## Risks & Open Questions

- SPAKE2 interoperability between Python `spake2` and JS implementation
- Active LAN attacker can tamper page JS on plain HTTP; mitigate with local HTTPS
- IP changes invalidate QR; hostname fallback helps
- Browser background tabs may drop WebSocket; reconnect logic present

## License

Prototype. See repository for details.

# ClipSync: Project Plan

Encrypted clipboard sync between a PC and a phone over the local network.

## 1. Goals

- Copy on the PC and the text shows up on the phone automatically.
- Send text from the phone to the PC clipboard with one tap.
- Pair once with a QR code (or a short fallback code); no accounts, no cloud.
- End-to-end encrypted. Nothing readable crosses the network.

**Non-goals (for now):** remote access outside the LAN, images and files, a native mobile app, multi-PC setups.

## 2. Decisions

| Area | Decision |
|---|---|
| PC | Python: `aiohttp`, `pyperclip`, `PyNaCl`, `qrcode`, `spake2` |
| Phone | PWA-style web page served by the PC, added to the home screen |
| Transport | WebSocket over the local network, plain `http` (Option A) |
| Crypto | libsodium on both sides (PyNaCl / `libsodium-wrappers`) |
| Pairing | QR code (primary), 6-character code via PAKE (fallback) |
| Discovery | IP and `.local` hostname carried in the QR; no mDNS needed from the browser |

### Why Option A (plain http)

Browsers only expose `crypto.subtle`, service workers, and `navigator.clipboard` on HTTPS. Plain http means we use libsodium.js for all crypto and live without those APIs. The phone page can be added to the home screen but is not a true installable PWA.

**Accepted risk:** an attacker actively tampering with LAN traffic could alter the page's JavaScript and steal the key. Passive sniffing is fully covered. Moving to local HTTPS (Option B) later closes this gap and does not change the protocol.

## 3. Architecture

```
 Phone (browser)                         PC (Python)
 ┌──────────────┐   encrypted WS msgs   ┌──────────────────┐
 │ UI           │ <───────────────────> │ aiohttp server   │
 │ libsodium.js │                       │ PyNaCl           │
 │ IndexedDB    │                       │ clipboard watcher│
 │ (keys)       │                       │ device store     │
 └──────────────┘                       └──────────────────┘
```

PC responsibilities: serve the page, run pairing, poll the clipboard, relay encrypted messages, keep the paired-device list.

Phone responsibilities: pair, hold the key in IndexedDB, show incoming items, send text on tap.

## 4. Pairing

### QR flow (primary)

1. User clicks "Pair new device" on the PC.
2. PC generates a random 256-bit pairing secret and shows a QR encoding `http://<ip>:8000/#p=<secret>&h=<hostname>`.
3. The secret is in the URL fragment, which browsers never send over the network.
4. Phone scans, the page reads the fragment, and both sides run the handshake in section 5.
5. On success, both store a long-term device key and each other's device ID. The pairing secret is discarded.

### Code flow (fallback)

- 6 characters, uppercase letters and digits, excluding lookalikes (`0 O 1 I L`), roughly 729 million combinations.
- Used with a PAKE (SPAKE2) so the code cannot be brute-forced offline.
- On success, the PAKE output acts as the pairing secret and the flow continues as above.

### Pairing rules

- Single use; expires after 2 minutes.
- Three failed attempts kill the code and the PC generates a new one.
- Pairing mode must be actively open on the PC; no always-on code.
- Rate-limit pairing attempts per IP.

## 5. Encryption design

**Pairing handshake:** both sides exchange X25519 public keys, bind them to the pairing secret with a keyed hash (BLAKE2b via `crypto_generichash`), and each side proves it knows the secret. A mismatch aborts pairing.

**Per-session keys:** on every connection, both devices exchange fresh ephemeral X25519 keys. Session keys derive from the Diffie-Hellman result mixed with the stored device key, using `crypto_generichash` as the KDF and separate keys per direction. This gives forward secrecy, so recorded traffic stays unreadable even if a device key leaks later.

**Messages:** sealed with XChaCha20-Poly1305 (`crypto_aead_xchacha20poly1305_ietf`). Nonces are counters per direction; reject any message whose counter is not strictly greater than the last seen one (blocks replay and reordering).

**Key storage:** PC keeps device keys in a file with restricted permissions; phone keeps them in IndexedDB.

## 6. Message format

Decrypted payload is JSON:

```json
{
  "id": "uuid",
  "type": "text",
  "payload": "copied text here",
  "ts": 1760000000,
  "device": "device-id",
  "hash": "sha256-of-payload"
}
```

- `type` is `text` for now; `image` and `file` are reserved for later.
- Size cap per message (start at 1 MB).
- Last writer wins. The content hash plus a "last applied hash" prevents echo loops.

## 7. Clipboard behavior

- PC polls the clipboard every ~500 ms; changes are encrypted and pushed to connected phones.
- Phone to PC: the user taps Send, and the PC sets its clipboard.
- History of the last 20 items on both sides, deduplicated by hash.
- Phone side needs a tap to copy (no background clipboard access in browsers).

## 8. Project structure

```
clipsync/
├── PLAN.md
├── requirements.txt
├── server/
│   ├── main.py          # aiohttp app, routes
│   ├── pairing.py       # QR/code pairing, PAKE, attempt limits
│   ├── crypto.py        # handshake, session keys, seal/open
│   ├── clipboard.py     # watcher, history, dedupe
│   ├── devices.py       # paired-device store, revoke
│   └── tray.py          # system tray icon (later)
├── web/
│   ├── index.html
│   ├── app.js           # UI and WebSocket
│   └── crypto.js        # libsodium wrapper, mirrors crypto.py
└── tests/
    ├── test_crypto.py
    └── test_pairing.py
```

## 9. Milestones

### M1: Crypto core
Handshake, session key derivation, seal/open in both Python and JS.
**Done when:** a Python-encrypted message decrypts in the browser and vice versa, replayed messages are rejected, and tampered ciphertext fails.

### M2: Pairing
QR generation and scan flow, then the 6-character code flow.
**Done when:** a fresh phone pairs via QR, codes expire after 2 minutes and die after 3 bad guesses, and wrong secrets never produce a session.

### M3: Encrypted transport
Replace the current plaintext WebSocket messages with sealed ones; reconnect with a fresh session each time.
**Done when:** a packet capture shows only ciphertext and the app still syncs after a dropped connection.

### M4: Clipboard logic
History, dedupe, echo prevention, size limits.
**Done when:** copying the same text repeatedly does not spam the phone, and no send loops occur.

### M5: Device management
Paired-device list, revoke, system tray icon.
**Done when:** a revoked device can no longer open a session.

## 10. Testing

- Unit tests for crypto: known-answer vectors, replay, tamper, wrong key.
- Cross-implementation tests: Python and JS must agree on the handshake and message format.
- Pairing tests: expiry, attempt limits, reuse of a used code.
- Manual: capture traffic with Wireshark and confirm nothing readable; try pairing from a second phone with a wrong code.

## 11. Risks and open questions

- **SPAKE2 interoperability:** the Python `spake2` library and a JavaScript implementation must use matching group parameters and identity handling. Verify a maintained JS library exists and interoperates before M2's code flow. Fallback: use a longer code (about 16 base32 characters) with no PAKE.
- **Active LAN attacker (Option A):** tampered page JavaScript can steal keys. Mitigation path is Option B (local HTTPS).
- **IP changes:** the IP in the QR can go stale; the hostname helps, and re-scanning is the fallback.
- **OS clipboard quirks:** Linux needs `xclip`, `xsel`, or `wl-clipboard`; macOS and Windows work out of the box.
- **Phone browser limits:** background tabs may drop the WebSocket; reconnect logic must be solid.
- **Libsodium.js on plain http:** confirm the WASM build loads in a non-secure context on target phones, with the asm.js fallback as backup.

## 12. Later

- Image and file support (chunked transfer).
- Remote access via Tailscale, or an encrypted relay.
- Local HTTPS for a full PWA.
- Native Android app for background sync.

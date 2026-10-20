#!/usr/bin/env python3
"""Smoke test for server/main.py: starts the server and exercises all routes."""

import asyncio
import os
import subprocess
import sys
import tempfile
import time

import aiohttp

HOST = "127.0.0.1"
PORT = 8033
BASE = f"http://{HOST}:{PORT}"


async def wait_for_server(timeout=30.0):
    deadline = time.time() + timeout
    async with aiohttp.ClientSession() as session:
        while time.time() < deadline:
            try:
                async with session.get(f"{BASE}/health") as resp:
                    if resp.status == 200:
                        return await resp.json()
            except Exception:
                pass
            await asyncio.sleep(0.3)
    raise RuntimeError("server did not become ready")


async def exercise():
    async with aiohttp.ClientSession() as session:
        for path in ("/", "/crypto.js", "/health"):
            async with session.get(f"{BASE}{path}") as resp:
                body = await resp.read()
                print(f"GET {path} -> {resp.status} ({len(body)} bytes)")

        async with session.ws_connect(f"{BASE}/ws") as ws:
            await ws.send_json({"type": "hello", "device_id": "phone-smoke"})
            msg = await ws.receive_json(timeout=10)
            print("hello ->", msg.get("type"), sorted(k for k in msg if k != "type"))
            assert msg["type"] == "pairing_info", msg
            code = msg["code"]

            await ws.send_json({"type": "code_input", "code": code})
            msg = await ws.receive_json(timeout=10)
            print("code_input ->", msg)

            await ws.send_json({"type": "encrypt", "payload": "hello from smoke"})
            print("encrypt ->", await ws.receive_json(timeout=10))

            await ws.send_json({"type": "ping"})
            print("ping ->", await ws.receive_json(timeout=10))

            await ws.send_json({"type": "clipboard_history", "limit": 5})
            print("clipboard_history ->", await ws.receive_json(timeout=10))

            await ws.send_json({"type": "clipboard_request"})
            print("clipboard_request ->", await ws.receive_json(timeout=10))

            await ws.send_json({"type": "clipboard_send", "content": "from phone"})
            print("clipboard_send ->", await ws.receive_json(timeout=10))

        # Reconnect with the same (now paired) device to exercise that branch.
        async with session.ws_connect(f"{BASE}/ws") as ws:
            await ws.send_json({"type": "hello", "device_id": "phone-smoke"})
            first = await ws.receive_json(timeout=10)
            second = await ws.receive_json(timeout=10)
            print("reconnect ->", first["type"], second["type"])
            assert first["type"] == "ready", first
            assert second["type"] == "connected", second


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    err_file = tempfile.NamedTemporaryFile(
        "w+", suffix=".err.log", delete=False, encoding="utf-8"
    )
    out_file = tempfile.NamedTemporaryFile(
        "w+", suffix=".out.log", delete=False, encoding="utf-8"
    )
    proc = subprocess.Popen(
        [sys.executable, "-u", "server/main.py", "--host", HOST, "--port", str(PORT)],
        cwd=here,
        stdout=out_file,
        stderr=err_file,
    )
    ok = True
    try:
        print("health:", asyncio.run(wait_for_server()))
        asyncio.run(exercise())
        print("\nSMOKE TEST PASSED")
    except Exception as exc:
        ok = False
        print("\nSMOKE TEST FAILED:", type(exc).__name__, exc)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        time.sleep(0.5)
        err_file.flush()
        out_file.flush()
        err_file.seek(0)
        out_file.seek(0)
        print("\n--- server stderr ---")
        print(err_file.read())
        err_path = err_file.name
        out_path = out_file.name
        err_file.close()
        out_file.close()
        for path in (err_path, out_path):
            try:
                os.unlink(path)
            except OSError:
                pass
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

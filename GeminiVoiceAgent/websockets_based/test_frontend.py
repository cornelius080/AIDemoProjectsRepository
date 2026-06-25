"""
test_frontend.py  —  UI mock server
=====================================
Launches two servers:

  1. HTTP server   (port 8091) — serves static files in ./frontend/
  2. WebSocket     (port 8765) — mock Gemini bridge (no real API calls)

When the browser sends a text message, the mock server streams back
a fake reply word-by-word so you can test the streaming chat UI.

Open http://localhost:8091 in your browser, then press Ctrl+C to stop.
"""

import asyncio
import http.server
import json
import os
import socketserver
import sys
import threading

import websockets

# ─── Configuration ───────────────────────────────────────────────────
HTTP_PORT    = 8091
WS_PORT      = 8765
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

# A pool of canned replies to cycle through
_MOCK_REPLIES = [
    "Sure! This is a simulated response from the Gemini Live mock server. "
    "The real model will answer here once you connect it.",

    "That's an interesting question! In a real session Gemini would stream "
    "audio back to you and you'd hear the answer spoken aloud.",

    "Great, the UI is working correctly. Text bubbles stream in word by word, "
    "just like the live API would send transcription chunks.",

    "Feel free to send more messages to test the conversation layout. "
    "User messages appear on the right, assistant replies on the left.",
]
_reply_index = 0


# ─── HTTP server ─────────────────────────────────────────────────────
class _FrontendHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def log_message(self, format, *args):   # silence request logs
        pass


def _run_http_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", HTTP_PORT), _FrontendHandler) as httpd:
        httpd.serve_forever()


# ─── WebSocket mock bridge ────────────────────────────────────────────
async def _mock_handler(websocket):
    """Handle one browser connection with fake streaming replies."""
    global _reply_index
    addr = getattr(websocket, "remote_address", "unknown")
    print(f"  [WS] client connected: {addr}")

    try:
        async for raw in websocket:
            if not isinstance(raw, str):
                continue            # ignore binary frames for now

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if msg.get("type") != "text":
                continue

            user_text = msg.get("content", "").strip()
            if not user_text:
                continue

            print(f"  [WS] user said: {user_text!r}")

            # --- stream back a mock reply word by word ---
            reply = _MOCK_REPLIES[_reply_index % len(_MOCK_REPLIES)]
            _reply_index += 1

            words = reply.split()
            for i, word in enumerate(words):
                chunk = word if i == 0 else " " + word
                await websocket.send(json.dumps({
                    "type":    "assistant_text",
                    "content": chunk,
                }))
                await asyncio.sleep(0.07)   # simulate streaming delay

            # Signal end of the assistant's turn
            await websocket.send(json.dumps({"type": "turn_complete"}))
            print(f"  [WS] mock reply sent ({len(words)} words)")

    except websockets.exceptions.ConnectionClosedOK:
        pass
    except websockets.exceptions.ConnectionClosedError as exc:
        print(f"  [WS] connection closed with error: {exc}")
    finally:
        print(f"  [WS] client disconnected: {addr}")


# ─── WebSocket server ────────────────────────────────────────────────
async def _run_ws_server():
    async with websockets.serve(_mock_handler, "localhost", WS_PORT):
        print(f"  WebSocket (mock)  →  ws://localhost:{WS_PORT}")
        await asyncio.Future()      # run forever


# ─── Main ─────────────────────────────────────────────────────────────
async def _main():
    if not os.path.isdir(FRONTEND_DIR):
        print(f"Error: frontend/ directory not found at '{FRONTEND_DIR}'.")
        sys.exit(1)

    # HTTP in a daemon thread
    threading.Thread(target=_run_http_server, daemon=True).start()

    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║   Gemini Live — UI Mock Test Server      ║")
    print("  ╚══════════════════════════════════════════╝")
    print()
    print(f"  Frontend (HTTP)   →  http://localhost:{HTTP_PORT}")

    try:
        await _run_ws_server()
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    print("\nPress Ctrl+C to stop.\n")
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        print("\nStopping…  Done.")
        sys.exit(0)

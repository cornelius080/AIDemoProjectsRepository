"""
main.py
================
Launches two servers simultaneously:

  1. HTTP server  (port 8091)  — serves the static files in ./frontend/
  2. WebSocket server (port 8765) — bridges the browser to Gemini Live API

Open your browser at http://localhost:8091 after running this script.
Press Ctrl+C to stop both servers cleanly.
"""

import asyncio
import http.server
import socketserver
import os
import sys
import threading
import time

import websockets

# Import the bridge class from gemini_live.py (same directory)
sys.path.insert(0, os.path.dirname(__file__))
from gemini_live import GeminiLiveBridge

# ─── Configuration ────────────────────────────────────────────────────
HTTP_PORT  = 8091
WS_PORT    = 8765
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")


# ─── HTTP server (serves the frontend/ folder) ────────────────────────
class _FrontendHandler(http.server.SimpleHTTPRequestHandler):
    """Serve files from the frontend directory."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    # Silence request logs — comment out to re-enable
    def log_message(self, format, *args):  # noqa: A002
        pass


def _run_http_server():
    """Run the HTTP server in a daemon thread."""
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", HTTP_PORT), _FrontendHandler) as httpd:
        httpd.serve_forever()


# ─── WebSocket server (Gemini Live bridge) ────────────────────────────
async def _run_ws_server():
    """Start the WebSocket server and keep it running until cancelled."""
    bridge = GeminiLiveBridge(
        model="gemini-3.1-flash-live-preview",
        system_instruction="You are a helpful and friendly AI assistant.",
    )

    async with websockets.serve(bridge.handle_client, "localhost", WS_PORT):
        print(f"  WebSocket server  →  ws://localhost:{WS_PORT}")
        await asyncio.Future()   # run forever


# ─── Entry point ──────────────────────────────────────────────────────
async def _main():
    if not os.path.isdir(FRONTEND_DIR):
        print(f"Error: frontend directory not found at '{FRONTEND_DIR}'.")
        sys.exit(1)

    # Start HTTP server in a background daemon thread
    http_thread = threading.Thread(target=_run_http_server, daemon=True)
    http_thread.start()

    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║      Gemini Live — Frontend Test     ║")
    print("  ╚══════════════════════════════════════╝")
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
        print("\nStopping servers…  Done.")
        sys.exit(0)

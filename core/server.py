import threading
import websockets
from db import SystemDB
from collections import defaultdict
import asyncio


import asyncio
import time
import traceback
from collections import defaultdict

import websockets


class SystemReceiver:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self._host = host
        self._port = port

        self.db = SystemDB()
        self.clients: set[websockets.WebSocketServerProtocol] = set()
        self.msg_count = defaultdict(int)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    # ─────────── per‑connection handler ─────────── #

    async def handler(self, ws: websockets.WebSocketServerProtocol, _path: str) -> None:
        self.clients.add(ws)
        peer = f"{ws.remote_address[0]}:{ws.remote_address[1]}"
        print(f"✓ {peer} connected  (now {len(self.clients)} clients)")
        try:
            async for msg in ws:
                self.msg_count[ws] += 1
                print(f"[{peer} #{self.msg_count[ws]}] {len(msg)} bytes")
        except websockets.ConnectionClosedOK:
            pass
        except Exception as exc:
            print(f"‽ handler error from {peer}: {exc}")
        finally:
            self.clients.discard(ws)
            print(f"✗ {peer} disconnected (now {len(self.clients)} clients)")

    # ───────────── supervisor loop ───────────── #

    def _run_forever(self, host: str, port: int) -> None:
        print(f"WebSocket server supervising on ws://{host}:{port}")
        while True:
            loop = asyncio.new_event_loop()
            self._loop = loop                      # remember it for stop()
            asyncio.set_event_loop(loop)
            try:
                server_coro = websockets.serve(self.handler, host, port)
                server = loop.run_until_complete(server_coro)
                print("Server started, entering run‑forever()")
                loop.run_forever()
            except KeyboardInterrupt:
                print("Interrupted – shutting down.")
                server.close()
                loop.run_until_complete(server.wait_closed())
                break
            except Exception:
                print("‼︎  Event‑loop crashed; restarting in 2 s")
                traceback.print_exc()
            finally:
                loop.call_soon(loop.stop)
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
                self.clients.clear()
                self.msg_count.clear()
                time.sleep(2)

    # ───────────── public control API ───────────── #

    def start(self) -> None:
        """
        Launch the WebSocket server in a background thread and return immediately.
        Call `stop()` to shut it down.
        """
        if self._thread and self._thread.is_alive():
            print("SystemReceiver is already running.")
            return

        print(f"Starting SystemMonitor on {self._host}:{self._port} (threaded)")
        self._thread = threading.Thread(
            target=self._run_forever,
            args=(self._host, self._port),
            name="SystemReceiver",
        )
        self._thread.start()

    def stop(self, timeout: float | None = None) -> None:
        """Politely stop the server and wait for the thread to finish."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout)
            self._thread = None
        print("SystemMonitor stopped.")
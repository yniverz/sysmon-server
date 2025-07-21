import json
import threading
import websockets
from db import SystemDB
from collections import defaultdict
import asyncio
from models import System, SystemCPU, SystemDisk, SystemMemory, SystemNetwork, SystemOS, Event, EventLevel, EventType, SystemType, Site, SiteType, Provider
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
                self.handle_message(msg, ws)
        except websockets.ConnectionClosedOK:
            pass
        except Exception as exc:
            print(f"‽ handler error from {peer}: {exc}")
            traceback.print_exc()
        finally:
            self.clients.discard(ws)
            print(f"✗ {peer} disconnected (now {len(self.clients)} clients)")

    def handle_message(self, msg: str, ws: websockets.WebSocketServerProtocol) -> None:
        print(f"Received message from {ws.remote_address}: {len(msg)}")
        json_data = json.loads(msg)

        system_id = json_data.get("system_id")
        timestamp = json_data.get("timestamp")
        type = json_data.get("type")

        # hardware:
        # 	network
        # 		hostname
        # 		fqdn
        # 		public_ip
        # 		interfaces
        # 			{}
        # 				interface name: interface ip
        # 	os
        # 		system
        # 		release
        # 		version
        # 		machine
        # 		processor
        # 	cpu
        # 		physical_cores
        # 		logical_cores
        # 		max_frequency_mhz
        # 	mem_total_gib
        # 	disks
        # 		[]
        # 			device
        # 			mountpoint
        # 			fstype
        # 			total_gib

        # usage:
        # 	cpu_pct
        # 	mem_used_gib
        # 	disks
        # 		[]
        # 			device
        # 			used_gib
        # 	network
        # 		hostname
        # 		fqdn
        # 		public_ip
        # 		interfaces
        # 			{}
        # 				interface name: interface ip

        system = self.db.get_system(system_id)
        if system is None:
            raise ValueError(f"Unknown system ID: {system_id}")

        if type == "hardware_info":
            data = json_data["hardware"]
            
            network = SystemNetwork(
                hostname=data["network"]["hostname"],
                fqdn=data["network"]["fqdn"],
                public_ip=data["network"]["public_ip"],
                interfaces=data["network"]["interfaces"],
            )
            os_info = SystemOS(
                system=data["os"]["system"],
                release=data["os"]["release"],
                version=data["os"]["version"],
                machine=data["os"]["machine"],
                processor=data["os"]["processor"],
            )
            cpu = SystemCPU(
                physical_cores=data["cpu"]["physical_cores"],
                logical_cores=data["cpu"]["logical_cores"],
                max_frequency_mhz=data["cpu"]["max_frequency_mhz"],
            )
            memory = SystemMemory(
                total_gib=data["mem_total_gib"],
            )
            disks = [
                SystemDisk(
                    device=disk["device"],
                    mountpoint=disk["mountpoint"],
                    fstype=disk["fstype"],
                    total_gib=disk["total_gib"],
                )
                for disk in data["disks"]
            ]

            self.db.update_system(
                system_id,
                network=network,
                os=os_info,
                cpu=cpu,
                memory=memory,
                disks=disks
            )

        elif type == "usage_info":
            data = json_data["usage"]

            cpu_pct = data["cpu_pct"]
            mem_used_gib = data["mem_used_gib"]
            for disk in data["disks"]:
                device = disk["device"]
                used_gib = disk["used_gib"]
                # Update the disk usage in the system
                for sys_disk in system.disks:
                    if sys_disk.device == device:
                        sys_disk.used_gib = used_gib
                        break
                    
            network = SystemNetwork(
                hostname=data["network"]["hostname"],
                fqdn=data["network"]["fqdn"],
                public_ip=data["network"]["public_ip"],
                interfaces=data["network"]["interfaces"],
            )

            system.cpu.usage_pct = cpu_pct
            system.memory.used_gib = mem_used_gib
            system.network = network

        system.last_seen = int(time.time())

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
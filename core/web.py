import dataclasses
import datetime
import json
import time
import uuid
from datetime import timedelta
from collections import defaultdict

from quart import Quart, websocket, session, render_template, request, redirect, url_for, abort, jsonify, flash

import redis

from models import Event, EventLevel, EventType, Provider, Site, System, SystemCPU, SystemDisk, SystemMemory, SystemNetwork, SystemOS, SystemService
from db import SystemDB
from util import Config


class Dashboard:
    def __init__(self, config: Config):
        self.config = config
        self.db = SystemDB()
        self.clients = set()
        self.client_map = {}
        self.msg_count = defaultdict(int)

        self.USERNAME = config.dashboard_username
        self.PASSWORD = config.dashboard_password

        self.app = Quart("SysMon", template_folder='core/templates', static_folder='core/static')
        self.app.secret_key = uuid.uuid4().hex
        self.app.config.update(
            APPLICATION_ROOT=config.dashboard_application_root,
            PERMANENT_SESSION_LIFETIME=timedelta(minutes=30)
        )

        self.redis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

        self._setup_routes()

    def get_limiter_login_fail_key(self):
        return f"login_fail:{request.remote_addr}"

    def _setup_routes(self):
        app = self.app

        @app.errorhandler(404)
        @app.errorhandler(405)
        async def standard_error(error):
            return await render_template("status_code.jinja", status_code=error.code), error.code

        @app.template_filter("datetimeformat")
        def datetimeformat(value):
            return datetime.datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')


        @app.route('/')
        async def index():
            if not session.get('logged_in'):
                return redirect(url_for('login'))
            return await render_template("index.jinja", providers=self.db.providers, application_root=app.config['APPLICATION_ROOT'])

        @app.route('/login', methods=['GET', 'POST'])
        async def login():

            # key = self.get_limiter_login_fail_key()
            # fails = int(self.redis.get(key) or 0)
            # if fails > 5:
            #     return "Too many attempts. Try again later.", 429

            # # On failure:
            # self.redis.incr(key)
            # self.redis.expire(key, 900)


            if session.get('logged_in'):
                return redirect(url_for('index'))

            if request.method == 'POST':
                form = await request.form
                username = form.get('username')
                password = form.get('password')
                if username == self.USERNAME and password == self.PASSWORD:
                    session.clear()
                    session.permanent = True
                    session['logged_in'] = True
                    return redirect(url_for('index'))
                else:
                    flash("Invalid username or password", 'error')

            return await render_template("login.jinja")

        @app.route('/logout')
        async def logout():
            session.pop('logged_in', None)
            flash("Logged out", 'success')
            return redirect(url_for('login'))

        @app.route('/providers.json')
        async def providers_json():
            if not session.get('logged_in'):
                abort(401)
            return jsonify([dataclasses.asdict(p) for p in self.db.providers])

        @app.route('/system')
        async def system_view():
            if not session.get('logged_in'):
                return redirect(url_for('login'))
            
            system_id = request.args.get('id')
            if not system_id:
                return redirect(url_for('index'))

            system = self._find_system_by_id(system_id)
            if not system:
                abort(404)
            return await render_template("system.jinja", system=system)

        @app.route('/system/json')
        async def system_json():
            if not session.get('logged_in'):
                abort(401)
            system_id = request.args.get('id')
            if not system_id:
                abort(400, "Missing system ID")
                
            system = self._find_system_by_id(system_id)
            if not system:
                abort(404)
            # return jsonify({
            #     "id": system.id,
            #     "name": system.name,
            #     "cpu": dataclasses.asdict(system.cpu),
            #     "memory": dataclasses.asdict(system.memory),
            #     "last_seen": system.last_seen,
            # })
            return jsonify(dataclasses.asdict(system))
        
        @app.route('/event/clear', methods=['POST'])
        async def clear_event():
            if not session.get('logged_in'):
                abort(401)

            data: dict = await request.get_json()
            if not data:
                abort(400, "Invalid JSON data")
            system_id = data.get('system_id')
            event_id = data.get('id')

            if not system_id or not event_id:
                abort(400, "Missing parameters")

            self.db.clear_event(system_id, event_id)

            return jsonify({"status": "success", "message": "Event cleared"})

        @app.route('/admin', methods=['GET', 'POST'])
        async def admin():
            if not session.get('logged_in'):
                return redirect(url_for('login'))

            if request.method == 'POST':
                form = await request.form
                action = form.get("action")
                try:
                    if action == "add_provider":
                        self.db.add_provider(Provider(name=form["name"], sites=[], url=form.get("url", "")))

                    elif action == "edit_provider":
                        self.db.edit_provider(form["name"], name=form["new_name"], url=form.get("url", ""))

                    elif action == "remove_provider":
                        self.db.remove_provider(form["name"])

                    elif action == "add_site":
                        self.db.add_site(
                            form["provider_name"],
                            Site(name=form["site_name"], type=form["type"], geoname=form.get("geoname", ""), systems=[])
                        )

                    elif action == "edit_site":
                        self.db.edit_site(
                            form["provider_name"],
                            form["site_name"],
                            name=form.get("new_name", form["site_name"]),
                            type=form.get("type"),
                            geoname=form.get("geoname", "")
                        )

                    elif action == "remove_site":
                        self.db.remove_site(form["provider_name"], form["site_name"])

                    elif action == "add_system":
                        self.db.add_system(
                            form["site_name"],
                            System(
                                id=form["id"],
                                name=form["name"],
                                type=form["type"],
                                auth_key=uuid.uuid4().hex,
                                group=form.get("group", ""),
                                connected=False,
                                warning=False,
                                critical=False,
                            )
                        )

                    elif action == "edit_system":
                        self.db.edit_system(
                            form["system_id"],
                            name=form.get("name"),
                            type=form.get("type"),
                            group=form.get("group", ""),
                            services=form.get("services", "").splitlines() if form.get("services") else [],
                            connected="connected" in form,
                            warning="warning" in form,
                            critical="critical" in form,
                        )

                        system_ws = next((ws for ws in self.clients if self.client_map[ws] == form["system_id"]), None)
                        if system_ws:
                            system_ws.send(json.dumps({
                                "type": "set_watch_services",
                                "services": [service.name for service in self.db.get_system(form["system_id"]).services]
                            }))

                    elif action == "edit_system_id":
                        self.db.edit_system_id(
                            form["system_id"],
                            new_id=form["new_id"]
                        )

                        old_ws = next((ws for ws in self.clients if self.client_map[ws] == form["system_id"]), None)
                        if old_ws:
                            self.client_map[old_ws] = form["new_id"]
                            print(f"Updated WebSocket mapping: {form['system_id']} -> {form['new_id']}")

                    elif action == "remove_system":
                        self.db.remove_system(form["system_id"])

                except Exception as e:
                    print(f"Error processing action {action}: {e}")

                return redirect(url_for("admin"))

            return await render_template("admin.jinja", providers=self.db.providers)

        @app.websocket('/ws')
        async def ws():
            ws = websocket._get_current_object()
            self.clients.add(ws)
            self.client_map[ws] = None
            print(f"✓ WebSocket connected (clients={len(self.clients)})")
            try:
                while True:
                    msg = await websocket.receive()
                    self.msg_count[ws] += 1
                    await self._handle_ws_message(msg, ws)
            except Exception as e:
                print(f"WebSocket error: {e}")
            finally:
                self.clients.discard(ws)
                sid = self.client_map.pop(ws, None)
                if sid:
                    self.db.update_system(sid, connected=False)
                print(f"✗ WebSocket disconnected (clients={len(self.clients)})")

    def _find_system_by_id(self, system_id):
        for prov in self.db.providers:
            for site in prov.sites:
                for sys in site.systems:
                    if sys.id == system_id:
                        return sys
        return None

    async def _handle_ws_message(self, msg, ws):
        print(f"Received message from {ws.remote_addr}: {len(msg)}")
        json_data = json.loads(msg)

        system_id = json_data.get("system_id")
        timestamp = json_data.get("timestamp")
        type = json_data.get("type")

        system = self.db.get_system(system_id)
        if not system:
            raise ValueError(f"Unknown system ID: {system_id}")

        self.client_map[ws] = system_id
        self.db.update_system(system_id, connected=True)

        system.last_seen = int(time.time())

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

            disks.sort(key=lambda d: d.total_gib, reverse=True)

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

            if cpu_pct > 90:
                self.db.add_event(system.id, Event.create_event(
                    level=EventLevel.CRITICAL,
                    type=EventType.CPU,
                    timestamp=timestamp,
                    clearable=True,
                    description=f"CPU usage is at {cpu_pct}%."
                ))
            elif cpu_pct > 75:
                self.db.add_event(system.id, Event.create_event(
                    level=EventLevel.WARNING,
                    type=EventType.CPU,
                    timestamp=timestamp,
                    clearable=True,
                    description=f"CPU usage is at {cpu_pct}%."
                ))

            if mem_used_gib > 0.9 * system.memory.total_gib:
                self.db.add_event(system.id, Event.create_event(
                    level=EventLevel.CRITICAL,
                    type=EventType.MEMORY,
                    timestamp=timestamp,
                    clearable=True,
                    description=f"Memory usage is at {mem_used_gib} GiB."
                ))
            elif mem_used_gib > 0.75 * system.memory.total_gib:
                self.db.add_event(system.id, Event.create_event(
                    level=EventLevel.WARNING,
                    type=EventType.MEMORY,
                    timestamp=timestamp,
                    clearable=True,
                    description=f"Memory usage is at {mem_used_gib} GiB."
                ))

            for disk in data["disks"]:
                device = disk["device"]
                used_gib = disk["used_gib"]
                
                for sys_disk in system.disks:
                    if sys_disk.device == device:
                        sys_disk.used_gib = used_gib
                        break

            system.disks.sort(key=lambda d: d.total_gib, reverse=True)

            network = SystemNetwork(
                hostname=data["network"]["hostname"],
                fqdn=data["network"]["fqdn"],
                public_ip=data["network"]["public_ip"],
                interfaces=data["network"]["interfaces"],
            )

            services = [
                SystemService(
                    name=service["name"],
                    running=service.get("running", False),
                    status=service.get("status", ""),
                )
                for service in json_data["watched_services"]
            ]

            if any(not service.running for service in services):
                self.db.add_event(system.id, Event.create_event(
                    level=EventLevel.WARNING,
                    type=EventType.SERVICE,
                    timestamp=timestamp,
                    clearable=True,
                    description="One or more services are not running."
                ))

            system.cpu.usage_pct = cpu_pct
            system.memory.used_gib = mem_used_gib
            system.network = network
            system.services = services

        elif type == "get_watch_services":
            services = [service.name for service in system.services]
            await ws.send(json.dumps({"type": "set_watch_services", "services": services}))

    def run(self):
        print(f"Starting on {self.config.dashboard_host}:{self.config.dashboard_port}")
        self.app.run(host=self.config.dashboard_host, port=self.config.dashboard_port)
[![License: NCPUL](https://img.shields.io/badge/license-NCPUL-blue.svg)](./LICENSE.md)

# sysmon‑server

A lightweight **dashboard server** that visualizes real-time system metrics from multiple machines running the [sysmon-agent](https://github.com/yniverz/sysmon-agent).  
The frontend uses a modern, responsive Vue-based UI for navigating providers, sites, and system groups, while the backend receives data via WebSocket and serves a live dashboard.

---

## Features

* 📡 **WebSocket receiver** for hardware and usage telemetry from agents
* 🖥️ **Dashboard** with per-provider, per-site, and per-group views
* 💾 **Persistence** of system state to JSON with automatic structure validation
* 🔐 **Login support** with rate-limiting and backoff (via Redis)
* 🧠 **ASGI-based Quart server** with native WebSocket and HTTP support
* 🌐 **Custom icon rendering** with stackable, status-aware system images

---

## Requirements

* Python 3.10+
* Redis (for login throttling)
* A modern web browser with WebGL support
* Recommended: `hypercorn` for production deployment

---

## Installation

```bash
git clone https://github.com/yourname/sysmon-server.git
cd sysmon-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Configuration

Create a `config.toml` file in the root directory:

```toml
[dashboard]
host = "0.0.0.0"
port = 5000
username = "admin"
password = "admin"
```

---

## Usage

### Development (with automatic reload):

```bash
python core
```

This will start a **Quart dashboard and WebSocket server** on `localhost:5000` for visualizing data and receiving agent telemetry


## Data Structure

* `structure.template.json`: Defines the provider/site/system hierarchy
* `data.json`: Stores live system data
* `template_hash.txt`: Ensures schema matches between template and stored data

The system will automatically rebuild the data on start if the template changes.

---

## Deployment Tips

* 🧪 Run `redis-server` locally or via Docker for login throttling
* 🛡️ Place behind `nginx` or `Caddy` with HTTPS termination (optional but recommended)

---

## Related Projects

* **[sysmon-agent](https://github.com/yniverz/sysmon-agent):** Lightweight client daemon that streams system data to this server.



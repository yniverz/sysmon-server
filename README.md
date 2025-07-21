Here’s a concise and clear `README.md` for your **SysMon Dashboard server** repo, designed to complement the agent's README:

---

[![License: NCPUL](https://img.shields.io/badge/license-NCPUL-blue.svg)](./LICENSE.md)

# sysmon‑server

A lightweight **dashboard server** that visualizes real-time system metrics from multiple machines running the [sysmon-agent](https://github.com/yniverz/sysmon-agent).
The frontend uses a modern, responsive Vue-based UI for navigating providers, sites, and system groups, while the backend receives data via WebSocket and persists it for live status tracking.

---

## Features

* 📡 **WebSocket receiver** for hardware and usage telemetry from agents
* 🖥️ **Dashboard** with per-provider, per-site, and per-group views
* 📁 **Persistence** of system state to JSON with automatic structure validation
* 🔐 **Login support** with rate-limiting and backoff (via Redis)
* 🌐 **Custom icon rendering** with stackable, status-aware system images

---

## Requirements

* Python 3.10+
* Redis (for login throttling)
* Web browser with WebGL for dashboard
* Optional: systemd + `waitress` for deployment

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

## Usage

```bash
python core
```

This starts:

* A **WebSocket server** (default: `0.0.0.0:8765`) that receives data from `sysmon-agent`
* A **Flask web server** (default: `localhost:5000`) for the live dashboard

> You can customize ports and credentials via `config.toml`.

---

## Configuration

Create a `config.toml` file in the root directory:

```toml
[dashboard]
host = "0.0.0.0"
port = 5000
username = "admin"
password = "admin"

[websocket]
host = "0.0.0.0"
port = 8765
```

---

## Data Structure

* `structure.template.json`: Defines the provider/site/system hierarchy
* `data.json`: Stores live data updates
* `template_hash.txt`: Ensures schema sync between template and data

If the template changes, the server will auto-rebuild the data structure.

---

## Related Projects

* **[sysmon-agent](https://github.com/yniverz/sysmon-agent):** Lightweight client daemon that streams system data to this server.

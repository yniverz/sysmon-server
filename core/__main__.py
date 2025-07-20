
import server
import web
import toml
from util import Config

# load config.toml to get host and port
def load_config():
    cfg = Config()
    try:
        with open('config.toml', 'r') as f:
            config_data = toml.load(f)
            cfg.dashboard_host = config_data.get('dashboard', {}).get('host', cfg.dashboard_host)
            cfg.dashboard_port = config_data.get('dashboard', {}).get('port', cfg.dashboard_port)
            cfg.websocket_host = config_data.get('websocket', {}).get('host', cfg.websocket_host)
            cfg.websocket_port = config_data.get('websocket', {}).get('port', cfg.websocket_port)
            return cfg

    except FileNotFoundError:
        print("config.toml not found, using default values.")
        
    return cfg


if __name__ == "__main__":
    cfg = load_config()

    monitor = server.SystemReceiver(cfg.websocket_host, cfg.websocket_port)
    monitor.start()

    web_server = web.Dashboard(cfg, local_debug=True)
    web_server.run()
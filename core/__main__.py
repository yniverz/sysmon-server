
import server
import web
import toml
from util import Config
import models

# load config.toml to get host and port
def load_config():
    cfg = Config()
    try:
        with open('config.toml', 'r') as f:
            config_data = toml.load(f)
            cfg.dashboard_host = config_data.get('dashboard', {}).get('host', cfg.dashboard_host)
            cfg.dashboard_port = config_data.get('dashboard', {}).get('port', cfg.dashboard_port)
            cfg.dashboard_username = config_data.get('dashboard', {}).get('username', cfg.dashboard_username)
            cfg.dashboard_password = config_data.get('dashboard', {}).get('password', cfg.dashboard_password)
            cfg.dashboard_application_root = config_data.get('dashboard', {}).get('application_root', cfg.dashboard_application_root)
            # websocket config
            cfg.websocket_host = config_data.get('websocket', {}).get('host', cfg.websocket_host)
            cfg.websocket_port = config_data.get('websocket', {}).get('port', cfg.websocket_port)
            return cfg

    except FileNotFoundError:
        print("config.toml not found, using default values.")
        
    return cfg


if __name__ == "__main__":
    cfg = load_config()

    receiver = server.SystemReceiver(cfg.websocket_host, cfg.websocket_port)
    receiver.start()

    web_server = web.Dashboard(cfg, receiver, local_debug=True)
    web_server.run()
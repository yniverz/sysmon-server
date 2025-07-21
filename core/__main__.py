
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

    # receiver.db.add_provider(models.Provider(name="Default Provider", sites=[]))
    # receiver.db.add_site("Default Provider", models.Site(
    #     name="Default Site",
    #     type="datacenter",
    #     geoname="Default Location",
    #     systems=[]
    # ))
    # receiver.db.add_system("Default Site", models.System(
    #     id="default_system",
    #     name="Default System",
    #     type="laptop"
    # ))
    # receiver.db.add_system("Default Site", models.System(
    #     id="2",
    #     name="System2",
    #     type="server"
    # ))
    # receiver.db.add_system("Default Site", models.System(
    #     id="3",
    #     name="System3",
    #     type="desktop"
    # ))

    web_server = web.Dashboard(cfg, receiver, local_debug=True)
    web_server.run()

import asyncio
import web
from util import Config

from hypercorn.asyncio import serve
from hypercorn.config import Config as HyperConfig


async def main():
    cfg = Config.from_toml()

    # Start dashboard (which sets up the Quart app)
    dashboard = web.Dashboard(cfg)

    # Run Quart using Hypercorn (production-ready)
    hyper_cfg = HyperConfig()
    hyper_cfg.bind = [f"{cfg.dashboard_host}:{cfg.dashboard_port}"]
    hyper_cfg.workers = 1  # Set >1 if using multiprocessing

    await serve(dashboard.app, hyper_cfg)

if __name__ == "__main__":
    asyncio.run(main())

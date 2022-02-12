#!.venv/bin/python
import argparse
import asyncio

from hypercorn.asyncio import serve
from hypercorn.config import Config

parser = argparse.ArgumentParser(
    prog="PiCamera Manager", description="Client application for PiCamera Manager"
)
parser.add_argument(
    "-p",
    "--production",
    action="store_true",
    help="Specify the whether the client is being run in the production environment",
)
args: argparse.Namespace = parser.parse_args()

if __name__ == "__main__":
    is_dev: bool = not args.production

    # import app here as it is necessary to set up the environment variables above, first
    from src.api import app  # noqa: E402

    ADDR: str = "0.0.0.0"
    PORT: int = 9000
    WORKERS: int = 1

    # set up the hypercorn server
    config: Config = Config()
    config.bind = f"{ADDR}:{PORT}"
    config.use_reloader = is_dev
    config.workers = WORKERS

    # run the app
    asyncio.run(serve(app, config))

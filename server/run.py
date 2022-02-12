#!.venv/bin/python
import argparse
import os

parser = argparse.ArgumentParser(
    prog="PiCamera Manager", description="Server application for PiCamera Manager"
)
parser.add_argument(
    "-e",
    "--environment",
    choices=["PRODUCTION", "DEVELOPMENT"],
    required=True,
    help="Specify the environment you wish to run the server in (e.g. development or production)",
)
args = parser.parse_args()

if __name__ == "__main__":
    env = args.environment
    is_dev = env == "DEVELOPMENT"
    os.environ["ENV"] = env

    # import app here as it is necessary to set up the environment variables above, first
    from src.dashboard import app  # noqa: E402

    # app.run_server(host="0.0.0.0", port=8001, debug=True, dev_tools_hot_reload=True)

    # # set up the dev environment
    # if is_dev:
    #     app.enable_dev_tools()
    #     subprocess.run("fuser -k -n tcp 8001".split())

    # ADDR = "0.0.0.0"
    # PORT = app.server.config["PORT"]
    # WORKERS = 1

    # # set up the hypercorn server
    # config = Config()
    # config.bind = f"{ADDR}:{PORT}"
    # config.use_reloader = is_dev
    # config.workers = WORKERS
    # app.logger.info(app.layout)

    # # run the app
    # asyncio.run(serve(app.server, config))

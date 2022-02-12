import logging
import os

import dash
import dash_bootstrap_components as dbc
from dash_extensions.enrich import DashProxy, MultiplexerTransform, NoOutputTransform, TriggerTransform
from flask import Flask, request
from flask_sock import Sock
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

from ..settings import load_settings
from ..utils import sql
from .utils import TimelapseEncoder, YouTubeMonitor

# first create and configure the Flask server
server = Flask(__name__)
server_config = load_settings()
server.config.from_object(server_config)


# there must be a better way to find out the IP address that the Flask server is listening on.
# Either way, we need to know it so that we can connect the Javascript MSE video client to the
# picamera server when streaming the video feed down the websocket
@server.before_first_request
def store_server_ip():
    try:
        server.config["SERVER_IP_ADDRESS"] = request.host_url.split(":")[1]
    except:  # noqa
        server.config["SERVER_IP_ADDRESS"] = "192.168.1.10"


# set up the global database object
db = SQLAlchemy(server, model_class=sql.Model, query_class=sql.Query)

# enable websockets
sock = Sock(server)


# ensure foreign key support is enabled
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# TODO: bootstrap 5 now includes its own SVG icons. Can we use those instead?
# create the actual Dash app
app = DashProxy(
    __name__,
    server=server,
    suppress_callback_exceptions=True,
    prevent_initial_callbacks=True,
    title="RPi Camera Manager",
    update_title=None,
    transforms=[MultiplexerTransform(), NoOutputTransform(), TriggerTransform()],
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        dbc.icons.BOOTSTRAP,
        # "https://fonts.googleapis.com/icon?family=Material+Icons",
    ],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ],
    # external_scripts=[
    #     {"src": "https://kit.fontawesome.com/0671cf27a1.js", "crossorigin": "anonymous"}
    # ],
)
app.enable_dev_tools(debug=True)

# set up logging; default handler is to stdout
app.logger.setLevel(logging.INFO)
app.logger.handlers[0].setFormatter(
    logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] %(message)s",
        "%Y-%m-%d %H:%M:%S %z",
    )
)

# create a single application-level encoder class for creating timelapses
TimelapseEncoder = TimelapseEncoder()

# create a single application-level YouTube monitor class for managing YouTube streams
# YouTubeMonitor = YouTubeMonitor()


# register the routes by running the code during import
from . import routes  # noqa: E402 F401

app.logger.info("App initialised in %s mode", os.environ["ENV"])

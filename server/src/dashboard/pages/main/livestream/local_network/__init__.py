import time

import dash_bootstrap_components as dbc
from dash import html

from .....app import app
from .....enums import Element as El
from . import callbacks  # noqa: F401


def make_network_output_content(cam):
    print("making network output content")
    return make_video_component(cam)


def make_video_component(cam):
    camera_config = cam.get_config()
    # width, height = camera_config["viewport_size"].split("x")
    width, height = "1024x768".split("x")
    return html.Div(
        [
            html.Video(
                id=f"network-stream-player-{cam.camera_id}",
                autoPlay=True,
                muted=True,
                controls=True,
                width=width,
                height=height,
            ),
            # setting the value to something dynamic ensures that the JavaScript gets run
            # each time the Video element above is loaded
            dbc.Input(id=El.INIT_MSE_CLIENT, type="hidden", value=time.time()),
            dbc.Input(
                id=El.SERVER_IP_ADDRESS, type="hidden", value=app.server.config["SERVER_IP_ADDRESS"]
            ),
            dbc.Input(id=El.SERVER_PORT, type="hidden", value=app.server.config["PORT"]),
        ],
        style={"textAlign": "center"},
    )

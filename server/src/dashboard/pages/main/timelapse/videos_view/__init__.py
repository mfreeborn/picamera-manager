import dash_bootstrap_components as dbc
from dash import dcc
from dash import html

from . import callbacks  # noqa
from . import modals


def make_timelapse_video_output_content():
    """Return the top-level component for the 'Video' tab for the 'Timelapse' output."""
    print("making timelapse videos view content")
    return dbc.Row(
        [
            dcc.Interval(id="timelapse-encoding-progress-interval", interval=500, disabled=True),
            dbc.Input(id="selected-timelapse-video-id", type="hidden"),
            # the left-hand column
            dbc.Col(
                [
                    html.Div(
                        dbc.Button(
                            "Create Timelapse Video",
                            id="create-timelapse-button",
                            style={"width": 256, "height": "3rem", "fontSize": "larger"},
                        ),
                        style={"paddingLeft": 25, "paddingBottom": 15},
                    ),
                    html.Div(
                        id="timelapse-videos-thumbnails-div",
                        style={
                            "gap": 25,
                            "display": "flex",
                            "flexWrap": "wrap",
                            "overflowY": "auto",
                            "paddingTop": 5,
                            "paddingLeft": 25,
                            "paddingBottom": 5,
                            "maxHeight": "100%",
                        },
                    ),
                ],
                width=2,
                style={"height": "100%"},
            ),
            dbc.Col(
                html.Div(id="view-timelapse-video-div", style={"height": "100%"}),
                width=10,
                style={"height": "100%"},
            ),
            modals.make_create_timelapse_modal(),
            modals.make_delete_timelapse_modal(),
            dbc.Toast(
                id="delete-timelapse-video-toast",
                header="Success!",
                icon="success",
                is_open=False,
                dismissable=True,
                duration=4000,  # display for 4 seconds
                style={
                    "position": "fixed",
                    "top": 66,
                    "right": 10,
                    "width": 350,
                    "backgroundColor": "white",
                    "color": "black",
                },
            ),
            dbc.Input(value=0, id="refresh-timelapse-video-thumbnails", type="hidden"),
        ],
        style={"height": 1000},
        id="timelapse-video-output-content-container",
    )

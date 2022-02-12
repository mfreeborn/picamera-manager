import dash_bootstrap_components as dbc
from dash import html

from . import components
from ....models import RegisteredCamera
from ...enums import Element as El


def MAIN_LAYOUT(camera_id):
    # camera_id == -1 when there are no cameras at all
    if camera_id < 0:
        return dbc.Row(
            dbc.Col(
                [
                    html.H3(
                        'Click "Add Camera +" above to get started!',
                        style={"paddingBottom": "5rem"},
                    ),
                    html.I(
                        className="bi-camera",
                        style={"color": "#6c757d", "fontSize": "600px"},
                    ),
                ],
            ),
            style={"textAlign": "-webkit-center", "paddingTop": "5rem"},
        )

    cam = RegisteredCamera.query.get(camera_id)

    return [
        dbc.Row(
            [
                dbc.Col(
                    # components.make_sidebar(cam), style={"maxWidth": "17%", "maxHeight": "100%"}
                    html.Div("Side bar"),
                    style={"maxWidth": "17%", "maxHeight": "100%"},
                ),
                dbc.Col(
                    [
                        html.Div(id=El.OUTPUT_CONTENT_DIV),
                        # this represents which output is current being viewed
                        dbc.Input(type="hidden", id=El.ACTIVE_OUTPUT),
                        dbc.Input(type="hidden", value=False, id=El.RELOAD_OUTPUT_CONTENT_FLAG),
                    ],
                    style={"paddingTop": "2rem"},
                ),
            ],
            style={"height": "100%", "maxHeight": "100%"},
        ),
        html.Div(id="out"),
        html.Div(id="out2"),
    ]

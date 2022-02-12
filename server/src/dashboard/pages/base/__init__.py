import dash_bootstrap_components as dbc
from dash import dcc
from dash import html

from ...enums import Element as El
from . import components, modals


def BASE_LAYOUT():
    return dbc.Container(
        [
            components.make_header_bar(),
            # note that the header bar height is 56px (40px + (8px x 2 margin))
            html.Div(id=El.PAGE_CONTENT, style={"height": "calc(100vh - 56px)"}),
            html.Div(modals.make_add_camera_modal(), id="CAM_MODAL_DIV"),
            modals.make_delete_camera_modal(),
            # we use this Timer to track any current timelapse encodings to then be able
            # to display a top-level Toast telling the user when the encoding is done
            dcc.Interval(id="timelapse-encoding-global-interval", interval=500, disabled=True),
            dbc.Toast(
                "Timelapse video succesfully created",
                id="timelapse-encoding-complete",
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
            dbc.Toast(
                "Camera successfully added",
                id="add-camera-toast",
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
            dbc.Toast(
                "Camera successfully deleted",
                id="delete-camera-toast",
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
        ],
        id=El.BASE_DIV,
        fluid=True,
        style={},
    )

import dash_bootstrap_components as dbc
from dash import dcc
from dash import html

from ....models import RegisteredCamera
from ...enums import Element as El


def make_header_bar():
    navbar = dbc.Navbar(
        dbc.Container(
            [
                # Use row and col to control vertical alignment of logo / brand
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.NavbarBrand("Raspberry Pi Camera Manager"),
                            class_name="ms-2",
                            width="auto",
                        ),
                        dbc.Col(_make_camera_select(), class_name="ms-2"),
                        dbc.Col(_make_add_camera_button(), class_name="ms-4", width="auto"),
                        dbc.Col(
                            _make_delete_camera_button(),
                            class_name="ms-4",
                            width="auto",
                        ),
                    ],
                    align="center",
                ),
            ],
            fluid=True,
        ),
        color="dark",
        dark=True,
        style={"marginLeft": -12, "marginRight": -12},
    )
    return navbar


def _make_camera_select():
    cams = RegisteredCamera.query.order_by(RegisteredCamera.name.asc())
    options = [{"label": cam.name, "value": cam.camera_id} for cam in cams]
    options = options or [{"label": "No cameras found!", "value": -1, "disabled": True}]

    return dcc.Dropdown(
        id=El.CAMERA_SELECT,
        options=options,
        value=options[0]["value"],
        searchable=False,
        clearable=False,
        style={"color": "black", "minWidth": "11rem"},
        persistence=True,
    )


def _make_delete_camera_button():
    return dbc.Button(
        [
            html.Span("Delete Camera"),
            html.I(className="far fa-trash-alt ms-2"),
        ],
        id=El.DELETE_CAMERA_MODAL_BUTTON_OPEN,
        color="danger",
        style={"display": "none" if not RegisteredCamera.query.first() else "block"},
    )


def _make_add_camera_button():
    return dbc.Button(
        [
            html.Span("Add Camera"),
            html.I(className="bi-plus-circle", style={"paddingLeft": "0.5rem"}),
        ],
        id=El.ADD_CAMERA_MODAL_BUTTON_OPEN,
        color="secondary",
    )

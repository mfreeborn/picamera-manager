import dash_bootstrap_components as dbc
from dash import html, dcc

from ...enums import Element as El


def FormFeedackError(component_id, text_id):
    """Return an error component to be displayed against the form as a whole."""
    return dbc.Row(
        [
            dbc.Col(
                html.I(
                    className="bi-exclamation-circle me-3",
                    style={"fontSize": "1.3rem"},
                ),
                width="auto",
            ),
            dbc.Col(
                html.Span("", id=text_id, style={"lineHeight": "normal"}),
            ),
        ],
        id=component_id,
        align="center",
        className="g-0 px-2 py-1",
        style={
            "backgroundColor": "#f44336",
            "borderColor": "red",
            "borderRadius": "4px",
            "borderStyle": "solid",
            "borderWidth": "2px",
            "display": "none",
            "fontSize": "0.9rem",
        },
    )


def make_save_camera_button(disabled=True):
    return dbc.Button(
        "Save Camera",
        id=El.ADD_CAMERA_MODAL_BUTTON_SAVE,
        disabled=disabled,
    )


def make_add_camera_modal():
    ip_address = html.Div(
        [
            dbc.Label("IP Address", html_for=El.ADD_CAMERA_IP_ADDRESS_INPUT),
            dbc.Input(
                type="text",
                id=El.ADD_CAMERA_IP_ADDRESS_INPUT,
                placeholder="e.g. 192.168.1.250",
            ),
            dbc.Input(id=El.ADD_CAMERA_IP_ADDRESS_INPUT_FULLY_VALID, type="hidden", value=False),
            dbc.FormFeedback(
                id=El.ADD_CAMERA_IP_ADDRESS_FORM_FEEDBACK,
                type="invalid",
            ),
        ],
        className="mb-3",
    )

    port = html.Div(
        [
            dbc.Label("Port", html_for=El.ADD_CAMERA_PORT_INPUT),
            dbc.Input(type="text", id=El.ADD_CAMERA_PORT_INPUT, placeholder="e.g. 8000"),
            dbc.Input(id=El.ADD_CAMERA_PORT_INPUT_FULLY_VALID, type="hidden", value=False),
            dbc.FormFeedback(
                id=El.ADD_CAMERA_PORT_FORM_FEEDBACK,
                type="invalid",
            ),
        ],
        className="mb-3",
    )

    camera_name = html.Div(
        [
            dbc.Label("Name", html_for=El.ADD_CAMERA_NAME_INPUT),
            dbc.Input(
                type="text",
                id=El.ADD_CAMERA_NAME_INPUT,
                placeholder="e.g. Charlotte",
            ),
            dbc.Input(id=El.ADD_CAMERA_NAME_INPUT_FULLY_VALID, type="hidden", value=False),
            dbc.FormFeedback(
                id=El.ADD_CAMERA_NAME_FORM_FEEDBACK,
                type="invalid",
            ),
        ],
        className="mb-2",
    )

    is_submitting = dbc.Input(id="ADD_CAMERA_FORM_IS_SUBMITTING", type="hidden", value=False)
    form_fully_valid = dbc.Input(id="FORM_FULLY_VALID", type="hidden", value=False)

    form = dbc.Form([ip_address, port, camera_name, is_submitting, form_fully_valid])

    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Add Camera"), close_button=False),
            dbc.ModalBody(form),
            dbc.ModalFooter(
                dbc.Row(
                    [
                        dbc.Col(
                            FormFeedackError(
                                component_id=El.ADD_CAMERA_FORM_SUBMISSION_ERROR,
                                text_id=El.ADD_CAMERA_FORM_SUBMISSION_ERROR_TEXT,
                            ),
                        ),
                        dbc.Col(
                            [
                                html.Div(
                                    make_save_camera_button(),
                                    id="SAVE_CAM_BUTTON_DIV",
                                    style={"display": "contents"},
                                ),
                                dbc.Button(
                                    "Close", id=El.ADD_CAMERA_MODAL_BUTTON_CLOSE, class_name="ms-2"
                                ),
                            ],
                            class_name="ms-3",
                            style={
                                "textAlign": "right",
                            },
                            width="auto",
                        ),
                    ],
                    align="center",
                    class_name="g-0",
                ),
                style={"display": "block"},
            ),
            html.Div(id="form-focus-hidden-div", className="hidden"),
        ],
        id=El.ADD_CAMERA_MODAL,
        is_open=False,
    )


def make_delete_camera_modal():
    body_content = html.Div(
        [
            html.P(
                "Are you sure you want to delete the following camera? "
                "All images, videos and configuration settings will be lost irretrievably."
            ),
            html.Ul(html.Li(id=El.DELETE_CAMERA_NAME)),
        ]
    )

    footer_content = dbc.Row(
        dbc.Col(
            [
                dbc.Button("Confirm", id=El.DELETE_CAMERA_MODAL_BUTTON_CONFIRM, color="danger"),
                dbc.Button(
                    "Close",
                    id=El.DELETE_CAMERA_MODAL_BUTTON_CLOSE,
                    style={"marginLeft": "0.5rem"},
                ),
            ],
            style={
                "padding": 0,
                "textAlign": "right",
            },
        )
    )

    return dbc.Modal(
        [
            dbc.ModalHeader("Delete Camera"),
            dbc.ModalBody(body_content),
            dbc.ModalFooter(footer_content),
        ],
        id=El.DELETE_CAMERA_MODAL,
        is_open=False,
    )

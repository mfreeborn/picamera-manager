from ipaddress import IPv4Address, AddressValueError
import re
import typing as t
from functools import partial

import dash
import dash_bootstrap_components as dbc
import requests
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
    ReadTimeout as RequestsReadTimeout,
)
from dash import html
from dash.dependencies import ClientsideFunction, Input, Output, State
from dash.exceptions import PreventUpdate
from dash_extensions.enrich import Trigger

from ....models import RegisteredCamera
from ... import pages
from ...app import TimelapseEncoder, app, db
from ...enums import Element as El
from . import modals


class FieldValidationError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__()


def FormFieldFeedbackError(message):
    """Return an error message to be displayed next to a single field."""
    return dbc.Row(
        [
            dbc.Col(
                html.I(
                    className="bi-exclamation-circle me-3",
                    style={"fontSize": "1.3rem"},
                ),
                width="auto",
            ),
            dbc.Col(html.Span(message), style={"lineHeight": "normal"}),
        ],
        align="center",
        class_name="g-0 px-2 py-1",
        style={
            "color": "white",
            "borderStyle": "solid",
            "borderRadius": "4px",
            "borderWidth": "2px",
            "borderColor": "red",
            "backgroundColor": "#f44336",
        },
    )


@app.callback(
    Output(El.PAGE_CONTENT, "children"),
    [Input(El.CAMERA_SELECT, "value")],
    prevent_initial_call=False,
)
def load_main_content(camera_id):
    # camera_id == -1 means that there are no cameras at all
    return pages.MAIN_LAYOUT(camera_id)


@app.callback([Input("timelapse-encoding-global-interval", "n_intervals")])
def timelapse_encoding_complete(tick):
    if not TimelapseEncoder.encoding:
        # this branch will get hit when the encoding finishes. We assume it completed successfully
        return [
            Output("timelapse-encoding-global-interval", "disabled", True),
            Output("timelapse-encoding-complete", "is_open", True),
        ]


@app.callback(
    Output(El.ADD_CAMERA_MODAL, "is_open"),
    [
        Input(El.ADD_CAMERA_MODAL_BUTTON_OPEN, "n_clicks"),
        Input(El.ADD_CAMERA_MODAL_BUTTON_CLOSE, "n_clicks"),
    ],
    [State(El.ADD_CAMERA_MODAL, "is_open")],
)
def open_add_camera_modal(open_clicks, close_clicks, is_open):
    return not is_open


def validate_ip_address(ip_addr: str, partial: bool = False) -> t.Tuple[str, bool]:
    """Ensure a well-formed IP address is provided."""
    # this should only be called when there is actually a value to parse
    assert ip_addr
    error = FieldValidationError("IP address must be in the format of a standard IPv4 address")

    try:
        ip_addr = str(IPv4Address(ip_addr))
    except AddressValueError:
        if not partial:
            raise error
    else:
        return ip_addr, True

    # verify we are only dealing with decimal points and numbers
    for p in ip_addr:
        if not p.isnumeric() and p != ".":
            raise error

    # the first character must be a number, and we definitely shouldn't have consecutive "."
    if not ip_addr[0].isnumeric() or ".." in ip_addr:
        raise error

    parts = ip_addr.split(".")
    # the condition here strips trailing empty strings when a partial ip_addr
    # ends with a "."
    octals = [int(octal) for octal in parts if octal]
    if any([octal > 255 for octal in octals]):
        raise error

    if len(parts) > 4:
        raise error

    return ip_addr, False


def validate_port(port: str, partial: bool = False) -> t.Tuple[int, bool]:
    """Ensure a well formed port is provided."""
    assert port
    error = FieldValidationError("Port must be an integer between 1024 and 65535, inclusive")
    try:
        port = int(port)
    except ValueError:
        raise error

    if port > 65_535:
        raise error

    # partial or not, port is now fully valid
    if port >= 1024:
        return port, True
    # if we are allowing a partial input, then this is still valid at present
    elif partial:
        return port, False
    # but otherwise the value for port is too low
    raise error


def validate_camera_name(name: str) -> str:
    """Ensure a well-formed camera name is provided."""
    assert name
    error = FieldValidationError(
        "Camera name must be an string between 1 and 30 characters in length, inclusive"
    )
    name = name.strip()
    if not (1 <= len(name) <= 30):
        raise error
    return name


@app.callback(
    [
        Output(El.ADD_CAMERA_MODAL_BUTTON_SAVE, "children"),
        Output(El.ADD_CAMERA_MODAL_BUTTON_SAVE, "disabled"),
    ],
    [
        Trigger(El.ADD_CAMERA_MODAL_BUTTON_SAVE, "n_clicks"),
        Trigger(El.ADD_CAMERA_IP_ADDRESS_INPUT, "n_submit"),
        Trigger(El.ADD_CAMERA_PORT_INPUT, "n_submit"),
        Trigger(El.ADD_CAMERA_NAME_INPUT, "n_submit"),
    ],
    [
        State("FORM_FULLY_VALID", "value"),
    ],
)
def submit_form(form_is_valid: bool):
    print(f"submit! form valid: {form_is_valid}")
    # block any trigger when the save button is disabled
    if not form_is_valid:
        raise PreventUpdate

    return dbc.Spinner(size="sm"), True


@app.callback(
    Output(El.ADD_CAMERA_MODAL_BUTTON_SAVE, "disabled"), [Input("FORM_FULLY_VALID", "value")]
)
def form_is_valid(form_is_valid):
    if form_is_valid:
        return False
    return True


@app.callback(
    Output("FORM_FULLY_VALID", "value"),
    [
        Input(El.ADD_CAMERA_IP_ADDRESS_INPUT_FULLY_VALID, "value"),
        Input(El.ADD_CAMERA_PORT_INPUT_FULLY_VALID, "value"),
        Input(El.ADD_CAMERA_NAME_INPUT_FULLY_VALID, "value"),
    ],
)
def check_form_fully_valid(ip_addr_valid, port_valid, name_valid):
    if all([ip_addr_valid, port_valid, name_valid]):
        return True
    return False


@app.callback(
    [
        Output(El.ADD_CAMERA_FORM_SUBMISSION_ERROR, "style"),
        Output(El.ADD_CAMERA_FORM_SUBMISSION_ERROR_TEXT, "children"),
        Output(El.ADD_CAMERA_MODAL, "is_open"),
        Output("add-camera-toast", "is_open"),
        Output(El.CAMERA_SELECT, "options"),
        Output(El.CAMERA_SELECT, "value"),
        Output("SAVE_CAM_BUTTON_DIV", "children"),
    ],
    [Input(El.ADD_CAMERA_MODAL_BUTTON_SAVE, "children")],
    [
        State(El.ADD_CAMERA_IP_ADDRESS_INPUT, "value"),
        State(El.ADD_CAMERA_PORT_INPUT, "value"),
        State(El.ADD_CAMERA_NAME_INPUT, "value"),
        State(El.CAMERA_SELECT, "options"),
        State(El.CAMERA_SELECT, "value"),
        State(El.ADD_CAMERA_FORM_SUBMISSION_ERROR, "style"),
    ],
)
def register_new_camera(
    save_button_children: list,
    ip_addr: str,
    port: str,
    camera_name: str,
    camera_select_options: t.List[t.Dict[str, t.Any]],
    camera_select_value: int,
    form_error_style: t.Dict[str, str],
):
    assert save_button_children["type"] == "Spinner"

    from pydantic import BaseModel

    form_error_style.update({"display": "none"})

    class CallbackOutput(BaseModel):
        submission_error_style: dict = form_error_style
        form_error_text: str = ""
        modal_is_open: bool = True
        toast_is_open: bool = False
        camera_select_options: list
        camera_select_value: int
        save_cam_button: t.Any = modals.make_save_camera_button(disabled=False)

        def values(self):
            return tuple(val for _, val in self)

    output = CallbackOutput(
        camera_select_options=camera_select_options, camera_select_value=camera_select_value
    )

    # we know that these validators won't fail, but we use them here to convert the types
    try:
        ip_addr, _ = validate_ip_address(ip_addr)
        port, _ = validate_port(port)
        camera_name = validate_camera_name(camera_name)
    except (FieldValidationError, AssertionError):
        # this should be unreachable, but there are certain race conditions which can trigger it. If
        # this happens, we just need to reset the submit button. It's not quite perfect but it's
        # good enough for now
        return output.values()

    # all the basic form validation is now done, so we can proceed with the business
    # logic of registering a camera

    # start with checking whether this camera IP address is already registered
    if (
        db.session.query(RegisteredCamera.camera_id)
        .filter(RegisteredCamera.ip_address == ip_addr)
        .scalar()
        is not None
    ):
        output.submission_error_style.update({"display": "flex"})
        output.form_error_text = "IP address already registered!"
        return output.values()

    # then check if a camera with this name already exists
    if (
        db.session.query(RegisteredCamera.camera_id)
        .filter(RegisteredCamera.name == camera_name)
        .scalar()
        is not None
    ):
        output.submission_error_style.update({"display": "flex"})
        output.form_error_text = "A camera with this name already exists!"
        return output.values()

    # then check the connection by pinging the camera server
    try:
        requests.get(f"http://{ip_addr}:{port}/ping", timeout=0.2).json() == "pong"
    except (RequestsConnectionError, RequestsReadTimeout):
        output.submission_error_style.update({"display": "flex"})
        output.form_error_text = "No camera found at this location!"
        return output.values()

    # then pair the client and server together
    try:
        resp = requests.post(
            f"http://{ip_addr}:{port}/register",
            json={"port": app.server.config["PORT"], "camera_name": camera_name},
        ).json()
        app.logger.info(resp)
    except RequestsConnectionError:
        output.submission_error_style.update({"display": "flex"})
        output.form_error_text = "Failed to pair the server and camera!"
        return output.values()

    # if all of the above is satisfied, save the camera to the database
    new_camera = RegisteredCamera(ip_address=ip_addr, port=port, name=camera_name)
    db.session.add(new_camera)
    db.session.commit()

    app.logger.info("New remote camera added: %r", new_camera)

    # set up the camera select dropdown component to include the new camera
    cams = db.session.query(RegisteredCamera).order_by(RegisteredCamera.name.asc())
    options = [{"label": cam.name, "value": cam.camera_id} for cam in cams]

    output.modal_is_open = False
    output.toast_is_open = True
    output.camera_select_options = options
    output.camera_select_value = new_camera.camera_id

    return output.values()


@app.callback(
    [
        Output(El.ADD_CAMERA_IP_ADDRESS_INPUT, "invalid"),
        Output(El.ADD_CAMERA_IP_ADDRESS_INPUT_FULLY_VALID, "value"),
        Output(El.ADD_CAMERA_IP_ADDRESS_FORM_FEEDBACK, "children"),
    ],
    [
        Input(El.ADD_CAMERA_IP_ADDRESS_INPUT, "value"),
        Input(El.ADD_CAMERA_IP_ADDRESS_INPUT, "n_blur"),
    ],
)
def validate_ip_address_input(ip_addr, n_blur):
    # allow the field to be empty whilst the user is still filling in the form
    if not ip_addr:
        return False, False, None

    trigger = dash.callback_context.triggered[0]["prop_id"].split(".")[1]
    allow_partial = trigger == "value"

    try:
        _, fully_valid = validate_ip_address(ip_addr, partial=allow_partial)
    except FieldValidationError as e:
        return True, False, FormFieldFeedbackError(e.message)
    return False, fully_valid, None


@app.callback(
    [
        Output(El.ADD_CAMERA_PORT_INPUT, "invalid"),
        Output(El.ADD_CAMERA_PORT_INPUT_FULLY_VALID, "value"),
        Output(El.ADD_CAMERA_PORT_FORM_FEEDBACK, "children"),
    ],
    [
        Input(El.ADD_CAMERA_PORT_INPUT, "value"),
        Input(El.ADD_CAMERA_PORT_INPUT, "n_blur"),
    ],
)
def validate_port_input(port, n_blur):
    # allow the field to be empty whilst the user is still filling in the form
    if not port:
        return False, False, None

    trigger = dash.callback_context.triggered[0]["prop_id"].split(".")[1]
    allow_partial = trigger == "value"

    try:
        _, fully_valid = validate_port(port, partial=allow_partial)
    except FieldValidationError as e:
        return True, False, FormFieldFeedbackError(e.message)
    return False, fully_valid, None


@app.callback(
    [
        Output(El.ADD_CAMERA_NAME_INPUT, "invalid"),
        Output(El.ADD_CAMERA_NAME_INPUT_FULLY_VALID, "value"),
        Output(El.ADD_CAMERA_NAME_FORM_FEEDBACK, "children"),
    ],
    [
        Input(El.ADD_CAMERA_NAME_INPUT, "value"),
    ],
)
def validate_camera_name_input(name: t.Optional[str]):
    if not name:
        return False, False, None

    try:
        validate_camera_name(name)
    except FieldValidationError as e:
        return True, False, FormFieldFeedbackError(e.message)
    return False, True, None


@app.callback(
    None,
    [Input(El.DELETE_CAMERA_MODAL_BUTTON_OPEN, "n_clicks")],
    [State(El.CAMERA_SELECT, "value"), State(El.DELETE_CAMERA_MODAL, "is_open")],
)
def open_delete_camera_modal(n_clicks, camera_id, is_open):
    cam = RegisteredCamera.query.get(camera_id)

    return (
        Output(El.DELETE_CAMERA_MODAL, "is_open", not is_open),
        Output(El.DELETE_CAMERA_NAME, "children", cam.name),
    )


@app.callback(None, [Input(El.DELETE_CAMERA_MODAL_BUTTON_CLOSE, "n_clicks")])
def close_delete_camera_modal(clicks):
    return Output(El.DELETE_CAMERA_MODAL, "is_open", False)


@app.callback(
    None,
    [Input(El.DELETE_CAMERA_MODAL_BUTTON_CONFIRM, "n_clicks")],
    [State(El.CAMERA_SELECT, "value")],
)
def delete_camera_confirm(clicks, camera_id):
    cam = RegisteredCamera.query.get(camera_id)
    cam.delete()

    # get the id of the next camera to display once this one is deleted
    cams = db.session.query(RegisteredCamera).order_by(RegisteredCamera.name.asc())
    options = [{"label": cam.name, "value": cam.camera_id} for cam in cams]
    options = options or [{"label": "No cameras found!", "value": -1, "disabled": True}]

    try:
        resp = requests.post(
            f"http://{cam.ip_address}:{cam.port}/unregister",
        ).json()
    except:  # noqa
        # doesn't actually matter if we can't reach the remote camera, so log it and move on
        app.logger.info("Unable to reach remote camera.")
    else:
        app.logger.info(resp)

    return (
        Output("delete-camera-toast", "is_open", True),
        Output(El.DELETE_CAMERA_MODAL, "is_open", False),
        Output(El.CAMERA_SELECT, "options", options),
        Output(El.CAMERA_SELECT, "value", options[0]["value"]),
    )


@app.callback(
    Output(El.DELETE_CAMERA_MODAL_BUTTON_OPEN, "style"), [Input(El.CAMERA_SELECT, "options")]
)
def toggle_delete_camera_button_display(options):
    new_style = {"display": "block"}
    if options[0]["value"] == -1:
        new_style["display"] = "none"
    return new_style


# set focus on first form field when "add camera" modal opens
app.clientside_callback(
    ClientsideFunction(namespace="clientside", function_name="focus_form_field"),
    Output("form-focus-hidden-div", "children"),
    [Input(El.ADD_CAMERA_MODAL, "is_open")],
    [State(El.ADD_CAMERA_IP_ADDRESS_INPUT, "id")],
)

import copy

import dash_bootstrap_components as dbc
from dash import dcc
from dash import html
import time
from flask import request
from requests.exceptions import ConnectionError

from ....auth.youtube_service import YouTubeHandler
from ...enums import Element as El
from ...app import app


def make_sidebar(cam):
    try:
        camera_config = cam.get_config()
    except ConnectionError:
        return html.Div("Camera not found! Are you sure it's online?")

    resolution_options = [
        {"label": "1920x1080 (16:9)", "value": "1920x1080"},
        {"label": "1640x1232 (4:3)", "value": "1640x1232"},
        {"label": "1640x922 (16:9)", "value": "1640x922"},
        {"label": "1280x720 (16:9)", "value": "1280x720"},
        {"label": "1200x900 (4:3)", "value": "1200x900"},
        {"label": "1024x768 (4:3)", "value": "1024x768"},
        {"label": "640x480 (4:3)", "value": "640x480"},
    ]

    viewport_resolution_options = copy.deepcopy(resolution_options)
    viewport_resolution_options.insert(3, {"label": "1440x1080 (4:3)", "value": "1440x1080"})

    exposure_modes = ["auto", "nightpreview"]
    exposure_mode_options = [{"label": mode.capitalize(), "value": mode} for mode in exposure_modes]

    return dbc.Row(
        dbc.Col(
            [
                dbc.Row(dbc.Col(make_camera_config_header())),
                dbc.Row(
                    dbc.Col(
                        [
                            _make_input_row(
                                label_text="Camera Name",
                                label_width=4,
                                input_type="text",
                                input_value=cam.name,
                                input_id=El.CAMERA_NAME_INPUT,
                            ),
                            _make_input_row(
                                label_text="Camera URL",
                                label_width=4,
                                input_type="text",
                                input_value=cam.client_url,
                                input_id=El.CAMERA_URL_INPUT,
                            ),
                            _make_dropdown_row(
                                label_text="Resolution",
                                label_width=4,
                                dropdown_options=resolution_options,
                                dropdown_value=camera_config["camera"]["resolution"],
                                dropdown_id=El.CAMERA_RESOLUTION_INPUT,
                            ),
                            _make_input_row(
                                label_text="Framerate",
                                label_width=4,
                                input_type="number",
                                input_value=camera_config["camera"]["framerate"],
                                input_id=El.CAMERA_FRAMERATE_INPUT,
                            ),
                            _make_dropdown_row(
                                label_text="Viewport Size",
                                label_width=4,
                                dropdown_options=viewport_resolution_options,
                                dropdown_value=camera_config["global"]["viewport_size"],
                                dropdown_id=El.CAMERA_VIEWPORT_SIZE_INPUT,
                            ),
                            _make_dropdown_row(
                                label_text="AWB Mode",
                                label_width=4,
                                dropdown_options=[
                                    {"label": "Auto (default)", "value": "auto"},
                                    {"label": "Greyworld", "value": "greyworld"},
                                    {"label": "Off", "value": "off"},
                                ],
                                dropdown_value=camera_config["camera"]["awb_mode"],
                                dropdown_id=El.CAMERA_AWB_MODE_INPUT,
                            ),
                            _make_dropdown_row(
                                label_text="Exposure Mode",
                                label_width=4,
                                dropdown_options=exposure_mode_options,
                                dropdown_value=camera_config["camera"]["exposure_mode"],
                                dropdown_id=El.CAMERA_EXPOSURE_MODE_INPUT,
                            ),
                            _make_dropdown_row(
                                label_text="Vflip",
                                label_width=4,
                                dropdown_options=[
                                    {"label": "True", "value": 1},
                                    {"label": "False", "value": 0},
                                ],
                                dropdown_value=int(camera_config["camera"]["vflip"]),
                                dropdown_id=El.CAMERA_VFLIP_INPUT,
                            ),
                            _make_dropdown_row(
                                label_text="Hflip",
                                label_width=4,
                                dropdown_options=[
                                    {"label": "True", "value": 1},
                                    {"label": "False", "value": 0},
                                ],
                                dropdown_value=int(camera_config["camera"]["hflip"]),
                                dropdown_id=El.CAMERA_HFLIP_INPUT,
                            ),
                            *make_livestream_sidebar_settings(
                                camera_config["outputs"]["livestream"]
                            ),
                            *make_timelapse_sidebar_settings(camera_config["outputs"]["timelapse"]),
                            *make_motion_sidebar_settings(camera_config["outputs"]["motion"]),
                            dcc.Store(storage_type="memory", id=El.CHANGED_CONFIG_STORE),
                        ],
                        style={"overflowY": "scroll", "paddingTop": "32px", "maxHeight": "100%"},
                    ),
                    # the camera config sidebar header has a height of 56px
                    style={"height": "calc(100% - 56px)"},
                ),
            ],
            style={"maxHeight": "100%"},
        ),
        className="bg-dark",
        style={"height": "100%"},
    )


def make_camera_config_header():
    return dbc.Row(
        [
            dbc.Col(),
            dbc.Col(
                html.H5(
                    "Camera Configuration",
                    style={"margin": 0, "textAlign": "center"},
                ),
                align="center",
                width=6,
                style={"padding": 0},
            ),
            dbc.Col(dbc.Button("Save", id=El.SAVE_CAMERA_CONFIG_BUTTON, style={"display": "none"})),
        ],
        align="center",
        style={"backgroundColor": "#6982FF", "height": 56},
    )


def make_livestream_sidebar_settings(conf):
    return (
        _make_output_subheading("Livestream", El.LIVESTREAM_OUTPUT_LINK, enabled=None),
        _make_input_row(
            label_text="Bitrate (bps)",
            label_width=5,
            input_type="number",
            input_value=conf["bitrate"],
            input_id=El.CAMERA_NETWORK_BITRATE_INPUT,
        ),
        _make_checkbox_row(
            label_text="Enable YouTube",
            label_width=5,
            checked=conf["youtube_mode"],
            checkbox_id="livestream-youtube-enabled",
        ),
    )


def make_timelapse_sidebar_settings(conf):
    return (
        _make_output_subheading("Timelapse", El.TIMELAPSE_OUTPUT_LINK, enabled=conf["enabled"]),
        _make_input_row(
            label_text="Capture Interval (s)",
            label_width=5,
            input_type="number",
            input_value=conf["capture_interval"],
            input_id=El.CAMERA_TIMELAPSE_CAPTURE_INTERVAL_INPUT,
        ),
    )


def make_motion_sidebar_settings(conf):
    # could need:
    #     bitrate
    return (
        _make_output_subheading("Motion", El.MOTION_OUTPUT_LINK, enabled=conf["enabled"]),
        _make_input_row(
            label_text="Captured Before (s)",
            label_width=5,
            input_type="number",
            input_value=conf["captured_before"],
            input_id=El.CAMERA_MOTION_CAPTURED_BEFORE_INPUT,
        ),
        _make_input_row(
            label_text="Captured After (s)",
            label_width=5,
            input_type="number",
            input_value=conf["captured_after"],
            input_id=El.CAMERA_MOTION_CAPTURED_AFTER_INPUT,
        ),
        _make_input_row(
            label_text="Motion Interval (s)",
            label_width=5,
            input_type="number",
            input_value=conf["motion_interval"],
            input_id=El.CAMERA_MOTION_INTERVAL_INPUT,
        ),
        _make_input_row(
            label_text="Min. Frames (s)",
            label_width=5,
            input_type="number",
            input_value=conf["min_frames"],
            input_id=El.CAMERA_MOTION_MIN_FRAMES_INPUT,
        ),
        _make_input_row(
            label_text="Min. Blocks (s)",
            label_width=5,
            input_type="number",
            input_value=conf["min_blocks"],
            input_id=El.CAMERA_MOTION_MIN_BLOCKS_INPUT,
        ),
        _make_togglable_input_row(
            label_text="Email Notifications",
            label_width=5,
            input_type="text",
            enabled=conf["notifications_enabled"],
            input_value=conf["notifications_email_address"],
            input_id="motion-email-notifications-input",
            enabled_id="motion-email-notifications-enabled",
        ),
    )


def _make_checkbox_row(label_text, label_width, checked, checkbox_id):
    return html.Div(
        [
            _make_parameter_label(label_text, label_width),
            dbc.Col(
                dbc.Checkbox(
                    id=checkbox_id, checked=checked, style={"height": "15px", "width": "15px"}
                )
            ),
        ],
        row=True,
        style={"alignItems": "center"},
    )


def _make_input_row(label_text, label_width, input_type, input_value, input_id):
    return html.Div(
        [
            _make_parameter_label(label_text, label_width),
            dbc.Col(
                dbc.Input(
                    type=input_type,
                    value=input_value,
                    id=input_id,
                ),
            ),
        ],
        style={"alignItems": "center"},
    )


def _make_togglable_input_row(
    label_text, label_width, input_type, enabled, input_value, input_id, enabled_id
):
    return html.Div(
        [
            _make_parameter_label(label_text, label_width),
            dbc.Col(
                dbc.InputGroup(
                    [
                        dbc.InputGroupAddon(
                            dbc.Checkbox(id=enabled_id, checked=enabled), addon_type="prepend"
                        ),
                        dbc.Input(
                            type=input_type, value=input_value, id=input_id, disabled=not enabled
                        ),
                    ]
                )
            ),
        ],
        style={"alignItems": "center"},
    )


def _make_dropdown_row(label_text, label_width, dropdown_options, dropdown_value, dropdown_id):
    return html.Div(
        [
            _make_parameter_label(label_text, label_width),
            dbc.Col(
                dcc.Dropdown(
                    options=dropdown_options,
                    value=dropdown_value,
                    clearable=False,
                    searchable=False,
                    style={"color": "black"},
                    id=dropdown_id,
                ),
            ),
        ],
        style={"alignItems": "center"},
    )


def _make_parameter_label(label_text, label_width):
    return dbc.Label(label_text, width=label_width)


def _make_output_subheading(heading, nav_id, enabled=None, disable_toggle=False):
    heading_id = "-".join(heading.lower().split())
    toggle = None
    if enabled is not None:
        toggle = dbc.Checklist(
            id=f"{heading_id}-output-enabled-switch",
            options=[{"label": "", "value": True, "disabled": disable_toggle}],
            value=[True] if enabled else [],
            switch=True,
        )
    return dbc.Row(
        [
            dbc.Col(width=4),
            dbc.Col(
                html.H6(
                    dbc.NavLink(
                        heading,
                        id=nav_id,
                        href="#",
                        className="output-nav-link",
                        active=nav_id == El.TIMELAPSE_OUTPUT_LINK,
                    ),
                    style={"margin": 0, "textAlign": "center"},
                ),
                width=4,
            ),
            dbc.Col(width=1),
            dbc.Col(
                toggle,
                width=2,
            ),
        ],
        align="center",
        style={"backgroundColor": "#6c757d", "height": 32, "marginBottom": 24},
    )

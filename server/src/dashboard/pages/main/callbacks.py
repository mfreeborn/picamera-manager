import dash
import requests
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from ....models import RegisteredCamera
from ...app import app
from ...enums import Element as El
from . import livestream, motion, timelapse


@app.callback(
    Output(El.OUTPUT_CONTENT_DIV, "children"),
    [Input(El.ACTIVE_OUTPUT, "value"), Input(El.RELOAD_OUTPUT_CONTENT_FLAG, "value")],
    [State(El.CAMERA_SELECT, "value")],
    prevent_initial_call=False,
)
def load_output_display(active_output, reload_flag, camera_id):
    print("active_output", active_output)
    DEFAULT_DISPLAY = "livestream"
    if active_output is None:
        active_output = DEFAULT_DISPLAY

    ctx = dash.callback_context
    # TODO: think this won't work now because it is a circular import
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    if trigger == El.RELOAD_OUTPUT_CONTENT_FLAG and not reload_flag:
        # this prevents double-reloads
        raise PreventUpdate

    cam = RegisteredCamera.query.get(camera_id)
    output_map = {
        "livestream": livestream.make_livestream_output_content,
        "timelapse": timelapse.make_timelapse_output_content,
        "motion": motion.make_motion_output_content,
    }

    return output_map[active_output](cam)


@app.callback(
    None,
    [
        Input("timelapse-output-enabled-switch", "value"),
        Input("motion-output-enabled-switch", "value"),
    ],
    [State(El.ACTIVE_OUTPUT, "value"), State(El.CAMERA_SELECT, "value")],
)
def output_enabled_toggle(timelapse_enabled, motion_enabled, active_output, camera_id):
    """Tell the camera to either add or remove the specified output."""
    ctx = dash.callback_context

    trigger = ctx.triggered[0]
    # this is one of "timelapse" or "motion"
    output_type = trigger["prop_id"].split("-")[0]
    # trigger["value"] is [1] if enabled, otherwise []
    enabled = bool(trigger["value"])
    action = "disable-output"
    if enabled:
        action = "enable-output"

    cam = RegisteredCamera.query.get(camera_id)

    ret = requests.post(f"{cam.client_url}/{action}", json={"output_type": output_type}).json()
    print(ret)

    # only reload the output view if the switch we toggled is for the output
    # we are currently viewing
    if output_type == active_output:
        return Output(El.RELOAD_OUTPUT_CONTENT_FLAG, "value", True)


@app.callback(
    Output(El.CHANGED_CONFIG_STORE, "data"),
    [
        Input(El.CAMERA_NAME_INPUT, "value"),
        Input(El.CAMERA_RESOLUTION_INPUT, "value"),
        Input(El.CAMERA_FRAMERATE_INPUT, "value"),
        Input(El.CAMERA_VIEWPORT_SIZE_INPUT, "value"),
        Input(El.CAMERA_AWB_MODE_INPUT, "value"),
        Input(El.CAMERA_EXPOSURE_MODE_INPUT, "value"),
        Input(El.CAMERA_VFLIP_INPUT, "value"),
        Input(El.CAMERA_HFLIP_INPUT, "value"),
        Input(El.CAMERA_NETWORK_BITRATE_INPUT, "value"),
        Input("livestream-youtube-enabled", "checked"),
        Input(El.CAMERA_TIMELAPSE_CAPTURE_INTERVAL_INPUT, "value"),
        Input(El.CAMERA_MOTION_CAPTURED_BEFORE_INPUT, "value"),
        Input(El.CAMERA_MOTION_CAPTURED_AFTER_INPUT, "value"),
        Input(El.CAMERA_MOTION_INTERVAL_INPUT, "value"),
        Input(El.CAMERA_MOTION_MIN_FRAMES_INPUT, "value"),
        Input(El.CAMERA_MOTION_MIN_BLOCKS_INPUT, "value"),
        Input("motion-email-notifications-enabled", "checked"),
        Input("motion-email-notifications-input", "value"),
    ],
    [State(El.CAMERA_SELECT, "value")],
)
def store_changed_config(
    name,
    res,
    framerate,
    viewport_size,
    awb_mode,
    exposure_mode,
    vflip,
    hflip,
    livestream_bitrate,
    youtube_enabled,
    cap_interval,
    motion_before,
    motion_after,
    motion_interval,
    motion_min_frames,
    motion_min_blocks,
    notifications_enabled,
    notifications_email_address,
    camera_id,
):
    if name is None:
        raise PreventUpdate

    cam = RegisteredCamera.query.get(camera_id)
    camera_config = cam.get_config()

    # we need to get all the new parameters and all the old parameters and find out which changed
    params = [
        ("global_name", cam.name, name),
        ("camera_resolution", camera_config["camera"]["resolution"], res),
        ("camera_framerate", camera_config["camera"]["framerate"], framerate),
        ("global_viewport_size", camera_config["global"]["viewport_size"], viewport_size),
        ("camera_awb_mode", camera_config["camera"]["awb_mode"], awb_mode),
        ("camera_exposure_mode", camera_config["camera"]["exposure_mode"], exposure_mode),
        ("camera_vflip", camera_config["camera"]["vflip"], vflip),
        ("camera_hflip", camera_config["camera"]["hflip"], hflip),
        (
            "livestream_bitrate",
            camera_config["outputs"]["livestream"]["bitrate"],
            livestream_bitrate,
        ),
        (
            "livestream_youtube_mode",
            camera_config["outputs"]["livestream"]["youtube_mode"],
            youtube_enabled,
        ),
        (
            "timelapse_capture_interval",
            camera_config["outputs"]["timelapse"]["capture_interval"],
            cap_interval,
        ),
        (
            "motion_captured_before",
            camera_config["outputs"]["motion"]["captured_before"],
            motion_before,
        ),
        (
            "motion_captured_after",
            camera_config["outputs"]["motion"]["captured_after"],
            motion_after,
        ),
        (
            "motion_motion_interval",
            camera_config["outputs"]["motion"]["motion_interval"],
            motion_interval,
        ),
        ("motion_min_frames", camera_config["outputs"]["motion"]["min_frames"], motion_min_frames),
        ("motion_min_blocks", camera_config["outputs"]["motion"]["min_blocks"], motion_min_blocks),
        (
            "motion_notifications_enabled",
            camera_config["outputs"]["motion"]["notifications_enabled"],
            notifications_enabled,
        ),
        (
            "motion_notifications_email_address",
            camera_config["outputs"]["motion"]["notifications_email_address"],
            notifications_email_address,
        ),
    ]

    old_params = set((p[0], p[1]) for p in params)
    new_params = set((p[0], p[2]) for p in params)

    # diff will be a set of 2-tuples containing the changed parameters
    diff = new_params - old_params
    return dict(diff)


@app.callback(
    Output(El.SAVE_CAMERA_CONFIG_BUTTON, "style"), [Input(El.CHANGED_CONFIG_STORE, "data")]
)
def toggle_save_button(new_config):
    if new_config:
        return {"display": "inline"}
    return {"display": "none"}


@app.callback(
    None,
    [Input(El.SAVE_CAMERA_CONFIG_BUTTON, "n_clicks")],
    [
        State(El.CHANGED_CONFIG_STORE, "data"),
        State(El.CAMERA_SELECT, "value"),
    ],
)
def save_new_config(click, new_config, camera_id):
    if click is None:
        raise PreventUpdate

    cam = RegisteredCamera.query.get(camera_id)

    # set the new configuration
    requests.post(f"{cam.client_url}/config", json=new_config).json()

    # clear the store on exit and reload the output component
    return (
        Output(El.CHANGED_CONFIG_STORE, "data", {}),
        Output(El.RELOAD_OUTPUT_CONTENT_FLAG, "value", True),
    )


@app.callback(
    None,
    [
        Input(El.LIVESTREAM_OUTPUT_LINK, "n_clicks"),
        Input(El.TIMELAPSE_OUTPUT_LINK, "n_clicks"),
        Input(El.MOTION_OUTPUT_LINK, "n_clicks"),
    ],
)
def change_output(livestream_clicks, timelapse_clicks, motion_clicks):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == El.LIVESTREAM_OUTPUT_LINK:
        active_states = [True, False, False]
        active_output = "livestream"

    elif trigger == El.TIMELAPSE_OUTPUT_LINK:
        active_states = [False, True, False]
        active_output = "timelapse"

    elif trigger == El.MOTION_OUTPUT_LINK:
        active_states = [False, False, True]
        active_output = "motion"

    return [Output(El.ACTIVE_OUTPUT, "value", active_output)] + [
        Output(el, "active", state)
        for el, state in zip(
            [
                El.LIVESTREAM_OUTPUT_LINK,
                El.TIMELAPSE_OUTPUT_LINK,
                El.MOTION_OUTPUT_LINK,
            ],
            active_states,
        )
    ]


@app.callback(
    None,
    [Input("motion-email-notifications-enabled", "checked")],
)
def toggle_input(enabled):
    return Output("motion-email-notifications-input", "disabled", not enabled)

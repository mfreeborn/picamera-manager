import base64
import datetime
import json
import os
from pathlib import Path
from urllib.parse import urlencode

import dash_bootstrap_components as dbc
import dash
from dash import html
from dash.dependencies import ALL, Input, Output, State
from dash.exceptions import PreventUpdate

from ......models import RegisteredCamera, TimelapseVideo, TimelapseImage
from .....app import TimelapseEncoder, app, db
from .....enums import Element as El
from ... import timelapse
from . import validators


@app.callback(
    None,
    [Input("timelapse-encoding-progress-interval", "n_intervals")],
    [State("refresh-timelapse-video-thumbnails", "value")],
)
def poll_timelapse_encoder(tick, refresh_value):
    if TimelapseEncoder.encoding:
        progress = TimelapseEncoder.progress
        progress_display = "0%"
        if 0 < progress < 1:
            progress_display = f"{progress:.1%}"
        else:
            progress_display = "100%"

        return [
            Output("ffmpeg-progress", "value", progress * 100),
            Output("ffmpeg-progress", "children", progress_display),
            Output("create-timelapse-submit", "disabled", True),
            Output("ffmpeg-progress", "style", {"display": "flex"}),
        ]
    else:
        # switch off the interval timer if there is no longer any encoding in progress
        return [
            Output("ffmpeg-progress", "value", 0),
            Output("ffmpeg-progress", "children", "0%"),
            Output("timelapse-encoding-progress-interval", "disabled", True),
            Output("create-timelapse-submit", "disabled", False),
            Output("ffmpeg-progress", "style", {"display": "none"}),
            Output("refresh-timelapse-video-thumbnails", "value", refresh_value + 1),
            Output("create-timelapse-modal", "is_open", False),
        ]


@app.callback(
    Output({"type": "timelapse-thumbnail-button-videos", "index": ALL}, "className"),
    [Input("selected-timelapse-video-id", "value")],
    [State({"type": "timelapse-thumbnail-button-videos", "index": ALL}, "id")],
)
def highlight_selected_thumbnail(video_id, ids):
    return [
        "focus" if video_id == thumbnail_components["index"] else None
        for thumbnail_components in ids
    ]


@app.callback(
    None,
    [Input("delete-timelapse-video-confirm-button", "n_clicks")],
    [
        State("selected-timelapse-video-id", "value"),
        State(El.CAMERA_SELECT, "value"),
        State("refresh-timelapse-video-thumbnails", "value"),
    ],
)
def delete_timelapse_video(click, video_id, camera_id, refresh_value):
    if click is None:
        raise PreventUpdate

    video = TimelapseVideo.query.filter(
        TimelapseVideo.camera_id == camera_id, TimelapseVideo.video_id == video_id
    ).one()
    filename = video.video_filename

    video.delete()

    return [
        Output("delete-timelapse-video-modal", "is_open", False),
        Output("delete-timelapse-video-toast", "is_open", True),
        Output("delete-timelapse-video-toast", "children", f"{filename} has been deleted"),
        Output("refresh-timelapse-video-thumbnails", "value", refresh_value + 1),
    ]


@app.callback(
    [
        Output("delete-timelapse-video-modal", "is_open"),
        Output("video-title-to-delete", "children"),
    ],
    [Input("open-delete-timelapse-video-modal", "n_clicks")],
    [State("selected-timelapse-video-id", "value"), State(El.CAMERA_SELECT, "value")],
)
def open_delete_timelapse_video_modal(click, video_id, camera_id):
    if click is None:
        raise PreventUpdate

    video = TimelapseVideo.query.filter(
        TimelapseVideo.camera_id == camera_id, TimelapseVideo.video_id == video_id
    ).one()

    return [True, video.video_filename]


@app.callback(None, [Input("delete-timelapse-video-cancel-modal-button", "n_clicks")])
def close_delete_timelapse_video_modal(click):
    return Output("delete-timelapse-video-modal", "is_open", False)


@app.callback(
    Output("selected-timelapse-video-id", "value"),
    [Input({"type": "timelapse-thumbnail-button-videos", "index": ALL}, "id")],
)
def set_initial_selected_timelapse_video(ids):
    if not ids:
        raise PreventUpdate

    video_id = ids[0]["index"]
    return video_id


@app.callback(
    Output("view-timelapse-video-div", "children"),
    [Input("selected-timelapse-video-id", "value")],
    [State(El.CAMERA_SELECT, "value")],
)
def load_timelapse_video_div(video_id, camera_id):
    video = TimelapseVideo.query.filter(
        TimelapseVideo.camera_id == camera_id, TimelapseVideo.video_id == video_id
    ).one()

    params = {"camera_id": camera_id, "video_id": video_id, "as_attachment": True}
    params = urlencode(params)
    video_url = (
        f"http://{app.server.config['SERVER_IP_ADDRESS']}:"
        f"{app.server.config['PORT']}/timelapse-video?{params}"
    )

    file_size = f"{video.video_path.stat().st_size / 1_000_000:.1f}MB"

    return [
        dbc.Row(
            [
                dbc.Col(html.H5(video.video_filename, style={"margin": 0}), width="auto"),
                dbc.Col(html.H6(f"[{file_size}]", style={"margin": 0}), width="auto"),
                dbc.Col(
                    dbc.DropdownMenu(
                        [
                            dbc.DropdownMenuItem("Delete", id="open-delete-timelapse-video-modal"),
                            dbc.DropdownMenuItem(
                                "Download",
                                id="download-timelapse-video-button",
                                href=video_url,
                                target="_self",
                            ),
                        ],
                        label="Actions ",
                        direction="right",
                        toggle_style={"paddingTop": 3, "paddingBottom": 3},
                    )
                ),
            ],
            align="center",
            style={"paddingBottom": 12},
        ),
        dbc.Row(
            dbc.Col(
                html.Video(
                    src=video_url, autoPlay=False, controls=True, style={"maxHeight": "100%"}
                ),
                style={"height": "100%"},
            ),
            style={"height": "100%"},
        ),
    ]


@app.callback(
    None, [Input({"type": "timelapse-thumbnail-button-videos", "index": ALL}, "n_clicks")]
)
def thumbnail_click(clicks):
    if not any(clicks):
        raise PreventUpdate

    video_id = json.loads(dash.callback_context.triggered[0]["prop_id"].rsplit(".", maxsplit=1)[0])[
        "index"
    ]

    return Output("selected-timelapse-video-id", "value", video_id)


@app.callback(
    Output("timelapse-videos-thumbnails-div", "children"),
    [
        Input("timelapse-video-output-content-container", "id"),  # first load
        Input("refresh-timelapse-video-thumbnails", "value"),  # subsequent loads
    ],
    [State(El.CAMERA_SELECT, "value")],
)
def load_video_thumbnails(_, refresh, camera_id):
    cam = RegisteredCamera.query.get(camera_id)

    n_videos = cam.timelapse_videos.with_entities(db.func.count(TimelapseVideo.video_id)).scalar()

    if not n_videos:
        return [
            Output("timelapse-videos-thumbnails-div", "children"),
            Output(
                "view-timelapse-video-div",
                "children",
                html.H5(
                    "Get started with making your first timelapse video by clicking the button!",
                    style={"fontStyle": "italic", "paddingTop": 12},
                ),
            ),
        ]

    videos = cam.timelapse_videos.order_by(TimelapseVideo.timestamp.desc())
    thumbnail_components = [
        timelapse.components.make_thumbnail_button(
            vid.video_filename,
            vid.title_image_to_base64(thumbnail=True),
            vid.video_id,
            "videos",
        )
        for vid in videos
    ]

    return thumbnail_components


@app.callback(
    None,
    [Input("create-timelapse-button", "n_clicks")],
    [State(El.CAMERA_SELECT, "value")],
)
def open_create_timelapse_modal(n_clicks, camera_id):
    cam = RegisteredCamera.query.get(camera_id)
    camera_name = cam.dir_name

    # set the default filename when the modal is opened
    now = datetime.datetime.now(datetime.timezone.utc)
    filename = f"{camera_name} {now:%Y-%m-%dT%H:%M:%SZ}"
    return [
        Output("create-timelapse-modal", "is_open", True),
        Output("create-timelapse-filename-input", "value", filename),
    ]


@app.callback(
    None,
    [
        Input("create-timelapse-filename-input", "value"),
        Input("create-timelapse-start-date-input", "value"),
        Input("create-timelapse-start-time-input", "value"),
        Input("create-timelapse-end-date-input", "value"),
        Input("create-timelapse-end-time-input", "value"),
        Input("create-timelapse-fps-input", "value"),
        Input("create-timelapse-divisor-input", "value"),
    ],
    [State(El.CAMERA_SELECT, "value")],
)
def validate_create_timelapse_form(
    filename, start_date, start_time, end_date, end_time, fps, divisor, camera_id
):
    # we will build up the outputs dynamically based on the validity of individual form fields
    outputs = []

    # validate filename
    filename = filename.strip()
    filename_error = validators.validate_filename(filename)
    invalid_filename = bool(filename_error)
    outputs.extend(
        [
            Output("create-timelapse-filename-input", "invalid", invalid_filename),
            Output(
                "create-timelapse-filename-input-feedback",
                "style",
                {"display": "block" if invalid_filename else "none"},
            ),
            Output("create-timelapse-filename-input-feedback", "children", filename_error),
        ]
    )

    # validate date range
    start_date = datetime.datetime.fromisoformat(f"{start_date}T{start_time}")
    end_date = datetime.datetime.fromisoformat(f"{end_date}T{end_time}")
    date_range_error = validators.validate_date_range(start_date, end_date)
    invalid_date_range = bool(date_range_error)
    outputs.extend(
        [
            Output("create-timelapse-end-date-input", "invalid", invalid_date_range),
            Output(
                "create-timelapse-date_range-input-feedback",
                "style",
                {"display": "block" if invalid_date_range else "none"},
            ),
            Output("create-timelapse-date_range-input-feedback", "children", date_range_error),
        ]
    )

    # validate fps
    fps_error = validators.validate_fps(fps)
    invalid_fps = bool(fps_error)
    outputs.extend(
        [
            Output("create-timelapse-fps-input", "invalid", invalid_fps),
            Output(
                "create-timelapse-fps-input-feedback",
                "style",
                {"display": "block" if invalid_fps else "none"},
            ),
            Output("create-timelapse-fps-input-feedback", "children", fps_error),
        ]
    )

    # validate divisor - this is only done if the fps validated correctly
    divisor_error = False
    if not invalid_fps:
        divisor_error = validators.validate_divisor(divisor, fps)
        invalid_divisor = bool(divisor_error)
        outputs.extend(
            [
                Output("create-timelapse-divisor-input", "invalid", invalid_divisor),
                Output(
                    "create-timelapse-divisor-input-feedback",
                    "style",
                    {"display": "block" if invalid_divisor else "none"},
                ),
                Output("create-timelapse-divisor-input-feedback", "children", divisor_error),
            ]
        )

    cam = RegisteredCamera.query.get(camera_id)
    n_images = (
        cam.timelapse_images.with_entities(db.func.count(TimelapseImage.image_id))
        .filter(TimelapseImage.timestamp.between(start_date, end_date))
        .scalar()
    )

    had_errors = any([invalid_filename, invalid_date_range, fps_error, divisor_error])
    outputs.append(
        Output(
            "create-timelapse-submit",
            "disabled",
            had_errors or TimelapseEncoder.encoding or n_images < 1,
        )
    )

    if not had_errors:
        if n_images < 1:
            info = "No images found - please choose a broader time range"
        else:
            n_images = max(1, n_images // divisor)
            info = (
                f"{n_images:,} image{'s' if n_images > 1 else ''} will be "
                f"converted into a {n_images / fps:,.1f} second video"
            )
        outputs.extend(
            [
                Output("timelapse-info", "children", info),
                Output("timelapse-info", "style", {"display": "block", "fontSize": "smaller"}),
            ]
        )
    else:
        outputs.append(Output("timelapse-info", "style", {"display": "none"}))

    return outputs


@app.callback(
    None,
    [Input("create-timelapse-submit", "n_clicks")],
    [
        State("create-timelapse-filename-input", "value"),
        State("create-timelapse-start-date-input", "value"),
        State("create-timelapse-start-time-input", "value"),
        State("create-timelapse-end-date-input", "value"),
        State("create-timelapse-end-time-input", "value"),
        State("create-timelapse-fps-input", "value"),
        State("create-timelapse-divisor-input", "value"),
        State(El.CAMERA_SELECT, "value"),
    ],
)
def submit_create_timelapse(
    n_clicks, file_stem, start_date, start_time, end_date, end_time, fps, divisor, camera_id
):
    if n_clicks is None or not all([start_date, start_time, end_date, end_time, fps]):
        raise PreventUpdate

    if TimelapseEncoder.encoding:
        # shouldn't hit this branch as we prevent it on the front end
        print("can't have more than one encoding job at a time!")

    start_date = datetime.datetime.fromisoformat(f"{start_date}T{start_time}:00")
    end_date = datetime.datetime.fromisoformat(f"{end_date}T{end_time}:00")

    cam = RegisteredCamera.query.get(camera_id)

    images = cam.timelapse_images.filter(
        TimelapseImage.timestamp.between(start_date, end_date)
    ).order_by(TimelapseImage.timestamp.asc())[::divisor]

    TimelapseEncoder.create_timelapse(images=images, file_stem=file_stem, fps=fps)

    print("Encoding status:", TimelapseEncoder.encoding)
    return [
        Output("timelapse-encoding-progress-interval", "disabled", False),
        Output("timelapse-encoding-global-interval", "disabled", False),
        Output("create-timelapse-submit", "disabled", True),
        Output("ffmpeg-progress", "style", {"display": "flex"}),
    ]

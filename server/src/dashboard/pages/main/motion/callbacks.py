import json

import dash
from dash import html
from dash.dependencies import ALL, Input, Output, State
from dash.exceptions import PreventUpdate

from .....models import MotionVideo, RegisteredCamera
from ....app import app, db
from ....enums import Element as El
from ....utils import get_date_dropdown_values
from . import components


@app.callback(
    Output("hidden-motion-div", "id"),  # anything arbitrary to trigger callback on page load
    [
        Input("motion-year-dropdown", "value"),
        Input("motion-month-dropdown", "value"),
        Input("selected-motion-day", "value"),
    ],
    [State(El.CAMERA_SELECT, "value")],
)
def load_timelapse_dropdown_options(year, month, day, camera_id):
    cam = RegisteredCamera.get(camera_id)
    # we either want to proceed when year, month and day are all None (i.e. first load),
    # or when all are present, in order to avoid partial reloads which don't make logical sense
    if not (
        (year is None and month is None and day is None)
        or (year is not None and month is not None and day is not None)
    ):
        raise PreventUpdate

    dropdown_values = get_date_dropdown_values(cam, MotionVideo, day=day, month=month, year=year)

    return (
        Output("motion-year-dropdown", "options", dropdown_values.years),
        Output("motion-year-dropdown", "value", dropdown_values.year),
        Output("motion-month-dropdown", "options", dropdown_values.months),
        Output("motion-month-dropdown", "value", dropdown_values.month),
        Output("motion-days-folder-row", "children", dropdown_values.days),
        Output("selected-motion-day", "value", dropdown_values.day),
    )


@app.callback(
    None,
    [Input({"type": "motion-day-folder", "index": ALL}, "n_clicks")],
    [
        State("selected-motion-day", "value"),
        State("refresh-motion-event-container", "value"),
    ],
)
def select_day(n_clicks, current_day, refresh_value):
    day = json.loads(dash.callback_context.triggered[0]["prop_id"].split(".")[0])["index"]
    if day == current_day:
        return Output("refresh-motion-event-container", "value", refresh_value + 1)
    return Output("selected-motion-day", "value", day)


@app.callback(
    Output({"type": "motion-day-folder", "index": ALL}, "className"),
    [Input("selected-motion-day", "value")],
    [
        State({"type": "motion-day-folder", "index": ALL}, "id"),
    ],
)
def highlight_selected_day(day, ids):
    # TODO: fix the fact that focus flashes on then off then on
    if day is None:
        raise PreventUpdate
    return ["focus" if day == folder_button["index"] else None for folder_button in ids]


@app.callback(
    None,
    [
        Input("selected-motion-day", "value"),
        Input("refresh-motion-event-container", "value"),
        Input("motion-ticker", "n_intervals"),
        Input("motion-current-page", "value"),
    ],
    [
        State("motion-month-dropdown", "value"),
        State("motion-year-dropdown", "value"),
        State(El.CAMERA_SELECT, "value"),
    ],
)
def update_displayed_images(day, _, tick, page, month, year, camera_id):
    # there aren't any videos to show if any of day, month or year are None
    if year is None:
        raise PreventUpdate

    cam = RegisteredCamera.query.get(camera_id)
    date = f"{year}-{month}-{day}"
    videos = cam.motion_videos.filter(MotionVideo.date == date)

    total_videos_count = videos.with_entities(db.func.count(MotionVideo.video_id)).scalar()

    # retrieve the paged list of motion events
    events_per_page = 35

    videos = (
        videos.order_by(MotionVideo.timestamp.desc())
        .limit(events_per_page)
        .offset((page - 1) * events_per_page)
        .all()
    )

    # build the thumbnails
    thumbnail_components = [components.make_thumbnail_button(vid) for vid in videos]

    if not total_videos_count:
        thumbnail_components = [
            html.I(
                "No videos found. Toggle the Motion function "
                '"on" to start recording motion triggered videos.'
            )
        ]

    # rebuild the pager component
    n_pages = (max(0, total_videos_count - 1) // events_per_page) + 1
    pager = components.make_pager(current_page=page, total_pages=n_pages)

    return [
        Output("motion-event-container", "children", thumbnail_components),
        Output("motion-table-pager-div", "children", pager),
        Output(
            "motion-total-event-count",
            "children",
            f"{total_videos_count} motion event{'s' if total_videos_count != 1 else ''}",
        ),
    ]


@app.callback(None, [Input({"type": "motion-thumbnail-button", "index": ALL}, "n_clicks")])
def toggle_carousel_modal(clicks):
    video_id = json.loads(dash.callback_context.triggered[0]["prop_id"].rsplit(".", maxsplit=1)[0])[
        "index"
    ]

    return (
        Output("motion-carousel-modal", "is_open", True),
        Output("selected-motion-event-input", "value", video_id),
    )


@app.callback(None, [Input("selected-motion-event-input", "value")])
def load_modal_content(video_id):
    video = MotionVideo.get(video_id)
    video_url = (
        f"http://{app.server.config['SERVER_IP_ADDRESS']}:"
        f"{app.server.config['PORT']}/motion-videos/{video_id}"
    )
    video_element = html.Video(
        src=f"{video_url}/video",
        poster=f"{video_url}/poster",
        autoPlay=False,
        controls=True,
        style={"maxHeight": "100%"},
    )

    # handle the left and right navigation arrows
    left_display = "flex" if video.has_next() else "none"
    right_display = "flex" if video.has_previous() else "none"
    return (
        Output("motion-carousel-modal-header", "children", video.video_filename),
        Output("motion-carousel-modal-content", "children", video_element),
        Output("motion-carousel-prev", "style", {"display": left_display}),
        Output("motion-carousel-next", "style", {"display": right_display}),
    )


@app.callback(
    None,
    [
        Input("motion-carousel-prev", "n_clicks"),
        Input("motion-carousel-next", "n_clicks"),
        Input("motion-carousel-key-press", "n_keydowns"),
    ],
    [
        State("motion-carousel-key-press", "keydown"),
        State("selected-motion-event-input", "value"),
    ],
)
def move_motion_carousel(click_prev, click_next, key_press, key_press_event, current_video_id):
    id_, trigger = dash.callback_context.triggered[0]["prop_id"].split(".")

    # parse out the direction when the user used the keyboard to navigate
    if trigger == "n_keydowns":
        key = key_press_event["key"]
        if key not in {"ArrowLeft", "ArrowRight"}:
            # we've just got a random key press which we can ignore
            raise PreventUpdate
        if key == "ArrowLeft":
            direction = "prev"
        else:
            direction = "next"
    # parse out the direction when the user clicked on of the carousel buttons
    else:
        direction = id_.split("-")[-1]

    # slightly back to front, but prev means "left" in the carousel, which means "newer"
    video = MotionVideo.get(current_video_id)
    if direction == "prev":
        new_video = video.next()
    else:
        new_video = video.previous()

    # this means we are at one end or the other of the carousel; no more videos
    if new_video is None:
        raise PreventUpdate

    return Output("selected-motion-event-input", "value", new_video.video_id)


@app.callback(Output("motion-ticker", "disabled"), [Input("motion-output-enabled-switch", "value")])
def toggle_motion_ticker(enabled):
    """Toggle the timelapse Interval ticker so that it only runs when the output is enabled."""
    if enabled:
        return False
    return True

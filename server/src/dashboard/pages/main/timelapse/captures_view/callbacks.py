import json

import dash
from dash import html
from dash.dependencies import ALL, Input, Output, State
from dash.exceptions import PreventUpdate

from ......models import RegisteredCamera, TimelapseImage
from .....app import app, db
from .....enums import Element as El
from .....utils import get_date_dropdown_values
from ... import timelapse
from . import components


@app.callback(
    Output("hidden-tl-div", "id"),  # anything arbitrary to trigger callback on page load
    [
        Input(El.TIMELAPSE_YEAR_DROPDOWN, "value"),
        Input(El.TIMELAPSE_MONTH_DROPDOWN, "value"),
        Input("selected-timelapse-day", "value"),
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

    dropdown_values = get_date_dropdown_values(cam, TimelapseImage, day=day, month=month, year=year)

    return (
        Output(El.TIMELAPSE_YEAR_DROPDOWN, "options", dropdown_values.years),
        Output(El.TIMELAPSE_YEAR_DROPDOWN, "value", dropdown_values.year),
        Output(El.TIMELAPSE_MONTH_DROPDOWN, "options", dropdown_values.months),
        Output(El.TIMELAPSE_MONTH_DROPDOWN, "value", dropdown_values.month),
        Output("timelapse-days-folder-row", "children", dropdown_values.days),
        Output("selected-timelapse-day", "value", dropdown_values.day),
    )


@app.callback(
    None,
    [Input({"type": "day-folder", "index": ALL}, "n_clicks")],
    [
        State("selected-timelapse-day", "value"),
        State("refresh-timelapse-captures-container", "value"),
    ],
)
def select_day(n_clicks, current_day, refresh_value):
    day = json.loads(dash.callback_context.triggered[0]["prop_id"].split(".")[0])["index"]
    if day == current_day:
        return Output("refresh-timelapse-captures-container", "value", refresh_value + 1)
    return Output("selected-timelapse-day", "value", day)


@app.callback(
    Output({"type": "day-folder", "index": ALL}, "className"),
    [Input("selected-timelapse-day", "value")],
    [
        State({"type": "day-folder", "index": ALL}, "id"),
    ],
)
def highlight_selected_day(day, ids):
    # TODO: fix the fact that focus flashes on then off then on
    if day is None:
        raise PreventUpdate
    return ["focus" if day == folder_button["index"] else None for folder_button in ids]


@app.callback(
    Output("timelapse-current-page", "value"),
    [Input({"type": "timelapse-pager-button", "action": ALL}, "n_clicks")],
    [State("timelapse-current-page", "value"), State("timelapse-total-pages", "value")],
)
def change_timelapse_table_page(clicks, current_page, last_page):
    trigger = dash.callback_context.triggered[0]["prop_id"].rsplit(".", maxsplit=1)[0]
    if not trigger:
        raise PreventUpdate

    action = json.loads(trigger)["action"]

    if action == "first":
        return 1
    elif action == "previous":
        return max(1, current_page - 1)
    elif action == "next":
        return min(last_page, current_page + 1)
    return last_page


@app.callback(
    None,
    [
        Input("selected-timelapse-day", "value"),
        Input("refresh-timelapse-captures-container", "value"),
        Input("timelapse-ticker", "n_intervals"),
        Input("timelapse-current-page", "value"),
    ],
    [
        State(El.TIMELAPSE_MONTH_DROPDOWN, "value"),
        State(El.TIMELAPSE_YEAR_DROPDOWN, "value"),
        State(El.CAMERA_SELECT, "value"),
    ],
)
def update_displayed_images(day, _, tick, page, month, year, camera_id):
    # there aren't any images to show if any of day, month or year are None
    if year is None:
        raise PreventUpdate

    captures_per_page = 35

    cam = RegisteredCamera.query.get(camera_id)
    date = f"{year}-{month}-{day}"
    images = cam.timelapse_images.filter(TimelapseImage.date == date)

    total_captures_count = images.with_entities(db.func.count(TimelapseImage.image_id)).scalar()

    images = (
        images.order_by(TimelapseImage.timestamp.desc())
        .limit(captures_per_page)
        .offset((page - 1) * captures_per_page)
        .all()
    )

    thumbnail_components = [
        timelapse.components.make_thumbnail_button(
            im.image_filename, im.to_base64(thumbnail=True), im.image_id, "images"
        )
        for im in images
    ]

    if not total_captures_count:
        thumbnail_components = [
            html.I(
                "No captures found. Toggle the Timelapse function "
                '"on" to start capturing timelapse images.'
            )
        ]

    n_pages = (max(0, total_captures_count - 1) // captures_per_page) + 1
    pager = components.make_pager(current_page=page, total_pages=n_pages)

    return [
        Output(El.TIMELAPSE_CAPTURES_CONTAINER, "children", thumbnail_components),
        Output("timelapse-table-pager-div", "children", pager),
        Output("timelapse-table-pager-div", "className", "visible"),
        Output(
            "timelapse-total-captures-count",
            "children",
            f"{total_captures_count} image{'s' if total_captures_count != 1 else ''}",
        ),
    ]


@app.callback(
    None, [Input({"type": "timelapse-thumbnail-button-images", "index": ALL}, "n_clicks")]
)
def toggle_carousel_modal(clicks):
    if not any(clicks):
        raise PreventUpdate

    image_id = json.loads(dash.callback_context.triggered[0]["prop_id"].rsplit(".", maxsplit=1)[0])[
        "index"
    ]

    return (
        Output("timelapse-carousel-modal", "is_open", True),
        Output("timelapse-carousel-image-id", "value", image_id),
    )


@app.callback(
    None,
    [
        Input("timelapse-carousel-prev", "n_clicks"),
        Input("timelapse-carousel-next", "n_clicks"),
        Input("timelapse-carousel-key-press", "n_keydowns"),
    ],
    [
        State("timelapse-carousel-key-press", "keydown"),
        State("timelapse-carousel-image-id", "value"),
    ],
)
def move_timelapse_carousel(
    click_prev,
    click_next,
    key_press,
    key_press_event,
    current_image_id,
):
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
    image = TimelapseImage.get(current_image_id)
    if direction == "prev":
        new_image = image.next()
    else:
        new_image = image.previous()

    # this means we are at one end or the other of the carousel; no more images
    if new_image is None:
        raise PreventUpdate

    return Output("timelapse-carousel-image-id", "value", new_image.image_id)


@app.callback(
    None,
    [Input("timelapse-carousel-image-id", "value")],
    [State(El.CAMERA_SELECT, "value")],
)
def load_modal_content(image_id, camera_id):
    im = TimelapseImage.query.filter(
        TimelapseImage.camera_id == camera_id, TimelapseImage.image_id == image_id
    ).one()

    encoded_image = im.to_base64()
    image_output = Output(
        "timelapse-carousel-modal-content",
        "children",
        html.Img(src=f"data:image/png;base64, {encoded_image}", style={"maxHeight": 1050}),
    )

    left_display = "flex" if im.has_next() else "none"
    right_display = "flex" if im.has_previous() else "none"

    return [
        image_output,
        Output(
            "timelapse-carousel-modal-header",
            "children",
            im.image_filename,
        ),
        Output("timelapse-carousel-prev", "style", {"display": left_display}),
        Output("timelapse-carousel-next", "style", {"display": right_display}),
    ]


@app.callback(
    Output("timelapse-ticker", "disabled"), [Input("timelapse-output-enabled-switch", "value")]
)
def toggle_timelapse_ticker(enabled):
    """Toggle the timelapse Interval ticker so that it only runs when the output is enabled."""
    if enabled:
        return False
    return True

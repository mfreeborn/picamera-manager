import datetime

import dash_bootstrap_components as dbc
from dash import html


def make_create_timelapse_modal():
    today = datetime.date.today()
    return dbc.Modal(
        [
            dbc.ModalHeader("Create Timelapse"),
            dbc.ModalBody(
                dbc.Form(
                    [
                        html.Div(
                            [
                                dbc.Label("Filename:", html_for="create-timelapse-filename-input"),
                                dbc.Row(
                                    dbc.Col(
                                        [
                                            dbc.InputGroup(
                                                [
                                                    dbc.Input(
                                                        id="create-timelapse-filename-input",
                                                        type="text",
                                                        value="",
                                                        debounce=True,
                                                    ),
                                                    dbc.InputGroupAddon(
                                                        ".mp4", addon_type="append"
                                                    ),
                                                ],
                                            ),
                                            # this formfeedback needs special-casing because it
                                            # doens't work properly when used with InputGroup
                                            dbc.FormFeedback(
                                                id="create-timelapse-filename-input-feedback",
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ),
                            ],
                        ),
                        html.Div(
                            [
                                dbc.Label("Start:", html_for="create-timelapse-start-input"),
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            dbc.Input(
                                                id="create-timelapse-start-date-input",
                                                type="date",
                                                value=today,
                                            ),
                                            width=6,
                                        ),
                                        dbc.Col(
                                            dbc.Input(
                                                id="create-timelapse-start-time-input",
                                                type="time",
                                                value="00:00",
                                            ),
                                            width=6,
                                        ),
                                    ]
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                dbc.Label("End:", html_for="create-timelapse-end-input"),
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            dbc.Input(
                                                id="create-timelapse-end-date-input",
                                                type="date",
                                                value=today,
                                            ),
                                            width=6,
                                        ),
                                        dbc.Col(
                                            dbc.Input(
                                                id="create-timelapse-end-time-input",
                                                type="time",
                                                value="23:59",
                                            ),
                                            width=6,
                                        ),
                                    ]
                                ),
                                dbc.FormFeedback(id="create-timelapse-date_range-input-feedback"),
                            ]
                        ),
                        html.Div(
                            [
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                dbc.Label(
                                                    "FPS:", html_for="create-timelapse-fps-input"
                                                ),
                                                dbc.Input(
                                                    id="create-timelapse-fps-input",
                                                    type="number",
                                                    value=30,
                                                    debounce=True,
                                                ),
                                                dbc.FormFeedback(
                                                    id="create-timelapse-fps-input-feedback"
                                                ),
                                            ],
                                            width=6,
                                        ),
                                        dbc.Col(
                                            [
                                                dbc.Label(
                                                    [html.Span("Divisor:"), html.Sup("?")],
                                                    id="create-timelapse-divisor-label",
                                                    html_for="create-timelapse-divisor-input",
                                                ),
                                                dbc.Row(
                                                    dbc.Col(
                                                        dbc.Input(
                                                            id="create-timelapse-divisor-input",
                                                            type="number",
                                                            value=1,
                                                            debounce=True,
                                                        ),
                                                    )
                                                ),
                                                dbc.FormFeedback(
                                                    id="create-timelapse-divisor-input-feedback"
                                                ),
                                                dbc.Tooltip(
                                                    "Make the timelapse video shorter by dividing "
                                                    "down the number of images used in its "
                                                    "creation",
                                                    target="create-timelapse-divisor-label",
                                                ),
                                            ],
                                            width=6,
                                        ),
                                    ]
                                ),
                            ],
                        ),
                        dbc.Row(dbc.Col(html.P(id="timelapse-info"))),
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Button(
                                        "Start",
                                        color="success",
                                        id="create-timelapse-submit",
                                        disabled=True,
                                    ),
                                    width="auto",
                                ),
                                dbc.Col(
                                    dbc.Progress(
                                        "0%",
                                        id="ffmpeg-progress",
                                        value=0,
                                        striped=True,
                                        animated=True,
                                        style={"display": "none"},
                                    )
                                ),
                            ],
                            align="center",
                        ),
                    ]
                ),
            ),
        ],
        id="create-timelapse-modal",
        is_open=False,
    )


def make_delete_timelapse_modal():
    return dbc.Modal(
        [
            dbc.ModalHeader("Delete Timelapse Video"),
            dbc.ModalBody(
                [
                    html.P("Are you sure you wish to delete the following timelapse video?"),
                    html.Ul(
                        html.Li(id="video-title-to-delete"),
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button("Cancel", id="delete-timelapse-video-cancel-modal-button"),
                    dbc.Button(
                        "Confirm", id="delete-timelapse-video-confirm-button", color="danger"
                    ),
                ],
                style={"justifyContent": "space-evenly"},
            ),
        ],
        id="delete-timelapse-video-modal",
        is_open=False,
    )

import dash_bootstrap_components as dbc
from dash import dcc
from dash import html

from .....models import MotionVideo
from . import modals


def make_motion_output_content():
    return [
        dcc.Interval(id="motion-ticker", interval=5000, disabled=True),  # 5 seconds
        make_day_select_row(),
        html.Hr(style={"backgroundColor": "#a0a0a0", "marginTop": 0}),
        make_motion_event_row(),
        modals.make_motion_carousel_modal(),
        html.Div(id="hidden-motion-div", className="hidden"),
    ]


def make_pager(current_page, total_pages):
    """Create a table pager component.

    current_page and total_pages are both 1-indexed.
    """
    back_disabled = False
    forward_disabled = False

    if current_page == 1:
        back_disabled = True

    if current_page == total_pages:
        forward_disabled = True

    return html.Div(
        [
            dbc.Input("motion-current-page", value=current_page, type="hidden"),
            dbc.Input("motion-total-pages", value=total_pages, type="hidden"),
            dbc.Button(
                html.I("first_page", className="material-icons"),
                id={"type": "motion-pager-button", "action": "first"},
                disabled=back_disabled,
                style={
                    "padding": 0,
                    "lineHeight": 0,
                    "backgroundColor": "transparent",
                    "borderWidth": 0,
                    "fontSize": 20,
                },
            ),
            dbc.Button(
                html.I("chevron_left", className="material-icons"),
                id={"type": "motion-pager-button", "action": "previous"},
                disabled=back_disabled,
                style={
                    "padding": 0,
                    "lineHeight": 0,
                    "backgroundColor": "transparent",
                    "borderWidth": 0,
                    "fontSize": 20,
                },
            ),
            html.Span(
                f"{current_page} of {total_pages}",
                style={
                    "verticalAlign": "middle",
                    "paddingLeft": 8,
                    "paddingRight": 8,
                },
            ),
            dbc.Button(
                html.I("chevron_right", className="material-icons"),
                id={"type": "motion-pager-button", "action": "next"},
                disabled=forward_disabled,
                style={
                    "padding": 0,
                    "lineHeight": 0,
                    "backgroundColor": "transparent",
                    "borderWidth": 0,
                    "fontSize": 20,
                },
            ),
            dbc.Button(
                html.I("last_page", className="material-icons"),
                id={"type": "motion-pager-button", "action": "last"},
                disabled=forward_disabled,
                style={
                    "padding": 0,
                    "lineHeight": 0,
                    "backgroundColor": "transparent",
                    "borderWidth": 0,
                    "fontSize": 20,
                },
            ),
        ]
    )


def make_day_select_row():
    return dbc.Row(
        [
            dbc.Col(
                [
                    html.H5("Year", style={"marginBottom": 32}),
                    dcc.Dropdown(
                        id="motion-year-dropdown",
                        style={"color": "black"},
                        clearable=False,
                        searchable=False,
                    ),
                ],
                style={"maxWidth": "6.5rem"},
                width=2,
            ),
            dbc.Col(
                [
                    html.H5("Month", style={"marginBottom": 32}),
                    dcc.Dropdown(
                        id="motion-month-dropdown",
                        style={"color": "black"},
                        clearable=False,
                        searchable=False,
                    ),
                ],
                style={"maxWidth": "9rem"},
                width=2,
            ),
            dbc.Col(
                html.Hr(
                    style={
                        "backgroundColor": "#a0a0a0",
                        "width": 1,
                        "height": "90%",
                        "margin": 0,
                    }
                ),
                width="auto",
            ),
            dbc.Col(
                id="motion-days-folder-row",
                width="auto",
                style={"maxWidth": "85%", "direction": "rtl"},
            ),
            dbc.Input(id="selected-motion-day", type="hidden"),
        ],
        style={"paddingLeft": 5, "minHeight": 125, "paddingTop": 58},
    )


def make_motion_event_row():
    return dbc.Row(
        [
            dbc.Col(
                [
                    html.Div(
                        dbc.Row(
                            [
                                dbc.Col(html.I(id="motion-total-event-count"), width="auto"),
                                dbc.Col(
                                    make_pager(1, 1),
                                    id="motion-table-pager-div",
                                    width="auto",
                                ),
                            ],
                            justify="end",
                            style={
                                "paddingBottom": 16,
                                "paddingRight": 150,
                            },
                        )
                    ),
                    html.Div(
                        id="motion-event-container",
                        className="thumbnail-container",
                    ),
                ]
            ),
            dbc.Input(id="refresh-motion-event-container", type="hidden", value=0),
        ],
    )


def make_thumbnail_button(video: MotionVideo):
    return dbc.Button(
        [
            html.Img(
                src=f"data:image/png;base64, {video.title_image_to_base64(thumbnail=True)}",
                style={
                    "marginBottom": 4,
                    "borderTopLeftRadius": "0.25rem",
                    "borderTopRightRadius": "0.25rem",
                },
            ),
            html.P(
                video.video_filename,
                style={"maxWidth": "fit-content", "marginBottom": 4},
            ),
        ],
        id={"type": "motion-thumbnail-button", "index": video.video_id},
        style={"padding": 0, "border": 0, "height": "fit-content", "textAlign": "-webkit-center"},
        className="thumbnail-button",
    )


def FolderRow(label, folders):
    return [
        dbc.Row(dbc.Col(html.H5(label))),
        dbc.Row(
            folders,
            style={
                "overflowX": "auto",
                "flexWrap": "unset",
                "marginLeft": -15,
                "marginRight": 0,
                "paddingBottom": 16,
                "paddingTop": 3,
            },
        ),
    ]


def make_folder(label):
    return dbc.Col(
        dbc.Button(
            [
                dbc.Row(
                    dbc.Col(
                        html.I(
                            "folder",
                            className="material-icons",
                            style={"fontSize": 60},
                        )
                    )
                ),
                dbc.Row(dbc.Col(html.P(label, className="no-margin", style={"marginTop": -12}))),
            ],
            id={"type": "motion-day-folder", "index": label},
            style={"paddingTop": 0, "paddingBottom": 0},
        ),
        style={"textAlign": "center"},
        width="auto",
    )

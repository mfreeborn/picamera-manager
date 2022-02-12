import dash_bootstrap_components as dbc
from dash import dcc
from dash import html

from .....enums import Element as El


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
            dbc.Input("timelapse-current-page", value=current_page, type="hidden"),
            dbc.Input("timelapse-total-pages", value=total_pages, type="hidden"),
            dbc.Button(
                html.I("first_page", className="material-icons"),
                id={"type": "timelapse-pager-button", "action": "first"},
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
                id={"type": "timelapse-pager-button", "action": "previous"},
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
                id={"type": "timelapse-pager-button", "action": "next"},
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
                id={"type": "timelapse-pager-button", "action": "last"},
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
                        id=El.TIMELAPSE_YEAR_DROPDOWN,
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
                        id=El.TIMELAPSE_MONTH_DROPDOWN,
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
                id="timelapse-days-folder-row",
                width="auto",
                style={"maxWidth": "85%", "direction": "rtl"},
            ),
            dbc.Input(id="selected-timelapse-day", type="hidden"),
        ],
        style={"paddingLeft": 5, "minHeight": 125},
    )


def make_timelapse_captures_row():
    return dbc.Row(
        [
            dbc.Col(
                [
                    html.Div(
                        dbc.Row(
                            [
                                dbc.Col(html.I(id="timelapse-total-captures-count"), width="auto"),
                                dbc.Col(
                                    make_pager(1, 1),
                                    id="timelapse-table-pager-div",
                                    width="auto",
                                    className="hidden",
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
                        id=El.TIMELAPSE_CAPTURES_CONTAINER,
                        className="thumbnail-container",
                    ),
                ]
            ),
            dbc.Input(id="refresh-timelapse-captures-container", type="hidden", value=0),
        ]
    )

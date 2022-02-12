import dash_bootstrap_components as dbc
from dash import html


def make_timelapse_output_content_tabs():
    return dbc.Tabs(
        [
            dbc.Tab(
                label="Images",
                tab_id="timelapse-image-tab",
                label_style={"color": "white"},
                active_label_style={"color": "black"},
            ),
            dbc.Tab(
                label="Videos",
                tab_id="timelapse-video-tab",
                label_style={"color": "white"},
                active_label_style={"color": "black"},
            ),
        ],
        id="timelapse-content-tabs",
        active_tab="timelapse-image-tab",
    )


def make_thumbnail_button(filename: str, image_data: str, media_id: int, tab: str) -> dbc.Button:
    return dbc.Button(
        [
            html.Img(
                src=f"data:image/png;base64, {image_data}",
                style={
                    "marginBottom": 4,
                    "borderTopLeftRadius": "0.25rem",
                    "borderTopRightRadius": "0.25rem",
                },
            ),
            html.P(
                filename,
                style={"maxWidth": "fit-content", "marginBottom": 4},
            ),
        ],
        id={"type": f"timelapse-thumbnail-button-{tab}", "index": media_id},
        style={"padding": 0, "border": 0, "height": "fit-content", "textAlign": "-webkit-center"},
        className="thumbnail-button",
    )

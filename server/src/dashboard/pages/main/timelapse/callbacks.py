from dash.dependencies import Input, Output

from ....app import app
from . import captures_view, videos_view


@app.callback(
    Output("timelapse-tab-content", "children"), [Input("timelapse-content-tabs", "active_tab")]
)
def select_tab(active_tab):
    if active_tab == "timelapse-image-tab":
        return captures_view.make_timelapse_image_output_content()
    elif active_tab == "timelapse-video-tab":
        return videos_view.make_timelapse_video_output_content()

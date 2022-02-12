from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from ......auth.youtube_service import YouTubeService
from ......models import RegisteredCamera
from .....app import app
from .....enums import Element as El
from . import components


@app.callback(None, [Input(El.YOUTUBE_OAUTH_BUTTON, "n_clicks")])
def trigger_youtube_auth(clicks):
    if clicks is None:
        raise PreventUpdate

    return [
        Output("youtube-oauth-input", "disabled", False),
        Output("youtube-oauth-code-button", "disabled", False),
    ]


@app.callback(
    None, [Input("youtube-oauth-code-button", "n_clicks")], [State("youtube-oauth-input", "value")]
)
def complete_auth_flow(n_clicks, code):
    # we can use the YouTubeService class directly because authentication is camera agnostic
    yt = YouTubeService()
    yt.complete_auth_flow(code=code)


@app.callback(
    Output("yt-loading-div", "children"),
    [Input("yt-loading-div", "id")],
    [State(El.CAMERA_SELECT, "value")],
)
def load_youtube_output_content(_, camera_id):
    cam = RegisteredCamera.get(camera_id)
    return components.make_youtube_output_content_proper(cam)

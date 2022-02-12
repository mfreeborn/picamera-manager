from ......auth.youtube_service import YouTubeHandler
from . import callbacks  # noqa: F401
from . import components


def make_youtube_output_content(cam):
    """Produce the content of the YouTube output view.

    For proper use, we need to be OAuth2 authenticated with the YouTube API.
    """
    print("making youtube output content")
    yt_handler = YouTubeHandler(cam)

    # if the user has never authenticated, we need to first take them through the OAuth2 workflow
    if not yt_handler.flow_completed:
        auth_flow_url = yt_handler.auth_flow_url()
        return components.make_auth_flow_content(auth_flow_url)
    # otherwise they are ready to view the livestream
    return components.make_youtube_content(cam)

from . import callbacks  # noqa: F401
from .local_network import make_network_output_content
from .youtube import make_youtube_output_content


def make_livestream_output_content(cam):
    """Return the top-level component for the 'Livestream' output.

    Depending on whether the user has enabled YouTube mode, this will either be an HTML
    video component playing a stream across the local network, or it will be the YouTube
    output.
    """
    config = cam.get_config()
    # if config["outputs"]["livestream"]["youtube_mode"]:
    # return make_youtube_output_content(cam)
    return make_network_output_content(cam)

from dash import html

from . import callbacks  # noqa
from . import components


def make_motion_output_content(cam):
    """Return the top-level component for the 'Motion' output."""
    return html.Div(
        components.make_motion_output_content(),
    )

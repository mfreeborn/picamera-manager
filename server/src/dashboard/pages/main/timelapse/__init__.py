from dash import html

from . import callbacks  # noqa
from . import components


def make_timelapse_output_content(cam):
    """Return the top-level component for the 'Timelapse' output."""
    return html.Div(
        [
            components.make_timelapse_output_content_tabs(),
            html.Div(id="timelapse-tab-content", style={"paddingTop": 16}),
        ]
    )

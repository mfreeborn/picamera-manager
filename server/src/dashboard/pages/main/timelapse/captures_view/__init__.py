from dash import dcc
from dash import html

from . import callbacks  # noqa
from . import components
from . import modals


def make_timelapse_image_output_content():
    """Return the top-level component for the 'Images' tab for the 'Timelapse' output."""
    print("making timelapse captures view content")
    return [
        # this timer lets us poll for new captures. Consider disabling it whilst not viewing the
        # current day's captures and/or the timelapse output is disabled
        dcc.Interval(id="timelapse-ticker", interval=5000, disabled=True),  # 5 seconds
        components.make_day_select_row(),
        html.Hr(style={"backgroundColor": "#a0a0a0", "marginTop": 0}),
        components.make_timelapse_captures_row(),
        modals.make_timelapse_carousel_modal(),
        html.Div(id="hidden-tl-div", className="hidden"),
    ]

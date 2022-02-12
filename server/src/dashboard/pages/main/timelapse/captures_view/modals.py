import dash_bootstrap_components as dbc
import dash_extensions as dext
from dash import html


def make_timelapse_carousel_modal():
    return dbc.Modal(
        [
            dext.Keyboard(id="timelapse-carousel-key-press"),
            dbc.Input(id="timelapse-carousel-image-id", type="hidden"),
            dbc.ModalHeader(
                id="timelapse-carousel-modal-header",
            ),
            dbc.ModalBody(
                html.Div(
                    [
                        html.Div(
                            html.Div(
                                id="timelapse-carousel-modal-content",
                                className="carousel-item active",
                            ),
                            className="carousel-inner",
                        ),
                        html.A(
                            html.Span(
                                className="carousel-control-prev-icon",
                                **{"aria-hidden": "true"},
                            ),
                            id="timelapse-carousel-prev",
                            className="carousel-control-prev",
                            role="button",
                        ),
                        html.A(
                            html.Span(
                                className="carousel-control-next-icon",
                                **{"aria-hidden": "true"},
                            ),
                            id="timelapse-carousel-next",
                            className="carousel-control-next",
                            role="button",
                        ),
                    ],
                    id="timelapse-carousel",
                    className="carousel",
                ),
            ),
        ],
        id="timelapse-carousel-modal",
        size="xl",
        centered=True,
        style={"maxWidth": "fit-content"},
    )

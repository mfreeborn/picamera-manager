import dash_bootstrap_components as dbc
import dash_extensions as dext
from dash import html


def make_motion_carousel_modal():
    return dbc.Modal(
        [
            dext.Keyboard(id="motion-carousel-key-press"),
            dbc.Input(id="selected-motion-event-input", type="hidden"),
            dbc.ModalHeader(
                id="motion-carousel-modal-header",
            ),
            dbc.ModalBody(
                html.Div(
                    [
                        html.Div(
                            html.Div(
                                id="motion-carousel-modal-content",
                                className="carousel-item active",
                            ),
                            className="carousel-inner",
                        ),
                        html.A(
                            html.Span(
                                className="carousel-control-prev-icon",
                                **{"aria-hidden": "true"},
                            ),
                            id="motion-carousel-prev",
                            className="carousel-control-prev",
                            role="button",
                            style={"height": "90%"},
                        ),
                        html.A(
                            html.Span(
                                className="carousel-control-next-icon",
                                **{"aria-hidden": "true"},
                            ),
                            id="motion-carousel-next",
                            className="carousel-control-next",
                            role="button",
                            style={"height": "90%"},
                        ),
                    ],
                    id="motion-carousel",
                    className="carousel",
                ),
            ),
        ],
        id="motion-carousel-modal",
        size="xl",
        centered=True,
        style={"maxWidth": "fit-content"},
    )

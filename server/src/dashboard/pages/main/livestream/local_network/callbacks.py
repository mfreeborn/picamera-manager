from dash.dependencies import ClientsideFunction, Input, Output, State

from .....app import app
from .....enums import Element as El


app.clientside_callback(
    ClientsideFunction(namespace="clientside", function_name="mse_client"),
    Output("out", "children"),
    [Input(El.INIT_MSE_CLIENT, "value")],
    [
        State(El.CAMERA_SELECT, "value"),
        State(El.SERVER_IP_ADDRESS, "value"),
        State(El.SERVER_PORT, "value"),
    ],
    prevent_initial_call=False,
)

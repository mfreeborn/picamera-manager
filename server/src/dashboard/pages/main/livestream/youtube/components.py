import time

import dash_bootstrap_components as dbc
from dash import html
import requests

from ......auth.youtube_service import YouTubeHandler
from .....enums import Element as El


def make_auth_flow_content(auth_flow_url):
    return html.Div(
        [
            html.P("Allow YouTube streaming by completing the following required steps:"),
            html.Ol(
                [
                    html.Li(
                        html.A(
                            dbc.Button("Allow YouTube Access"),
                            id=El.YOUTUBE_OAUTH_BUTTON,
                            href=auth_flow_url,
                            target="_blank",
                            style={
                                "marginLeft": "4rem",
                                "marginTop": "1rem",
                                "marginBottom": "1rem",
                            },
                        )
                    ),
                    html.Li(
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Input(
                                        id="youtube-oauth-input",
                                        type="text",
                                        placeholder=("Paste the code obtained from the first step"),
                                        disabled=True,
                                        style={
                                            "marginLeft": "4rem",
                                            "marginTop": "1rem",
                                            "marginBottom": "1rem",
                                            "width": "22rem",
                                        },
                                    ),
                                    width="auto",
                                ),
                                dbc.Col(
                                    dbc.Button(
                                        "Submit",
                                        id="youtube-oauth-code-button",
                                        disabled=True,
                                        style={
                                            "marginTop": "1rem",
                                            "marginBottom": "1rem",
                                        },
                                    )
                                ),
                            ]
                        )
                    ),
                ]
            ),
        ]
    )


def make_youtube_content(cam):
    return html.Div("Loading output...", id="yt-loading-div")


def make_youtube_output_content_proper(cam):
    yt_handler = YouTubeHandler(cam)

    # we're both authenticated and enabled - is this the first time we're running this output
    # for this camera? If so, we need to create a liveStream resource
    if cam.youtube_stream_id is None:
        print(f"No YouTube livestream resource associated with {cam}. Creating one now...")
        youtube_stream = yt_handler.create_video_stream()
        # here we need to inform the camera of the ingestion_url. The streams are resuable (whereas
        # the broadcasts are single use and can get repeatedly recreated), so we should only ever
        # need to let the camera know the ingestion URL on this one occassion. NOTE: unless we want
        # to change the parameters e.g. framerate, resolution, title
        ingestion_info = youtube_stream["cdn"]["ingestionInfo"]
        ingestion_url = f"{ingestion_info['ingestionAddress']}/{ingestion_info['streamName']}"
        # updating the config will force the camera to restart its outputs, so it will start
        # streaming video to YouTube
        requests.post(f"{cam.client_url}/config", json={"livestream_ingestion_url": ingestion_url})
        print(f"YouTube livestream resource created and saved successfully for {cam}.")

    # so now we are authenticated, enabled and have a stream.
    # Is there a current broadcast? If so, we can simply get the id and load the embedded video
    broadcast = yt_handler.get_broadcast()
    if broadcast is None:
        print(f"No YouTube broadcase resource associated with {cam}. Creating one now...")
        # this is the first run of the YouTube output, so we need to create a fresh new broadcast
        # and bind it with the stream
        broadcast = yt_handler.create_broadcast()
        yt_handler.bind()
        print(f"YouTube broadcast resource created and saved successfully for {cam}")

        # broadcast starts "ready", then progresses to "liveStarting" before finally
        # becoming "live" when the camera actually kicks in with its stream. Wait for
        # the transition to "live" before loading the iframe
        tries = 0
        while True:
            time.sleep(2)
            broadcast = yt_handler.get_broadcast(parts="status")
            status = broadcast["status"]["lifeCycleStatus"]
            if status in {"ready", "liveStarting"}:
                if tries > 4:
                    print(
                        (
                            "Warning - timed out whilst waiting for broadcast to "
                            "become live. Current status:"
                        ),
                        status,
                    )
                    break
                # wait...
                tries = +1
                continue

            if status == "live":
                break
            else:
                print("Warning - the broadcast seems to be in a non-functioning state:", status)
                break

    cam_config = cam.get_config()
    width, height = cam_config["global"]["viewport_size"].split("x")
    return html.Div(
        html.Iframe(
            src=(
                f"https://www.youtube.com/embed/{cam.youtube_broadcast_id}"
                f"?autoplay=1&mute=1&controls=1"
            ),
            width=width,
            height=height,
            style={"borderStyle": "none"},
        ),
        style={"textAlign": "center"},
    )

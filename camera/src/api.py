import logging

from fastapi import FastAPI, Request
from pydantic import BaseModel

from .camera import Camera


class Output(BaseModel):
    output_type: str


class RegisterPayload(BaseModel):
    port: str
    camera_name: str


class RestartYouTubeStreamPayload(BaseModel):
    # the number of seconds of grace to give the YouTube output before
    # forcing it to restart
    grace_period: int


app = FastAPI()

# instantiate the camera instance. The saved configuration should be transparently
# loaded at this point
cam = Camera()
# now, cam is fully configured, but it won't begin doing anything until we call .start()


@app.on_event("startup")
def startup():
    # start the outputs running if we are registered with a server
    if cam.server_address:
        cam.start()


@app.on_event("shutdown")
def shutdown():
    # we need to ensure we free up the camera when shutting down
    logging.info("Closing camera")
    if cam.running:
        cam.stop()
    cam.close()


@app.get("/ping")
def ping():
    cam.configure({"camera": {"vflip": not cam.vflip}})
    return "pong"


@app.post("/register")
async def register(payload: RegisterPayload, request: Request):
    """Called when this camera receives a request to be paired with the server."""
    if cam.server_address:
        logging.warning(
            "This camera is already registered with a server located at %s - previous "
            "configuration will now be overwritten",
            cam.server_address,
        )
    if cam.running:
        cam.stop()

    # double check that the config file is initially set to its default values
    cam.config.reset()

    # compile the basic parameters to save for the new camera
    server_ip = request.client.host
    server_port = payload.port
    server_address = {"ip": server_ip, "port": server_port}

    new_cam_config = {
        "server_address": server_address,
        "camera": {"name": payload.camera_name},
        # TODO: rather than hard coding a port, we could use an OS-designated port when
        # initialising the network output socket and set that as a config parameter. The
        # server could then just ask for the config and the port would be there
        "outputs": {"network": {"enabled": True}},
    }

    cam.configure(new_cam_config)

    logging.info("Camera successfully registered with the server located at %s", server_address)
    cam.start()

    return {"status": "success", "message": f"Registered camera at {request.headers['host']}"}


@app.post("/unregister")
async def unregister(request: Request):
    # reset the config file to defaults so it's nice and fresh when it is re-registered
    cam.stop()
    cam.config.clear()
    logging.info("Camera successfully unregistered")
    return {"status": "success", "message": f"Unregistered camera at {request.headers['host']}"}


@app.get("/config")
async def get_config():
    return cam.config.to_dict()


@app.post("/config")
async def set_config(new_config: dict):
    print(new_config)
    cam.config.update(new_config)


@app.post("/enable-output")
async def enable_output(output: Output, request: Request):
    out = output.output_type
    print(out)
    settings_to_update = {f"{out}_enabled": True}

    extra = await request.json()
    if "youtube_ingestion_url" in extra:
        settings_to_update["youtube_ingestion_url"] = extra["youtube_ingestion_url"]

    cam.config.update(settings_to_update)

    return f"{output.output_type} output enabled"


@app.post("/disable-output")
async def disable_output(output: Output):
    try:
        out = output.output_type
        cam.config.update({f"{out}_enabled": False})
    except Exception:  # noqa
        print(f"error whilst disabling {output.output_type} output")
        import traceback

        traceback.print_exc()
        return f"error whilst disabling {output.output_type} output"
    return f"{output.output_type} output disabled"


# @app.post("/restart-youtube-stream")
# async def restart_youtube_stream(payload: RestartYouTubeStreamPayload):
#     output = cam.outputs["livestream"]

#     if not isinstance(output, YouTubeOutput):
#         return "YouTube stream not restarted. Not currently attached."

#     now = time.time()
#     grace_period_cutoff = output.time_started + payload.grace_period
#     if now > grace_period_cutoff:
#         print("Grace period exceeded; restarting YouTube stream.")
#         cam.remove_output("livestream")
#         cam.add_output("livestream")
#         return "Grace period exceeded - YouTube stream restarted."
#     time_remaining = grace_period_cutoff - now
#     return f"YouTube stream not restarted. {time_remaining:.1f}s remaining in the grace period."

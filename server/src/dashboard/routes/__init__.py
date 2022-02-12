import asyncio
import base64
import datetime
import io

import ffmpeg
from PIL import Image
from flask import request, send_from_directory

from ... import tasks
from ...models import RegisteredCamera, TimelapseVideo, MotionVideo
from ..app import app, server, sock


@server.route("/motion-videos/<int:video_id>/video")
def send_motion_video(video_id):
    video = MotionVideo.get(video_id)
    return send_from_directory(
        directory=video.video_dir,
        file_name=video.video_filename,
        mimetype="video/mp4",
        as_attachment=request.args.get("as_attachment", False),
    )


@server.route("/motion-videos/<int:video_id>/poster")
def send_motion_trigger_image(video_id):
    video = MotionVideo.get(video_id)
    return send_from_directory(
        directory=video.title_image_dir,
        file_name=video.title_image_filename,
        mimetype="image/jpg",
        as_attachment=request.args.get("as_attachment", False),
    )


@server.route("/process-new-motion-event", methods=["POST"])
def process_new_motion_event():
    """Receive and save a new motion video.

    3 files are provided in the request.files attribute:
        {
            "before_video": werkzeug.FileStorage,
            "after_video": werkzeug.FileStorage,
            "trigger_image": werkzeug.FileStorage,
        }

    Metadata is provided in the request.form attribute:
        {
            "timestamp": iso8601 str,
            "framerate": int,
        }
    """
    files = request.files
    # werkzeug.FileStorage is not pickleable, so we need to get the actual file streams
    files = {k: v.stream for k, v in files.items()}
    metadata = request.form

    # type wrangling and additional metadata
    metadata["timestamp"] = datetime.datetime.fromisoformat(metadata["timestamp"])
    metadata["camera_ip_address"] = request.remote_addr
    metadata["framerate"] = int(metadata["framerate"])

    tasks.process_motion_event(files, metadata)
    print("motion video request finished")
    return "New motion event saved"


@server.route("/timelapse-video")
def stream_timelapse_video():
    args = request.args
    video = TimelapseVideo.query.filter(
        TimelapseVideo.camera_id == args["camera_id"], TimelapseVideo.video_id == args["video_id"]
    ).one()

    return send_from_directory(
        directory=video.video_dir,
        file_name=video.video_filename,
        mimetype="video/mp4",
        as_attachment=request.args.get("as_attachment", False),
    )


@server.route("/save-timelapse-capture", methods=["POST"])
def save_timelapse_capture():
    """Receive and save a base64 encoded timelapse capture.

    The payload is expected to be in the form:

    {
        "capture": base64 str,
        "capture_time": iso 8601 str
    }
    """
    data = request.form
    # wrangle the types
    data["capture"] = Image.open(io.BytesIO(base64.b64decode(data["capture"])))
    data["capture_time"] = datetime.datetime.fromisoformat(data["capture_time"])
    data["camera_ip_address"] = request.remote_addr
    tasks.save_timelapse_capture(data)

    return "Capture saved"


@sock.route("/ws")
def ws(ws):
    import time

    # the first part of the "protocol" is that the client sends us the id of the camera
    camera_id = ws.receive()
    camera = RegisteredCamera.get(camera_id)
    print(camera)

    # here we build the ffmpeg command which will convert an h264 video stream to fragmented MP4.
    # This is then streamed down a websocket for a (javascript) client to read from and play the
    # live video feed.
    global_args = ["-hide_banner", "-loglevel", "panic"]

    video = ffmpeg.input(camera.video_stream_address, hide_banner=None, thread_queue_size=512)
    audio = ffmpeg.input("anullsrc", format="lavfi")
    stream = ffmpeg.output(
        video,
        audio,
        "pipe:",
        audio_bitrate=128_000,
        format="mp4",
        movflags="frag_keyframe+default_base_moof+empty_moov",
        vcodec="copy",
    )
    # try:
    proc = stream.run_async(pipe_stdout=True)
    print(proc.args)
    # except Exception as e:
    # app.logger.exception("Error", exc_info=e)

    chunk_size = 65535
    while True:
        try:
            in_bytes = proc.stdout.read(chunk_size)
            if not in_bytes:
                break
            ws.send(in_bytes)
        except Exception as e:
            app.logger.exception("Error", exc_info=e)
            break
    proc.terminate()

    # # initialise and create a handle for the ffmpeg process. We will be reading
    # # from its stdout, so we need to put a PIPE on it
    # proc = await asyncio.create_subprocess_exec(
    #     *cmd,
    #     stdout=subprocess.PIPE,
    # )

    # try:
    #     chunk_size = 65536  # default max websocket frame size
    #     while not proc.stdout.at_eof():
    #         await websocket.send(await proc.stdout.read(chunk_size))

    # except asyncio.CancelledError:
    #     # this happens when we switch away from the livestream output. We can just
    #     # ignore it and carry on to kill the ffmpeg process
    #     pass

    # finally:
    #     try:
    #         # we just need to make sure we try and kill the ffmpeg process
    #         proc.kill()
    #     except:  # noqa
    #         pass

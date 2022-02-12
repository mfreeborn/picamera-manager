import io
import os
import smtplib
import tempfile
import time
from email.message import EmailMessage
from pathlib import Path

import ffmpeg
from PIL import Image

from ..models import MotionVideo, RegisteredCamera, TimelapseImage
from ..utils import run_in_background_process, run_in_background_thread


class MotionEvent:
    def __init__(
        self,
        before_video: io.BytesIO,
        after_video: io.BytesIO,
        framerate: int,
    ):
        self.before_video = before_video
        self.after_video = after_video
        self.framerate = framerate
        self.motion_video = io.BytesIO()

    def concat_video_parts(self):
        with tempfile.TemporaryDirectory() as tempdir:
            before_path = Path(tempdir) / "before_video.h264"
            after_path = Path(tempdir) / "after_video.h264"

            # save the video files to the temporary directory
            with open(before_path, "wb") as fh:
                fh.write(self.before_video.getbuffer())
            with open(after_path, "wb") as fh:
                fh.write(self.after_video.getbuffer())

            with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", dir=tempdir) as fh:
                # create a file containing a list of video filepaths, as required by ffmpeg
                fh.write("\n".join(f"file '{filepath}'" for filepath in [before_path, after_path]))
                fh.seek(0)

                # concatenate the video streams to a single MP4 file
                input_stream = ffmpeg.input(fh.name, f="concat", safe=0)
                cmd = ffmpeg.output(
                    input_stream,
                    "pipe:",
                    # TODO: I'm not sure that the framerate parameter is being honored by ffmpeg
                    r=self.framerate,
                    c="copy",
                    movflags="frag_keyframe+default_base_moof+empty_moov",
                    f="mp4",
                )
                t0 = time.perf_counter()

                proc = cmd.run_async(cmd=["ffmpeg", "-hide_banner"], pipe_stdout=True)

                self.motion_video.write(proc.stdout.read())
                if not self.motion_video.tell():
                    # if tell() is 0 (i.e. nothing has been written to the stream), then there
                    # was an error
                    raise Exception("Error concatenating video streams")
                self.motion_video.seek(0)
                t1 = time.perf_counter()

                print(f"ffmpeg finished in {(t1 - t0) * 1000:.1f}ms")


def _process_motion_event(files, metadata):
    before, after, trigger_image = (
        files["before_video"],
        files["after_video"],
        files["trigger_image"],
    )

    # produce and save the the video and associated images
    motion_event = MotionEvent(before, after, metadata["framerate"])
    motion_event.concat_video_parts()

    cam = RegisteredCamera.from_ip_address(metadata["camera_ip_address"])
    cam_config = cam.get_config()["outputs"]["motion"]

    video = MotionVideo(
        camera_id=cam.camera_id,
        timestamp=metadata["timestamp"],
        video=motion_event.motion_video,
        title_image=Image.open(trigger_image),
    )

    # then do the notification
    if cam_config["notifications_enabled"]:
        email_address = os.getenv("EMAIL_ADDRESS")
        email_password = os.getenv("EMAIL_PASSWORD")
        server = os.getenv("SMTP_SERVER")
        port = os.getenv("SMTP_PORT")
        if not all([email_address, email_password, server, port]):
            print(
                "Error - the following environment variables all need to be set in order to "
                "support email notifications: EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT"
            )
            return

        message = EmailMessage()
        message["From"] = email_address
        message["To"] = cam_config["notifications_email_address"]
        message["Subject"] = "Motion Detected"

        body = "Motion detected"
        message.set_content(body)

        message.add_attachment(
            video.title_image_path.read_bytes(),
            maintype="image",
            subtype="jpeg",
            filename="trigger_image.jpg",
        )

        message.add_attachment(
            video.video_path.read_bytes(),
            maintype="video",
            subtype="mp4",
            filename="motion_video.mp4",
        )

        with smtplib.SMTP_SSL(server, port=port) as server:
            server.login(email_address, email_password)
            server.send_message(message)
            print("Email sent!")
        print("task complete")


# multiprocessing tasks must be at the top level of the module, so we can't use
# the @ decorator syntax like we do with the background threaded tasks
process_motion_event = run_in_background_process(_process_motion_event)


@run_in_background_thread
def save_timelapse_capture(data):
    # get the camera which owns the image
    cam = RegisteredCamera.from_ip_address(data["camera_ip_address"])

    # create an instance for storage in the db
    TimelapseImage(camera_id=cam.camera_id, timestamp=data["capture_time"], image=data["capture"])

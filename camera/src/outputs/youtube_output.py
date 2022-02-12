from __future__ import annotations

import subprocess
import time
import threading
import typing as t

import ffmpeg

from .bases import BaseOutput, VideoOutputHandler
from .. import enums

if t.TYPE_CHECKING:
    from ..camera import Camera
    from ..types import Frame


class _StreamingThread(threading.Thread):
    def __init__(self, framerate: int, ingestion_url: str):
        super().__init__()
        self.closed: bool = False
        self.daemon: bool = True

        self.global_args = ["-hide_banner", "-re"]

        video_in = ffmpeg.input(
            "pipe:0",
            framerate=framerate,
            thread_queue_size=512,
        )
        audio_in = ffmpeg.input("anullsrc", f="lavfi")

        self.cmd = ffmpeg.output(
            video_in,
            audio_in,
            ingestion_url,
            vcodec="copy",
            f="flv",
            audio_bitrate="128k",  # setting it to <128k causes an annoying warning from YT
        )

        self.proc: subprocess.Popen = self.cmd.run_async(
            pipe_stdin=True, cmd=["ffmpeg"] + self.global_args, overwrite_output=True
        )
        self.start()

    def run(self):
        print(" ".join(self.proc.args))
        while not self.closed:
            time.sleep(1)

    def send_frame(self, frame_data: bytes) -> None:
        self.proc.stdin.write(frame_data)

    def close(self) -> None:
        self.closed = True
        self.proc.kill()


class YouTubeOutput(BaseOutput):
    def __init__(self, camera: Camera):
        super().__init__(output_name="youtube", camera=camera)
        self.video_handler = VideoOutputHandler(
            video_output=camera.video_output,
            frame_callback=self.process_frame,
            thread_name="YoutubeOutputThread",
        )

        ingestion_url = self.config.ingestion_url
        if not ingestion_url:
            raise Exception("YouTube not properly initialised yet; need an ingestion url!")

        self.streaming_thread = _StreamingThread(
            framerate=camera.framerate, ingestion_url=ingestion_url
        )

    def process_frame(self, frame: Frame) -> None:
        self.streaming_thread.send_frame(frame.data)

    def close(self) -> None:
        super().close()
        self.join()

        self.streaming_thread.close()
        self.streaming_thread.join()

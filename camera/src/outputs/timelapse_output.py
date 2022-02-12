from __future__ import annotations

import base64
import datetime
import io
import logging
import threading
from typing import TYPE_CHECKING, Optional

import requests

from .bases import BaseOutput, VideoOutputHandler
from ..types import FrameBuffer, VideoFrame

if TYPE_CHECKING:
    from ..camera import Camera


class SenderThread(threading.Thread):
    def __init__(self, timelapse_output: TimelapseOutput, server_addr: str):
        super().__init__(daemon=True)
        self.closed = False
        self.timelapse_output = timelapse_output
        self.timelapse_event = timelapse_output.timelapse_event
        self.server_addr = server_addr
        self.start()

    def run(self):
        while not self.closed:
            if self.timelapse_event.wait(1):
                payload = {
                    "timelapse_image_data": {
                        "frame_group": self.timelapse_output.last_frame_group.raw_bytes(),
                        "timelapse_frame_index": len(self.timelapse_output.last_frame_group) - 2,
                    },
                    "timestamp": self.timelapse_output.last_frame_group[-1].timestamp,
                }

                # requests.post(f"{self.server_addr}/api/timelapse-image", json=payload)
                self.timelapse_event.clear()
            else:
                # this branch will run very second that there is no timelapse image to send, which
                # means we can end this thread externally as it is not in an infinite loop
                continue

    def close(self):
        self.closed = True
        self.join()


class TimelapseOutput(BaseOutput):
    """POST a new timelapse image to the server at a predefined interval."""

    def __init__(self, camera: Camera):
        logging.info("Timelapse output initialising")
        super().__init__(output_name="timelapse", camera=camera)
        self.video_handler = VideoOutputHandler(
            video_output=camera.video_output,
            frame_callback=self.process_frame,
            thread_name="TimelapseOutputThread",
        )
        # maintain a buffer of the most recent frames. It needs to be large enough
        # to include a minimum of one SPS header
        self.buffer = FrameBuffer(maxlen=30)

        # the number of seconds between each timelapse image
        self.interval = self.config.capture_interval

        # this is used to alert the image sending child thread that a new timelapse
        # image needs to be processed and sent
        self.timelapse_event = threading.Event()

        # keep track of the most recent timelapse data
        self.last_frame_group: Optional[FrameBuffer] = None

        # handle the job of processing and sending the latest timelapse data in
        # a different thread
        self.sender_thread = SenderThread(self, camera.server_address)

    def process_frame(self, frame: VideoFrame) -> None:
        self.buffer.append(frame)

        # start with just filling up the buffer so that we definitely have
        # some valid frames to work with. We can also return early if this is
        # just a header frame (we'll wait for the next data frame) or if we
        # are already busy sending a timelapse image
        if not self.buffer.full or frame.sps_header or self.timelapse_event.is_set():
            return

        # if it is time to create a new timelapse image, notify the image sender thread
        if (self.last_timestamp is None) or frame.timestamp >= (
            self.last_frame_group[-1].timestamp + self.interval
        ):
            frame_group = self.buffer.final_group()
            self.last_frame_group = frame_group
            self.timelapse_event.set()

    def close(self):
        logging.info("Timelapse output closing")
        # end the VideoOutputHandler thread
        self.video_handler.close()

        # end the image sender thread
        self.sender_thread.close()
        logging.info("Timelapse output closed")

from __future__ import annotations

import abc
import logging
import time
from threading import Event, Thread
import typing as t

if t.TYPE_CHECKING:
    from .. import types
    from ..camera import MotionOutput, VideoOutput, Camera


class BaseOutput(abc.ABC):
    def __init__(self, output_name: str, camera: Camera):
        self.config = camera.config.output(output_name).copy()


class VideoOutputHandler:
    """Interface defining outputs which process video frames produced by the camera.

    Any subclass will implement a `process_frame` method, which is called with a
    `Frame` object whenever the camera has produced a new frame. Each output is run
    in a background thread.
    """

    def __init__(
        self,
        video_output: VideoOutput,
        frame_callback: t.Callable[[types.VideoFrame], None],
        thread_name: str = None,
    ):
        # name mangling is used so that it can be subclassed simultaneously with MotionOutputMeta
        logging.info("Init VideoOutputMeta")
        self.__t = Thread(daemon=True, name=thread_name, target=self.__run)
        self.__closed = Event()
        self.__event = video_output.event
        self.video_output = video_output
        self.frame_callback = frame_callback
        # track the previous frame so that we can see if we have dropped one somewhere
        self.__prev_frame = None
        self.__t.start()

    def __run(self) -> None:
        while not self.__closed.is_set():
            if self.__event.wait(timeout=1):
                frame = self.video_output.frame
            else:
                logging.warning("Timed out waiting for new frame")
                continue
            if self.__prev_frame is not None:
                if frame.frame_num != self.__prev_frame.frame_num + 1:
                    logging.warning(
                        "Dropped frame. Previous frame = %d. Current frame = %d",
                        self.__prev_frame.frame_num,
                        frame.frame_num,
                    )
            self.__prev_frame = frame
            start = time.perf_counter_ns()
            self.frame_callback(frame)
            end = time.perf_counter_ns()
            # logging.debug(
            #     "Video processing of frame %d ran in %dμs", frame.frame_num, (end - start) / 1_000
            # )

    def close(self):
        self.__closed.set()
        logging.info("Joining video thread")
        self.__t.join()
        logging.info("Video thread joined")


class MotionOutputHandler:
    """Interface defining outputs which process motion frames produced by the camera.

    Any subclass will implement a `process_frame` method, which is called with a
    `Frame` object whenever the camera has produced a new frame. Each output is run
    in a background thread.

    """

    def __init__(
        self,
        motion_output: MotionOutput,
        motion_frame_callback: t.Callable[[types.MotionFrame], None],
        thread_name: str = None,
    ):
        # name mangling is used so that it can be subclassed simultaneously with VideoOutputMeta
        logging.info("Init MotionOutputMeta")
        self.__t = Thread(daemon=True, name=thread_name, target=self.__run)
        self.__closed = Event()
        self.__event = motion_output.event
        self.motion_output = motion_output
        self.motion_frame_callback = motion_frame_callback
        # track the previous frame so that we can see if we have dropped one somewhere
        self.__prev_frame = None
        self.__t.start()

    def __run(self) -> None:
        while not self.__closed.is_set():
            if self.__event.wait(timeout=1):
                frame = self.motion_output.motion_frame
            else:
                logging.warning("Timed out waiting for new frame")
                continue
            if self.__prev_frame is not None:
                if frame.frame_num != self.__prev_frame.frame_num + 1:
                    logging.warning(
                        "Dropped motion frame. Previous frame = %d. Current frame = %d",
                        self.__prev_frame.frame_num,
                        frame.frame_num,
                    )
            self.__prev_frame = frame

            start = time.perf_counter_ns()
            self.motion_frame_callback(frame)
            end = time.perf_counter_ns()
            logging.debug(
                "Motion processing of frame %d ran in %dμs\n",
                frame.frame_num,
                (end - start) / 1_000,
            )

    @abc.abstractmethod
    def process_motion_frame(self, frame: types.MotionFrame) -> None:
        """Handle the receipt of a `MotionFrame` object."""
        return NotImplemented

    def close(self):
        self.__closed.set()
        logging.info("Joining motion thread")
        self.__t.join()
        logging.info("Motion thread joined")

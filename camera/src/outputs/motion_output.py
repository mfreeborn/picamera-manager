from __future__ import annotations

import io
import logging
import time
import threading
import typing as t

import ffmpeg
import numpy as np
import requests
from scipy import ndimage, signal

from ..types import Box, Boxes, VideoFrame, MotionFrame, FrameBuffer
from .bases import BaseOutput, MotionOutputHandler, VideoOutputHandler

if t.TYPE_CHECKING:
    from ..camera import Camera


def create_trigger_image(trigger_frame_group, boxes):
    assert trigger_frame_group._data[0].sps_header
    raw_stream = b""
    for frame in trigger_frame_group:
        raw_stream += frame.data

    logging.info("Trigger frame group length: %d", len(trigger_frame_group))
    logging.info("Raw stream length: %d bytes", len(raw_stream))

    # read input from stdin
    stream = ffmpeg.input("pipe:", f="h264", framerate=30)
    # select the last frame in the video stream
    stream = ffmpeg.filter(stream, "select", f"eq(n,{len(trigger_frame_group)-2})")
    # add each motion box to the output
    for box in boxes:
        stream = ffmpeg.drawbox(
            stream, box.x0, box.y0, box.width, box.height, color="red", thickness=3
        )

    # convert the h264 video into mjpeg, keeping just one frame (i.e. the final frame that
    # was selected by the above filter)
    stream = ffmpeg.output(stream, "pipe:", vframes=1, f="mjpeg")

    out, _err = ffmpeg.run(
        stream, cmd=["ffmpeg", "-hide_banner"], input=raw_stream, capture_stdout=True
    )

    logging.info("Length of return: %d", len(out))
    trigger_image = io.BytesIO(out)

    with open(f"pics/out{time.monotonic_ns()}.jpeg", "wb") as fh:
        fh.write(trigger_image.getvalue())


def find_motion_areas(mask: np.ndarray) -> list:
    """Return a sequence of Slice objects which locate distinct areas of detected motion."""
    # this connections array says that blocks with motion are part of the same group
    # if they are adjacent to a positive block in any direction
    connections = np.ones(9).reshape(3, 3)

    # label_array is the same shape as mask, but each distinct group of positive blocks
    # has a unique number (i.e. label)
    label_array, _ = ndimage.label(mask, structure=connections)

    return ndimage.find_objects(label_array)


def get_bounding_boxes(mask: np.ndarray, slices: list, min_blocks: int) -> Boxes:
    """Return a list of [x0, y0, x1, y1] points describing all boxes where motion was detected."""
    boxes = Boxes()
    # flipping the x and y is deliberate so that the coordinates map nicely from
    # the numpy array slicing to the pillow image coordinates
    for y, x in slices:
        # exclude any areas which don't contain the minimum number of blocks. This
        # has the effect of reducing noise/spurious small areas of change
        if mask[y, x].sum() >= min_blocks:
            # multiply the indices by 16 to convert from macroblock to full size
            box = Box(x0=x.start * 16, y0=y.start * 16, x1=x.stop * 16, y1=y.stop * 16)
            boxes.append(box)

    # remove any smaller boxes which are fully enclosed within a larger box
    boxes.remove_subboxes()
    return boxes


def denoise(mask: np.ndarray, min_neighbours: int = 2) -> np.ndarray:
    """Return a mask with the same shape and size with isolated 'True' blocks removed.

    'min_neighbours' - any True value in the original mask will be removed unless it has
                       at least min_neighbours number of neighbouring blocks in which
                       motion was also detected.
    """
    kernel = np.ones(9).reshape(3, 3).astype(np.uint8)
    kernel[1, 1] = 0
    # move a 3x3 kernel across the mask to return a new matrix where each cell contains the number
    # of positive neighbours it has. Benching demonstrates that scipy.signal.convolve2d is faster
    # than alternatives (incl. oaconvovle and fftconvolve)
    neighbours = signal.convolve2d(mask, kernel, mode="same")

    # by multiplying by 'mask', we zero any blocks where there wasn't any motion detected originally
    mask = neighbours * mask

    # zero any blocks which don't have at least 'min_neighbours' neighbours
    return mask >= min_neighbours


class MotionEvent:
    """A minimal container for a motion event.

    Simply contains the time of the event and the boxes which represent the coordinates
    of the areas where motion was detected in the frame.
    """

    def __init__(self, timestamp: float, motion_boxes: Boxes):
        self.timestamp = timestamp
        self.motion_boxes = motion_boxes


class DetectMotion:
    def __init__(self, sensitivity: int, min_blocks: int, min_frames: int):
        self.sensitivty = sensitivity
        self.min_blocks = min_blocks
        self.min_frames = min_frames
        self._consecutive_motion_frames = 0

    def detect(self, motion_frame: MotionFrame) -> t.Optional[MotionEvent]:
        """Run the motion detection algorithm.

        If motion is detected, a MotionEvent is returned, otherwise returns None.
        """
        # calculate the magnitude of all motion vectors
        t1 = time.perf_counter_ns()
        magnitudes = np.sqrt(
            np.square(motion_frame.motion_data["x"].astype(int))
            + np.square(motion_frame.motion_data["y"].astype(int))
        )

        # TODO: apply a mask to exclude uninteresting areas

        t2 = time.perf_counter_ns()
        motion_mask = magnitudes >= self.sensitivty
        t3 = time.perf_counter_ns()
        # I don't think we actually need to denoise here because we remove very
        # small boxes of motion in `get_bounding_boxes`
        # remove any small, isolated blocks of motion which are probably just noise
        # motion_mask = denoise(motion_mask, min_neighbours=2)
        t4 = time.perf_counter_ns()
        if motion_mask.sum() >= self.min_blocks:
            # we have detected motion in at least the minimum required number of blocks
            # now find where in the image motion was detected
            t5 = time.perf_counter_ns()
            slices = find_motion_areas(motion_mask)
            t6 = time.perf_counter_ns()
            # this function filters out any areas which have less than MIN_BLOCKS number
            # of blocks where motion was detected. As an example, say that MIN_BLOCKS = 3.
            # If that is 3 separate areas with one motion block each, then no boxes will be
            # returned. In contrast, if that is one box with 3 motion blocks, then a box
            # would be returned
            boxes = get_bounding_boxes(motion_mask, slices, self.min_blocks)
            t7 = time.perf_counter_ns()

            if boxes:
                # we have detected motion in this frame
                # self.consecutive_motion_frames lags by one, hence we subtract 1 here
                # when this condition is true, it means we have met all requirements
                # for having detected a motion event
                if self._consecutive_motion_frames >= (self.min_frames - 1):
                    t8 = time.perf_counter_ns()

                    logging.info(
                        "\n"
                        "Calculate magnitudes: %dμs\n"
                        "Create motion mask:   %dμs\n"
                        "Denoise mask:         %dμs\n"
                        "Sum mask:             %dμs\n"
                        "Find motion areas:    %dμs\n"
                        "Get bounding boxes:   %dμs\n"
                        "Rest excl. set event: %dμs\n"
                        "Total:                %dμs\n"
                        "\n"
                        "Number of motion areas: %d\n"
                        "Size of motion areas:   %s\n",
                        (t2 - t1) / 1_000,
                        (t3 - t2) / 1_000,
                        (t4 - t3) / 1_000,
                        (t5 - t4) / 1_000,
                        (t6 - t5) / 1_000,
                        (t7 - t6) / 1_000,
                        (t8 - t7) / 1_000,
                        (t8 - t1) / 1_000,
                        len(boxes),
                        ", ".join(f"{box.area:,d}px" for box in boxes),
                    )

                    return MotionEvent(timestamp=motion_frame.timestamp, motion_boxes=boxes)

                else:
                    self._consecutive_motion_frames += 1
                    return

        # reset the consecutive_motion_frames attribute in all cases except for the else branch
        # in the preceding line
        self._consecutive_motion_frames = 0


class MotionDetectionOutput(BaseOutput):
    def __init__(self, camera: Camera):
        logging.info("Motion output initialising")
        super().__init__(output_name="motion", camera=camera)
        self.video_handler = VideoOutputHandler(
            video_output=camera.video_output,
            frame_callback=self.process_frame,
            thread_name="MotionVideoThread",
        )
        self.motion_handler = MotionOutputHandler(
            motion_output=camera.motion_output,
            motion_frame_callback=self.process_motion_frame,
            thread_name="MotionDataThread",
        )
        self.pre_event_buffer = FrameBuffer(maxlen=camera.framerate * self.config.captured_before)
        self.post_event_buffer = FrameBuffer(maxlen=camera.framerate * self.config.captured_after)
        self.motion_detected = threading.Event()
        self.last_motion_event: t.Optional[MotionEvent] = None
        self.motion_detector = DetectMotion(
            sensitivity=self.config.sensitivity,
            min_blocks=self.config.min_blocks,
            min_frames=self.config.min_frames,
        )

    def process_frame(self, frame: VideoFrame) -> None:
        if not self.motion_detected.is_set():
            # these event buffers are circular, so whilst no motion has been detected, we
            # continually record the most recent frames
            self.pre_event_buffer.append(frame)
        else:
            # we need to switch to the post event buffer...
            self.post_event_buffer.append(frame)
            # ...and just keep filling it until it is full
            if self.post_event_buffer.full:
                # the triggering frame is always the last element of the pre event buffer, as
                # the motion frames always follow the video frame they refer to. Also note
                # that motion frames never follow an SPS header
                trigger_frame_group = self.pre_event_buffer.final_group()

                logging.info("Length of trigger frame group: %d", len(trigger_frame_group))

                full_event = self.pre_event_buffer.concatenate(self.post_event_buffer)
                full_event.trim_start()

                # create_trigger_image(trigger_frame_group, self.last_motion_event.motion_boxes)
                payload = {
                    "motion_video": full_event.raw_bytes(),
                    "trigger_image_data": {
                        "frame_group": trigger_frame_group.raw_bytes(),
                        "trigger_frame_index": len(trigger_frame_group) - 2,
                        "boxes": self.last_motion_event.motion_boxes.serialise(),
                    },
                    "timestamp": self.last_motion_event.timestamp,
                }
                create_trigger_image(trigger_frame_group, self.last_motion_event.motion_boxes)

                SERVER_ADDR = "192.168.1.10:8000"
                # requests.post(f"{SERVER_ADDR}/api/motion_event", data=payload)

                # reset the buffers
                self.pre_event_buffer.clear()
                self.post_event_buffer.clear()

                # reset the motion_detected event flag
                self.motion_detected.clear()

    def process_motion_frame(self, frame: MotionFrame) -> None:
        MIN_MOTION_INTERVAL = self.config.motion_interval
        # if we are already processing a motion detection event, or our pre event
        # buffer hasn't filled up yet, return early
        if self.motion_detected.is_set():
            logging.info("Motion already detected - skipping motion detection")
            return

        if not self.pre_event_buffer.full:
            logging.info("Pre event buffer not yet full - skipping motion detection")
            return

        # if it's too soon after the last motion event, return early
        if self.last_motion_event is not None and time.time() < (
            self.last_motion_event.timestamp + MIN_MOTION_INTERVAL
        ):
            logging.info(
                "Motion detected within the last %ds - skipping motion detection",
                MIN_MOTION_INTERVAL,
            )
            return

        # we've passed all the guards which would obviate the need to run the algorithm
        event = self.motion_detector.detect(frame)
        if event is not None:
            self.last_motion_event = event
            # signal to the video_frame processing thread that we are good to start recording
            # a new motion event
            self.motion_detected.set()

    def close(self):
        self.video_handler.close()
        self.motion_handler.close()

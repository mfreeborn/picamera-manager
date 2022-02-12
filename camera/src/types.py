from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import picamerax


class Boxes:
    def __init__(self, boxes: list = None):
        self._boxes = boxes or []

    def append(self, box: Box) -> None:
        """Add a box to this instance."""
        self._boxes.append(box)

    def remove_subboxes(self) -> None:
        """Remove any `Box` instances which are fully self-contained within another box."""
        boxes = []
        for box in self:
            for other_box in self:
                if box.is_contained_by(other_box):
                    # skip adding this Box to the new list of boxes, as all of it's coordinates
                    # are within the bounds of another Box
                    break
            else:
                boxes.append(box)
        self._boxes = boxes

    def serialise(self) -> List[Tuple[int, int, int, int]]:
        """Convert `Boxes` to a list of lists, where each sublist contains the coords of a box.

        The coordinates of each box are in the same order that they are defined on the `Box` class.

        The utility of this method is that we can then send this datastructure across the network
        as it can be converted to JSON.
        """
        return [tuple(box) for box in self]

    def __iter__(self):
        return iter(self._boxes)

    def __len__(self) -> int:
        return len(self._boxes)


@dataclass
class Box:
    x0: int
    y0: int
    x1: int
    y1: int

    def __iter__(self):
        for attr in [self.x0, self.y0, self.x1, self.y1]:
            yield attr

    def is_contained_by(self, other_box: Box) -> bool:
        """Return True if the box is fully contained within the area of another box, else False."""
        return (
            (self.x1 < other_box.x1)
            and (self.y1 < other_box.y1)
            and (self.x0 > other_box.x0)
            and (self.y0 > other_box.y0)
        )

    @property
    def width(self) -> int:
        """Return the width, in pixels, of the box."""
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        """Return the height, in pixels, of the box."""
        return self.y1 - self.y0

    @property
    def area(self) -> int:
        """Return the number pixels contained in this box."""
        return self.width * self.height


class MotionFrame:
    """Represents a single motion frame, which contains a numpy array of motion vector data."""

    def __init__(self, motion_data: np.ndarray, frame_num: int, timestamp: float):
        self.motion_data = motion_data
        self.frame_num = frame_num
        self.timestamp = timestamp


class VideoFrame:
    """Represents a single h264 video frame.

    Attributes:
        data: the raw bytes data of the frame
        frame_num: a monotonically increasing frame count
        timestamp: the number of seconds since the epoch that this frame was produced
        frame_type: the type of frame produced viz. P-frame, I-frame or SPS header
        sps_header: a short hand for finding out whether this is a header frame
    """

    def __init__(
        self,
        data: bytes,
        frame_num: int,
        timestamp: float,
        frame_type: picamerax.PiVideoFrameType,
    ):
        self.data = data
        self.frame_num = frame_num
        self.timestamp = timestamp
        self.frame_type = frame_type

    @property
    def sps_header(self) -> bool:
        return self.frame_type == picamerax.PiVideoFrameType.sps_header

    def _parse_frame_type(self):
        frame_types = {
            0: "P-frame",
            1: "I-frame",
            2: "SPS header",
            # 3: "Motion data", *unreachable*
        }
        return frame_types[self.frame_type]

    def __repr__(self):
        class_name = self.__class__.__name__
        return (
            f"<{class_name}("
            f"frame_num={self.frame_num}, "
            f"frame_len={len(self.data)}, "
            f"frame_type={self._parse_frame_type()}, "
            f"timestamp={self.timestamp}"
            f")>"
        )


class FrameBuffer:
    """A circular buffer containing H264 video frames."""

    def __init__(self, maxlen: int):
        self._data = deque(maxlen=maxlen)
        self.maxlen = maxlen

    def trim_start(self) -> None:
        """Drop all leading frames in the buffer until an SPS header is the first frame."""
        if self._contains_header_frame:
            while not self._data[0].sps_header:
                self._data.popleft()

    def concatenate(self, other: FrameBuffer) -> FrameBuffer:
        """Return a new buffer containing the concatenating frames of self and other."""
        new_buffer = FrameBuffer(maxlen=self.maxlen + other.maxlen)
        new_buffer._data.extend(self._data.copy() + other._data.copy())
        return new_buffer

    def final_group(self) -> FrameBuffer:
        """Return the last, i.e. most recent, group of pictures in the buffer.

        This group will comprise of the latest SPS header followed by however many data frames
        remain in the buffer.

        The underlying buffer is left unchanged by the end of this method.
        """
        frames = FrameBuffer(maxlen=50)
        trailing_header = None
        if not self.empty:
            if self._data[-1].sps_header:
                trailing_header = self._data.pop()

        if self._contains_header_frame:
            while True:
                frame = self._data.pop()
                frames.append(frame)
                if frame.sps_header:
                    break
            frames.reverse()
            self._data.extend(frames._data.copy())

        if trailing_header is not None:
            self.append(trailing_header)

        return frames

    def reverse(self) -> None:
        """Reverse the order of the frames in the buffer."""
        self._data.reverse()

    def append(self, frame: VideoFrame) -> None:
        """Add a new frame to the end of the buffer.

        If the buffer is already max_len, then the first frame in the buffer will be dropped.
        """
        self._data.append(frame)

    def clear(self) -> None:
        """Remove all frames from the buffer."""
        self._data.clear()

    def raw_bytes(self) -> bytes:
        """Return all the video data in the buffer as bytes."""
        return b"".join(frame.data for frame in self)

    @property
    def full(self) -> bool:
        """Return whether the buffer is full or not."""
        return len(self) == self.maxlen

    @property
    def empty(self) -> bool:
        """Return whether the buffer is empty or not."""
        return not self._data

    @property
    def _contains_header_frame(self) -> bool:
        """Return whether there is at least one SPS header in the buffer."""
        for frame in self:
            if frame.sps_header:
                return True
        return False

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        return iter(self._data)
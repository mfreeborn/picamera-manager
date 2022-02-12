from __future__ import annotations

import logging
import threading
import time
import typing as t

import numpy as np
import picamerax
from picamerax.array import PiMotionAnalysis

from . import encoders, enums, exceptions, outputs
from . import schema as s
from . import types
from .config import Config
from .outputs import bases

if t.TYPE_CHECKING:
    from .config import ServerAddress


class _TimestampedPiCamera(picamerax.PiCamera):
    """PiCamera object which includes timestamps on captures and videos by default."""

    def _get_image_encoder(self, camera_port, output_port, format_, resize, **options):
        """Add a timestamp to every captured image."""
        return encoders.TimestampedImageEncoder(
            self, camera_port, output_port, format_, resize, **options
        )

    def _get_video_encoder(self, camera_port, output_port, format_, resize, **options):
        """Add a timestamp to video recordings."""
        return encoders.TimestampedVideoEncoder(
            self, camera_port, output_port, format_, resize, **options
        )


class VideoOutput:
    """This class is intended to be used as a custom output when recording video.

    It works in unison with subclasses of `BaseOutput` to coordinate the processing of video
    data.

    The `write` method is called repeatedly by the owning `PiCamera` instance when recording
    is active, and receives the most recently recorded frame data as a sequence of bytes.
    During each execution of the `write` method, we can find out more about the current
    frame from the `PiCamera.frame` attribute, which returns a PiVideoFrame object. More often
    than not, a single call to `write` will contain all the data for a single frame, although,
    occassionally a frame may be split across mutliple `write` calls if it is especially large.
    For convenience, we gather combine data across multiple calls to `write`, so that anything
    downstream knows that it will always receive a full frame.

    A `threading.Event` object is the central synchronisation primitive, which we use to
    notify any other interested parties that a new frame is available. Rather than just make the
    frame data available as raw bytes, we package it into a `Frame` object which contains additional
    useful metadata such as a timestamp and the frame type.
    """

    def __init__(self, camera: Camera):
        self.camera = camera
        self.event = threading.Event()
        self.frame: t.Optional[types.VideoFrame] = None
        self._frame_num = 0
        self._current_frame_data = b""

    def write(self, frame_part: bytes) -> None:
        """Notify parties of a new, complete frame being available."""
        self._current_frame_data += frame_part
        pi_frame = self.camera.frame
        if pi_frame.complete:
            self.frame = types.VideoFrame(
                data=self._current_frame_data,
                frame_num=self._frame_num,
                timestamp=time.time(),
                frame_type=pi_frame.frame_type,
            )
            self._current_frame_data = b""
            self._frame_num += 1
            self.event.set()
            self.event.clear()


class MotionOutput(PiMotionAnalysis):
    """Stub output attached to the PiCamera recording motion output.

    This class simply takes the motion vector data (in np.ndarray form) and sends out a notification
    to any interested parties when a new array of motion data (i.e. a frame) is available.

    By subclassing PiMotionAnalysis, this motion data is nicely pre-parsed into a numpy array
    for further processing.

    Attributes:
        event: a threading.Event object which can by waited upon by interested parties. This
            class calls notify_all() every time a new frame's worth of motion data is available.
        motion_data: an np.ndarray of x, y and SAD motion data for the current frame.
    """

    def __init__(self, camera: picamerax.PiCamera):
        super().__init__(camera)
        self.event = threading.Event()
        self.motion_frame: t.Optional[types.MotionFrame] = None
        self._frame_num = 0

    def analyze(self, motion_data: np.ndarray):
        """Notify parties of a new frame's worth of motion vector data is available."""
        self.motion_frame = types.MotionFrame(motion_data, self._frame_num, time.time())
        self._frame_num += 1
        self.event.set()
        self.event.clear()


class Camera:
    """Represents a single PiCamera.

    Configuring the camera is performed via the `configure` method, which enables bulk
    changing and bulk validating of parameters. Such behaviour is desirable as some
    parameters (e.g. resolution and framerate) require the camera to be restarted. Limiting
    the number of times that the camera needs to be restarted to a maximum of once even whilst
    changing multiple parameters at the same time minimises dispruption to the video stream.
    Furthermore, bulk validating of parameters ensures that we don't leave the camera in a
    partially newly configured state.
    """

    _outputs: t.Dict[str, bases.BaseOutput] = {}

    def __init__(self, config_path: str = None):
        logging.info("Initialising camera")
        try:
            self._camera = _TimestampedPiCamera()
        except picamerax.PiCameraMMALError:
            raise exceptions.CameraNotAvailable()

        # check we are running a supported camera i.e. the V2 module or the HQ camera
        self._ensure_camera_supported()

        self.running = False

        # initialise the outputs we will use with the `camera.start_recording` method
        self.video_output = VideoOutput(self._camera)
        self.motion_output = MotionOutput(self._camera)

        # load the config
        self.config = Config(self, config_path)
        self.config.init()

        # more for debugging, really
        self._camera.annotate_frame_num = True

    def _ensure_camera_supported(self):
        """Validate that a supported camera is used (V2 or HQ)."""
        try:
            self.revision
        except ValueError:
            raise exceptions.UnsupportedCamera(self._camera.revision)

    @property
    def revision(self) -> enums.CameraRevision:
        return enums.CameraRevision(self._camera.revision)

    @property
    def server_address(self) -> s.ServerAddress:
        """Return the address of the registered server.

        If present, it is a pydantic object with an `ip: IPv4Address` and a `port: int` field.

        This attribute is read-only can only be configured using the `configure` method.
        """
        return self._camera_server_address

    def _server_address(self, server_address: ServerAddress) -> None:
        self._camera_server_address = server_address

    _server_address = property(None, _server_address)

    @property
    def name(self) -> t.Optional[str]:
        """Return the textual name of the camera.

        This attribute is read-only can only be configured using the `configure` method.
        """
        if hasattr(self, "_camera_name"):
            return self._camera_name

    def _name(self, name: str) -> None:
        self._camera_name = name

    _name = property(None, _name)

    @property
    def viewport_size(self) -> str:
        """Return the viewport size.

        The value is a string in a format consistent with "WIDTHxHEIGHT".

        This attribute is read-only can only be configured using the `configure` method.
        """
        return str(self._camera_viewport_size)

    def _viewport_size(self, viewport_size: str) -> None:
        self._camera_viewport_size = viewport_size

    _viewport_size = property(None, _viewport_size)

    @property
    def resolution(self) -> str:
        """Return the current resolution of the camera.

        The value is a string in a format consistent with "WIDTHxHEIGHT".

        This attribute is read-only can only be configured using the `configure` method.
        """
        return str(self._camera.resolution)

    def _resolution(self, resolution: str) -> None:
        self._camera.resolution = resolution

    _resolution = property(None, _resolution)

    @property
    def framerate(self) -> int:
        """Return the current framerate of the camera.

        This attribute is read-only can only be configured using the `configure` method.
        """
        return int(self._camera.framerate)

    def _framerate(self, framerate: int) -> None:
        self._camera.framerate = framerate

    _framerate = property(None, _framerate)

    @property
    def bitrate(self) -> t.Optional[int]:
        """Return the bitrate of the camera video stream.

        This attribute is read-only can only be configured using the `configure` method.
        """
        if hasattr(self, "_camera_bitrate"):
            return self._camera_bitrate

    def _bitrate(self, bitrate):
        self._camera_bitrate = bitrate

    _bitrate = property(None, _bitrate)

    @property
    def awb_mode(self) -> enums.AWBMode:
        """Return the auto white balance mode of the camera.

        This attribute is read-only can only be configured using the `configure` method.
        """
        return enums.AWBMode(self._camera.awb_mode)

    def _awb_mode(self, awb_mode: enums.AWBMode) -> None:
        self._camera.awb_mode = awb_mode.value

    _awb_mode = property(None, _awb_mode)

    @property
    def hflip(self) -> bool:
        """Return whether the video stream has been flipped horizontally.

        This attribute is read-only can only be configured using the `configure` method.
        """
        return self._camera.hflip

    def _hflip(self, hflip: bool) -> None:
        self._camera.hflip = hflip

    _hflip = property(None, _hflip)

    @property
    def vflip(self) -> bool:
        """Return whether the video stream has been flipped vertically.

        This attribute is read-only can only be configured using the `configure` method.
        """
        return self._camera.vflip

    def _vflip(self, vflip: bool) -> None:
        self._camera.vflip = vflip

    _vflip = property(None, _vflip)

    def configure(self, config: dict):
        self.config.update(config)

    def start(self) -> None:
        """Start the camera recording.

        h264 frames and motion vector frames are sent to the video output stub and motion
        data stub respectively.
        """
        logging.info("Camera starting")
        # start the picamera producing frames
        self._camera.start_recording(
            self.video_output,
            motion_output=self.motion_output,
            format="h264",
            bitrate=self.bitrate,
            # aim for a key frame every ~0.5s
            # intra_period=max(int(self.framerate / 2), 1),
            intra_period=1,
            camera_name=self.name,
            sps_timing=True,
            sei=True,
        )

        # and then initialise any enabled outputs
        for output_name, output_config in self.config.outputs:
            if output_config.enabled:
                self.add_output(output_name)
        self.running = True

    def stop(self) -> None:
        """Stop the camera recording.

        This will raise an error from the picamera library if the camera is not currently recording.
        """
        # stop the actual picamera producing frames
        logging.info("Camera stopping")
        self._camera.stop_recording()
        # and stop any outputs which are currently active
        for output_name in self._outputs.copy():
            self.remove_output(output_name)
        self.running = False

    def close(self) -> None:
        """Release the underlying resources back to the operating system.

        Once closed, the camera has to be  completely re-initialised.
        """
        self._camera.close()
        self.running = False

    def add_output(self, output: enums.OutputName) -> None:
        outputs_map = {
            enums.OutputName.NETWORK: outputs.NetworkOutput,
            enums.OutputName.MOTION: outputs.MotionDetectionOutput,
            enums.OutputName.YOUTUBE: outputs.YouTubeOutput,
        }

        # guard against double-adding outputs
        if output in self._outputs:
            raise Exception(f"{output!r} output already attached to the camera!")

        out = outputs_map[output]
        self._outputs[output] = out(self)

    def remove_output(self, output: enums.OutputName) -> None:
        try:
            output = self._outputs.pop(output)
        except KeyError:
            raise Exception(f"{output!r} output not found; cannot remove it from the camera.")
        else:
            output.close()

    def restart_output(self, output: enums.OutputName) -> None:
        self.remove_output(output)
        self.add_output(output)

    def output_enabled(self, output: enums.OutputName) -> bool:
        return output in self._outputs

    def output_is_stale(self, output_name: str) -> bool:
        """Return whether the current configuration has changed since creation of a given output."""
        output = self._outputs[output_name]
        current_config = output.config
        for attr, new_val in self.config.output(output_name):
            if getattr(current_config, attr) != new_val:
                return True
        return False

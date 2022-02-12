import time

import pytest
import toml
from pydantic import ValidationError

import src.exceptions as exc
from src import enums, types
from src.camera import Camera


def test_camera_singleton(config_template_path):
    # create a camera once...
    camera = Camera(config_path=config_template_path)
    with pytest.raises(exc.CameraNotAvailable):
        # ...and create a second one simultaneously
        Camera(config_path=config_template_path)
    camera.close()


def test_default_camera_parameters(default_camera):
    assert default_camera.name == "test_cam1"
    assert default_camera.resolution == "1640x1232"
    assert default_camera.framerate == 25
    assert default_camera.awb_mode == enums.AWBMode.AUTO
    assert default_camera.vflip == default_camera.hflip == False  # noqa: E712
    assert default_camera.bitrate == 3_000_000
    assert default_camera.server_address


def test_updated_parameter_persists(default_camera, config_path):
    assert default_camera.framerate == 25
    default_camera.configure({"camera": {"framerate": 30}})
    conf = toml.load(str(config_path))
    assert conf["camera"]["framerate"] == 30


def test_invalid_parameter_does_not_persist(default_camera, config_path):
    assert default_camera.framerate == 25
    try:
        default_camera.configure({"camera": {"framerate": 200}})
    except:  # noqa: E722
        pass
    conf = toml.load(str(config_path))
    assert conf["camera"]["framerate"] == 25


def test_default_camera_start_stop(config_template_path):
    default_camera = Camera(config_path=config_template_path)
    assert not default_camera.running
    default_camera.start()
    assert default_camera.running
    default_camera.stop()
    assert not default_camera.running
    default_camera.start()
    assert default_camera.running
    default_camera.stop()
    default_camera.close()
    assert not default_camera.running


def test_video_output_stub(default_camera):
    assert default_camera.video_output.event
    assert default_camera.video_output.frame is None
    default_camera.start()
    # give it a sec for the first frame to be produced
    time.sleep(0.1)
    frame_1 = default_camera.video_output.frame
    assert isinstance(frame_1, types.VideoFrame)
    # let the camera produce another couple of frames and check that
    # they are getting updated in the video output
    time.sleep(1.3)
    frame_2 = default_camera.video_output.frame
    assert frame_2.frame_num > frame_1.frame_num


def test_video_output_stub_event(default_camera):
    assert default_camera.video_output.frame is None
    event = default_camera.video_output.event
    default_camera.start()
    frame_count = 0
    last_frame = None
    while frame_count < 3:
        if event.wait(timeout=0.5):
            frame = default_camera.video_output.frame
            assert isinstance(frame, types.VideoFrame)

            if last_frame is not None:
                assert frame.frame_num == last_frame.frame_num + 1

            frame_count += 1
        else:
            raise Exception("Expected to be notified of a new frame")


def test_motion_output_stub(default_camera):
    assert default_camera.motion_output.event
    assert default_camera.motion_output.motion_frame is None
    default_camera.start()
    # give it a sec for the first frame to be produced
    time.sleep(0.5)
    frame_1 = default_camera.motion_output.motion_frame
    assert isinstance(frame_1, types.MotionFrame)
    time.sleep(0.5)
    frame_2 = default_camera.motion_output.motion_frame
    assert frame_2.frame_num > frame_1.frame_num


def test_motion_output_stub_event(default_camera):
    assert default_camera.motion_output.motion_frame is None
    event = default_camera.motion_output.event
    default_camera.start()
    frame_count = 0
    last_frame = None
    while frame_count < 3:
        if event.wait(timeout=0.5):
            frame = default_camera.motion_output.motion_frame
            assert isinstance(frame, types.MotionFrame)

            if last_frame is not None:
                assert frame.frame_num == last_frame.frame_num + 1

            frame_count += 1
        else:
            raise Exception("Expected to be notified of a new frame")


@pytest.mark.parametrize(
    ["parameter", "value"],
    [
        ("server_address", "192.168.1.1:5000"),
        ("name", "Steve"),
        ("viewport_size", "640x480"),
        ("resolution", "640x480"),
        ("framerate", 20),
        ("bitrate", 1_000_000),
        ("awb_mode", enums.AWBMode.GREYWORLD),
        ("vflip", True),
        ("hflip", True),
    ],
)
def test_cannot_set_parameters_directly(parameter, value, default_camera):
    with pytest.raises(AttributeError):
        setattr(default_camera, parameter, value)


def test_unsupported_parameter_fails(default_camera):
    # check at the root level
    with pytest.raises(exc.UnsupportedParameter):
        default_camera.configure({"iso": "anything"})

    # check at the camera level
    with pytest.raises(exc.UnsupportedParameter):
        default_camera.configure({"camera": {"iso": "anything"}})

    # check at the outputs level
    with pytest.raises(exc.UnsupportedParameter):
        default_camera.configure({"outputs": {"network": {"iso": "anything"}}})


@pytest.mark.parametrize(
    ["parameter", "value"],
    [
        ("resolution", "1920x1080"),
        ("framerate", 20),
        ("bitrate", 1_000_000),
        ("awb_mode", enums.AWBMode.GREYWORLD),
        ("vflip", True),
        ("hflip", True),
    ],
)
def test_configure_camera_parameter(parameter, value, default_camera):
    default_camera.start()
    assert getattr(default_camera, parameter) != value
    default_camera.configure({"camera": {parameter: value}})
    assert getattr(default_camera, parameter) == value


@pytest.mark.parametrize(
    ["parameter", "value"],
    [
        ("resolution", "250x150"),
        ("framerate", 200),
        ("bitrate", 1_000),
        ("awb_mode", "fake_mode"),
        ("vflip", "not true"),
        ("hflip", "not bool"),
    ],
)
def test_configure_camera_parameter_invalid(parameter, value, default_camera):
    default_camera.start()
    with pytest.raises(ValidationError):
        default_camera.configure({"camera": {parameter: value}})


def test_camera_revision(default_camera):
    assert default_camera.revision == enums.CameraRevision.IMX219


def test_unsupported_camera_revision(default_camera):
    # patch the underlying camera to make it think it's the v1 camera
    default_camera._camera._revision = "ov5647"

    # _ensure_supported() is normally called during __init__()
    with pytest.raises(exc.UnsupportedCamera):
        default_camera._ensure_camera_supported()

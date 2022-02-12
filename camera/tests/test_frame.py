from picamerax import PiVideoFrameType

from src import types


def test_frame():
    frame = types.Frame(b"", 0, 123.123, PiVideoFrameType.key_frame)
    assert frame.data == b""
    assert frame.frame_num == 0
    assert frame.timestamp == 123.123
    assert frame.frame_type == PiVideoFrameType.key_frame
    assert not frame.sps_header

import pytest
from pydantic import ValidationError

from src.enums import AWBMode, CameraRevision
from src.schema import CameraConfigSchema, ServerAddress


@pytest.mark.parametrize(
    ["ip", "port"],
    [
        ("192.168.1.255", 1),
        ("1.1.1.1", 5555),
        ("255.255.255.255", 65535),
    ],
)
def test_server_address_schema(ip, port):
    addr = ServerAddress(ip=ip, port=port)
    assert str(addr.ip) == ip
    assert addr.port == port


@pytest.mark.parametrize(
    ["ip", "port"],
    [
        ("192.168.1.256", 0),
        ("1.1.1.1", 555555),
        ("255.255.255", 0),
    ],
)
def test_server_address_schema_invalid(ip, port):
    with pytest.raises(ValidationError):
        ServerAddress(ip=ip, port=port)


@pytest.mark.parametrize(
    ["name", "revision", "resolution", "framerate", "bitrate", "awb_mode", "vflip", "hflip"],
    [
        # known good defaults
        (None, CameraRevision.IMX219, "1920x1080", 25, 1_000_000, AWBMode.CLOUDY, False, False),
        # short name
        ("a", CameraRevision.IMX219, "1920x1080", 25, 1_000_000, AWBMode.CLOUDY, False, False),
        # long name
        ("a" * 30, CameraRevision.IMX219, "1920x1080", 25, 1_000_000, AWBMode.CLOUDY, False, False),
        # different camera revision
        (None, CameraRevision.IMX477, "1920x1440", 25, 1_000_000, AWBMode.CLOUDY, False, False),
        # different resolution
        (None, CameraRevision.IMX219, "1640x1232", 25, 1_000_000, AWBMode.CLOUDY, False, False),
        # low framerate
        (None, CameraRevision.IMX219, "1920x1080", 1, 1_000_000, AWBMode.CLOUDY, False, False),
        # high framerate
        (None, CameraRevision.IMX219, "1920x1080", 30, 1_000_000, AWBMode.CLOUDY, False, False),
        # higher framerate with valid resolution
        (None, CameraRevision.IMX219, "1640x1232", 40, 1_000_000, AWBMode.CLOUDY, False, False),
        # max bitrate
        (None, CameraRevision.IMX219, "1640x1232", 40, 25_000_000, AWBMode.CLOUDY, False, False),
        # another awb mode
        (None, CameraRevision.IMX219, "1640x1232", 40, 25_000_000, AWBMode.AUTO, False, False),
        # including greyworld
        (None, CameraRevision.IMX219, "1640x1232", 40, 25_000_000, AWBMode.GREYWORLD, False, False),
        # different v/hflips
        (None, CameraRevision.IMX219, "1640x1232", 40, 25_000_000, AWBMode.CLOUDY, False, True),
        (None, CameraRevision.IMX219, "1640x1232", 40, 25_000_000, AWBMode.CLOUDY, True, False),
        (None, CameraRevision.IMX219, "1640x1232", 40, 25_000_000, AWBMode.CLOUDY, True, True),
    ],
)
def test_camera_schema(name, revision, resolution, framerate, bitrate, awb_mode, vflip, hflip):
    CameraConfigSchema(
        name=name,
        revision=revision,
        resolution=resolution,
        framerate=framerate,
        bitrate=bitrate,
        awb_mode=awb_mode,
        vflip=vflip,
        hflip=hflip,
    )


@pytest.mark.parametrize(
    ["name", "revision", "resolution", "framerate", "bitrate", "awb_mode", "vflip", "hflip"],
    [
        # too short name
        ("", CameraRevision.IMX219, "1920x1080", 25, 1_000_000, AWBMode.CLOUDY, False, False),
        # too long name
        ("a" * 31, CameraRevision.IMX219, "1920x1080", 25, 1_000_000, AWBMode.CLOUDY, False, False),
        # unsupported resolution
        (None, CameraRevision.IMX477, "1920x1080", 25, 1_000_000, AWBMode.CLOUDY, False, False),
        # unsupported resolution
        (None, CameraRevision.IMX219, "1920x1440", 25, 1_000_000, AWBMode.CLOUDY, False, False),
        # too low framerate
        (None, CameraRevision.IMX219, "1920x1080", 0, 1_000_000, AWBMode.CLOUDY, False, False),
        # too high framerate
        (None, CameraRevision.IMX219, "1920x1080", 60, 1_000_000, AWBMode.CLOUDY, False, False),
        # too high framerate for resolution
        (None, CameraRevision.IMX219, "1920x1080", 40, 1_000_000, AWBMode.CLOUDY, False, False),
        # too high bitrate
        (None, CameraRevision.IMX219, "1640x1232", 40, 25_000_001, AWBMode.CLOUDY, False, False),
        # too low bitrate
        (None, CameraRevision.IMX219, "1640x1232", 40, 0, AWBMode.CLOUDY, False, False),
    ],
)
def test_camera_schema_invalid(
    name, revision, resolution, framerate, bitrate, awb_mode, vflip, hflip
):
    with pytest.raises(ValidationError):
        CameraConfigSchema(
            name=name,
            revision=revision,
            resolution=resolution,
            framerate=framerate,
            bitrate=bitrate,
            awb_mode=awb_mode,
            vflip=vflip,
            hflip=hflip,
        )

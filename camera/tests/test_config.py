from src.config import Config
from src.enums import CameraRevision


def test_init_config(config_path, _fresh_config):
    class MockCamera:
        revision = CameraRevision.IMX219
        name = None
        resolution = None
        framerate = None
        bitrate = None
        awb_mode = None
        vflip = None
        hflip = None
        server_address = None
        running = None

    config = Config(camera=MockCamera, config_path=config_path)
    config.init()

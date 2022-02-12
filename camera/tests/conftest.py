import os
from pathlib import Path

import pytest
import toml

from src.camera import Camera
from src.config import Config
from src.enums import CameraRevision


@pytest.fixture()
def config_path():
    return Path("tests/config/test_camera_config.toml")


@pytest.fixture()
def config_template_path():
    return Path("tests/config/test_camera_config_template.toml")


@pytest.fixture()
def _fresh_config(config_path, config_template_path):
    default_config = toml.load(str(config_template_path))
    with open(config_path, "w") as fh:
        toml.dump(default_config, fh)
    yield
    os.remove(config_path)


@pytest.fixture()
def default_camera(config_path, _fresh_config):
    camera = Camera(config_path)
    yield camera
    camera.close()


@pytest.fixture()
def config_model(config_path, _fresh_config):
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

    yield Config(camera=MockCamera, config_path=config_path)._config

from enum import Enum


class CameraRevision(str, Enum):
    IMX219 = "imx219"  # V2 camera
    IMX477 = "imx477"  # HQ camera


class OutputName(str, Enum):
    MOTION = "motion"
    NETWORK = "network"
    TIMELAPSE = "timelapse"
    YOUTUBE = "youtube"


class AWBMode(str, Enum):
    OFF = "off"
    AUTO = "auto"
    SUNLIGHT = "sunlight"
    CLOUDY = "cloudy"
    SHADE = "shade"
    TUNGSTEN = "tungsten"
    FLUORESCENT = "fluorescent"
    INCANDESCENT = "incandescent"
    FLASH = "flash"
    HORIZON = "horizon"
    GREYWORLD = "greyworld"


class ViewportSize(str, Enum):
    VS_1200X900 = "1200x900"
    VS_640X480 = "640x480"

import typing as t
from ipaddress import IPv4Address

from pydantic import BaseModel as PydanticBaseModel
from pydantic import EmailStr, Field, validator

from . import enums

# p.110 https://www.mclibre.org/descargar/docs/revistas/magpi-books/raspberry-pi-camera-guide-en-2020-04.pdf  # noqa E501
modes = {
    enums.CameraRevision.IMX219: {
        "1920x1080": (1, 30),  # sensor mode 1
        "1640x1232": (1, 40),  # sensor mode 4
    },
    enums.CameraRevision.IMX477: {
        "1920x1440": (1, 50),  # sensor mode 2
    },
}


class BaseModel(PydanticBaseModel):
    class Config:
        # use_enum_values = True
        pass


class ServerAddress(BaseModel):
    ip: IPv4Address
    port: int = Field(..., gt=0, le=65535)


class CameraConfigSchema(BaseModel):
    name: t.Optional[str] = Field(None, min_length=1, max_length=30)
    revision: enums.CameraRevision
    resolution: str
    framerate: int
    bitrate: int = Field(..., ge=1_000_000, le=25_000_000)
    awb_mode: enums.AWBMode
    vflip: bool
    hflip: bool

    @validator("resolution")
    def check_valid_resolution(cls, resolution, values):
        if "revision" not in values:
            raise ValueError("Cannot validate resolution without a valid camera revision.")
        revision = values["revision"]
        resolution = resolution.lower()
        if resolution not in modes[revision]:
            raise ValueError(
                f"Invalid resolution {{{resolution!r}}}. "
                f"Must be one of: {[res for res in modes[revision]]!r}"
            )
        return resolution

    @validator("framerate")
    def check_valid_framerate(cls, framerate, values):
        if "resolution" not in values:
            raise ValueError("Cannot validate framerate without a valid camera resolution.")

        revision = values["revision"]
        resolution = values["resolution"]
        min_framerate, max_framerate = modes[revision][resolution]
        if framerate < min_framerate or framerate > max_framerate:
            raise ValueError(
                f"Invalid framerate {{{framerate!r}}}. Must be between "
                f"{min_framerate} and {max_framerate}, inclusive"
            )
        return framerate


class BaseOutputConfigSchema(BaseModel):
    pass


class NetworkOutputConfigSchema(BaseOutputConfigSchema):
    enabled: bool
    socket_port: int = Field(..., gt=0, le=65535)


class YoutubeOutputConfigSchema(BaseOutputConfigSchema):
    ingestion_url: t.Optional[str]
    # enabled needs to come after ingestion_url so it can be validated last
    enabled: bool

    @validator("enabled")
    def ensure_required_settings(cls, enabled, values):
        if enabled and values.get("ingestion_url") is None:
            raise ValueError("Cannot enable YouTube output without a valid ingestion URL.")
        return enabled


class TimelapseOutputConfigSchema(BaseOutputConfigSchema):
    enabled: bool
    capture_interval: int = Field(..., gt=0)


class MotionOutputConfigSchema(BaseOutputConfigSchema):
    enabled: bool
    captured_before: int = Field(..., gt=0, le=60 * 0.5)  # max 30s
    captured_after: int = Field(..., gt=0, le=60 * 5)  # max 5mins
    motion_interval: int = Field(..., ge=0)
    min_blocks: int = Field(..., gt=0)
    min_frames: int = Field(..., gt=0, le=10)
    sensitivity: int = Field(..., gt=0, le=100)
    notifications_email_address: t.Optional[EmailStr]
    notifications_enabled: bool

    @validator("notifications_enabled")
    def ensure_required_settings(cls, enabled, values):
        if enabled and values.get("notifications_email_address") is None:
            raise ValueError("Cannot enable motion notifications without a valid email address")
        return enabled


class OutputsSchema(BaseModel):
    network: NetworkOutputConfigSchema
    timelapse: TimelapseOutputConfigSchema
    youtube: YoutubeOutputConfigSchema
    motion: MotionOutputConfigSchema


class SavedConfigSchema(BaseModel):
    server_address: t.Optional[ServerAddress]
    # I don't think viewport_size is required by the camera
    viewport_size: enums.ViewportSize
    camera: CameraConfigSchema
    outputs: OutputsSchema

    @validator("outputs")
    def ensure_disabled_outputs_if_no_server_address(cls, outputs, values):
        if values.get("server_address") is None:
            for output_name, output in outputs:
                if output.enabled:
                    raise ValueError(
                        f"Cannot enable {output_name} output without a valid server_address"
                    )
        return outputs

    class Config:
        extra = "forbid"

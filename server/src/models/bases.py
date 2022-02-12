from ..dashboard.app import db
from .mixins import ImageMixin, MediaMixin, VideoMixin

__all__ = ["ImageBase", "VideoBase"]


class _MediaBase(db.Model, MediaMixin):
    __tablename__ = "media"

    media_id = db.Column(db.Integer, primary_key=True)
    camera_id = db.Column(
        db.Integer,
        db.ForeignKey("registered_cameras.camera_id", ondelete="CASCADE"),
        nullable=False,
    )
    # { user_image | timelapse_image | user_video | timelapse_video | motion_video }
    media_type = db.Column(db.Text(), nullable=False)
    timestamp = db.Column(db.DateTime(), nullable=False)
    file_stem = db.Column(db.Text())

    camera = db.relationship("RegisteredCamera", viewonly=True)

    __mapper_args__ = {"polymorphic_identity": "media", "polymorphic_on": media_type}


class ImageBase(ImageMixin, _MediaBase):
    """Base class for image-type media.

    Any image-type media should subclass this object.
    """


class VideoBase(VideoMixin, _MediaBase):
    """Base class for video-type media.

    Any video-type media should subclass this object.
    """

import shutil
from pathlib import Path

import requests

from ..dashboard.app import app, db
from .bases import ImageBase, VideoBase


class RegisteredCamera(db.Model):
    __tablename__ = "registered_cameras"

    camera_id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.Text(), nullable=False, unique=True)
    port = db.Column(db.Text(), nullable=False)
    name = db.Column(db.Text(), nullable=False, unique=True)

    # for YouTube, we need:
    #     1. A stream_id
    #     2. A broadcast_id
    # Both of these are required for properly managing the resultant livestream
    youtube_stream_id = db.Column(db.Text())
    youtube_broadcast_id = db.Column(db.Text())

    timelapse_images = db.relationship(
        "TimelapseImage",
        lazy="dynamic",
        passive_deletes=True,
    )

    timelapse_videos = db.relationship(
        "TimelapseVideo",
        lazy="dynamic",
        passive_deletes=True,
    )

    motion_videos = db.relationship(
        "MotionVideo",
        lazy="dynamic",
        passive_deletes=True,
    )

    def __init__(self, ip_address, port, name):
        self.ip_address = ip_address
        self.port = port
        self.name = name

        # flush here to give us access to the camera_id, which is used in the file tree
        db.session.add(self)
        db.session.flush()

        # set up the data directory. Note this will fail if it already exists (i.e. this
        # camera has the same ID as some previously existing camera which is no longer in
        # the database but hasn't cleaned up it's file tree)
        self.data_dir().mkdir(parents=True)
        for sub_directory in [
            "user_videos",
            "user_images",
            "timelapse_videos",
            "timelapse_images",
            "motion_videos",
        ]:
            self.data_dir(sub_dir=sub_directory).mkdir()

    def delete(self):
        """Entirely delete a registered camera, including all data."""
        # delete all images/videos in the file system
        shutil.rmtree(self.data_dir(), ignore_errors=True)

        # delete itself and relations from the database
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def from_ip_address(cls, ip_address: str):
        return cls.query.filter(cls.ip_address == ip_address).one()

    def data_dir(self, sub_dir: str = None) -> Path:
        """Return the path to the camera's data directory.

        :params:
        sub_dir - One of { "motion" | "timelapse_{images|videos}" | "snapshots" }. Return the
            path to the given sub directory
        """
        data_dir = app.server.config["ROOT_DATA_DIR"] / "cameras" / str(self.camera_id)

        if sub_dir and sub_dir in {
            "timelapse_videos",
            "timelapse_images",
            "motion_videos",
            "user_images",
            "user_videos",
        }:
            return data_dir / sub_dir
        return data_dir

    def get_config(self):
        """Return the configuration settings of the camera client."""
        return requests.get(f"{self.client_url}/config").json()

    @property
    def client_url(self):
        """Return the ip address and port of the camera."""
        return f"http://{self.ip_address}:{self.port}"

    @property
    def video_stream_address(self):
        """Return the TCP address through which the camera streams its video output."""
        conf = self.get_config()
        return f"tcp://{self.ip_address}:{conf['outputs']['network']['socket_port']}"

    @property
    def dir_name(self):
        return "_".join(self.name.lower().split())

    def restart_youtube_stream(self):
        # this grace period gives a chance for the YouTube output to complete the booting
        # up process when the ffmpeg process has just begun
        return requests.post(
            f"{self.client_url}/restart-youtube-stream", json={"grace_period": 10}
        ).json()

    def __repr__(self):
        name = self.__class__.__name__
        return (
            f"<{name}("
            f"camera_id={self.camera_id}, "
            f"name={self.name}, "
            f"ip_address={self.ip_address}, "
            f"port={self.port}"
            f")>"
        )


class TimelapseImage(ImageBase):
    __tablename__ = "timelapse_images"

    image_id = db.Column(
        db.Integer, db.ForeignKey("media.media_id", ondelete="CASCADE"), primary_key=True
    )

    __mapper_args__ = {"polymorphic_identity": "timelapse_image"}


class TimelapseVideo(VideoBase):
    __tablename__ = "timelapse_videos"

    video_id = db.Column(
        db.Integer, db.ForeignKey("media.media_id", ondelete="CASCADE"), primary_key=True
    )

    __mapper_args__ = {"polymorphic_identity": "timelapse_video"}


class MotionVideo(VideoBase):
    __tablename__ = "motion_videos"

    video_id = db.Column(
        db.Integer, db.ForeignKey("media.media_id", ondelete="CASCADE"), primary_key=True
    )

    __mapper_args__ = {"polymorphic_identity": "motion_video"}

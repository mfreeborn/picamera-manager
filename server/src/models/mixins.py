import base64
import datetime
import io
from pathlib import Path

from PIL import Image
from sqlalchemy.ext.hybrid import hybrid_property

from ..dashboard.app import db


class MediaMixin:
    """Mixin class to provide generic attributes for all images and videos."""

    @property
    def data_dir(self) -> Path:
        return self.camera.data_dir(sub_dir=self.media_type + "s")

    @hybrid_property
    def year(self) -> str:
        return self.timestamp.strftime("%Y")

    @year.expression
    def year(cls):
        return db.func.strftime("%Y", cls.timestamp)

    @hybrid_property
    def month(self) -> str:
        return self.timestamp.strftime("%m")

    @month.expression
    def month(cls):
        return db.func.strftime("%m", cls.timestamp)

    @hybrid_property
    def day(self) -> str:
        return self.timestamp.strftime("%d")

    @day.expression
    def day(cls):
        return db.func.strftime("%d", cls.timestamp)

    @hybrid_property
    def date(self) -> str:
        return f"{self.year}-{self.month}-{self.day}"

    @date.expression
    def date(cls) -> str:
        return db.func.strftime("%Y-%m-%d", cls.timestamp)

    def next(self):
        """Return the next most recent piece of media."""
        cls = self.__class__
        return (
            cls.query.filter(cls.timestamp > self.timestamp, cls.camera_id == self.camera_id)
            .order_by(cls.timestamp.asc())
            .limit(1)
            .first()
        )

    def previous(self):
        """Return the previous most recent piece of media."""
        cls = self.__class__
        return (
            cls.query.filter(cls.timestamp < self.timestamp, cls.camera_id == self.camera_id)
            .order_by(cls.timestamp.desc())
            .limit(1)
            .first()
        )

    def has_next(self) -> bool:
        """Return whether or not there is a more recent piece of media."""
        return self.next() is not None

    def has_previous(self) -> bool:
        """Return whether or not there is a less recent piece of media."""
        return self.previous() is not None

    def create_thumbnail(self, image: Image) -> Image:
        """Return a thumbnail if the given image with a maximum width of 256 pixels."""
        thumbnail = image.copy()
        thumb_size = (256, 192)  # this will give us a max width of 256 pixels
        thumbnail.thumbnail(thumb_size)
        return thumbnail

    def default_file_stem(self):
        """Return the default file stem."""
        return f"{self.camera.dir_name} {self.timestamp}"


class ImageMixin:
    def __init__(
        self, camera_id: int, timestamp: datetime.datetime, image: Image, file_stem: str = None
    ):
        # set the basic fields
        self.camera_id = camera_id
        self.timestamp = timestamp

        db.session.add(self)
        db.session.flush()  # now self.camera is available

        # set the file_stem attribute
        self.file_stem = file_stem if file_stem is not None else self.default_file_stem()

        # store the image
        self.thumbnail_dir.mkdir(exist_ok=True, parents=True)
        self.save_fullsize_image(image)
        self.save_thumbnail(self.create_thumbnail(image))

        db.session.commit()

    def to_base64(self, thumbnail: bool = False) -> str:
        """Return a base64 encoded string representation of the image.

        If thumbnail is True, then return the encoded thumbnail, otherwise return the
        encoded fullsize image (default).
        """
        filepath = self.image_path if not thumbnail else self.thumbnail_path
        with open(filepath, "rb") as fh:
            buff = base64.b64encode(fh.read()).decode("utf-8")
        return buff

    def save_fullsize_image(self, image: Image) -> None:
        image.save(self.image_path, format="jpeg")

    def save_thumbnail(self, thumbnail: Image) -> None:
        thumbnail.save(self.thumbnail_path, format="jpeg")

    @property
    def image_filename(self):
        return f"{self.file_stem}.jpg"

    @property
    def image_dir(self):
        return self.data_dir / self.year / self.month / self.day

    @property
    def image_path(self):
        return self.image_dir / self.image_filename

    @property
    def thumbnail_dir(self):
        return self.image_dir / "thumbs"

    @property
    def thumbnail_path(self):
        return self.thumbnail_dir / self.image_filename


class VideoMixin:
    def __init__(
        self,
        camera_id: int,
        timestamp: datetime.datetime,
        video: io.BytesIO,
        title_image: Image,
        file_stem: str = None,
    ):
        self.camera_id = camera_id
        self.timestamp = timestamp

        db.session.add(self)
        db.session.flush()  # now self.camera is available

        # set the file_stem attribute
        self.file_stem = file_stem if file_stem is not None else self.default_file_stem()

        # store the associated media
        self.title_image_thumbnail_dir.mkdir(exist_ok=True, parents=True)
        self.save_video(video)
        self.save_fullsize_title_image(title_image)
        self.save_title_image_thumbnail(self.create_thumbnail(title_image))

        db.session.commit()

    def delete(self):
        """Destructor method for removing a a piece of video media."""
        # start by deleting the data on disk
        for filepath in [self.video_path, self.title_image_path, self.title_image_thumbnail_path]:
            filepath.unlink()

        # and then delete itself from the database
        db.session.delete(self)
        db.session.commit()

    def title_image_to_base64(self, thumbnail: bool = False) -> str:
        """Convert the underlying title_image into a base64 string.

        By default, convert the fullsize image, otherwise convert the thumbnail image
        if thumbnail is set to True.
        """
        filepath = self.title_image_path if not thumbnail else self.title_image_thumbnail_path
        with open(filepath, "rb") as fh:
            encoded_image = base64.b64encode(fh.read()).decode("utf-8")
        return encoded_image

    def save_video(self, video: io.BytesIO) -> None:
        self.video_path.write_bytes(video.getbuffer())

    def save_fullsize_title_image(self, image: Image) -> None:
        image.save(self.title_image_path, format="jpeg")

    def save_title_image_thumbnail(self, image: Image) -> None:
        image.save(self.title_image_thumbnail_path, format="jpeg")

    @property
    def title_image_thumbnail_dir(self) -> Path:
        return self.title_image_dir / "thumbs"

    @property
    def title_image_thumbnail_path(self) -> Path:
        return self.title_image_thumbnail_dir / self.title_image_filename

    @property
    def title_image_dir(self) -> Path:
        return self.video_dir / "title_images"

    @property
    def title_image_path(self) -> Path:
        return self.title_image_dir / self.title_image_filename

    @property
    def video_dir(self) -> Path:
        return self.data_dir / self.year / self.month / self.day

    @property
    def video_path(self) -> Path:
        return self.video_dir / self.video_filename

    @property
    def video_filename(self) -> str:
        return self.file_stem + ".mp4"

    @property
    def title_image_filename(self) -> str:
        return self.file_stem + ".jpg"

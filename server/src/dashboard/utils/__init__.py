import datetime
import io
import shutil
import tempfile
import threading
import time

import dash_bootstrap_components as dbc
import ffmpeg
from dash import html
from PIL import Image
from requests.exceptions import ConnectionError
from sqlalchemy import func


class DateSelectionValues:
    def __init__(self, years, months, days, year, month, day):
        self.years = years
        self.months = months
        self.days = days
        self.year = year
        self.month = month
        self.day = day


class TimelapseEncoder:
    def __init__(self):
        self.encoding = False
        self.proc = None
        self._progress = 0

    @property
    def progress(self):
        if not self.encoding:
            # return None if we aren't currently encoding a timelapse video
            return
        return self._progress

    @progress.setter
    def progress(self, value):
        self._progress = value

    def create_timelapse(self, images, file_stem, fps):
        """Create a timelapse video from the given JPEG filepaths."""
        if self.encoding:
            raise Exception(
                "Encoder already running! Can only encode one timelapse video at a time."
            )

        self.encoding = True

        # gather all the necessary arguments together to pass to the other thread. It's a little
        # involved because we can't just pass it the collection of TimelapseImage database
        # objects due to SQLite threading restrictions (well, we can, but it opens up possible
        # synchronisation bugs)
        filepaths = [im.image_path for im in images]
        title_image = images[0]
        title_image_path = title_image.image_path
        camera_id = title_image.camera_id

        t = threading.Thread(
            target=_create_timelapse,
            args=(self, filepaths, title_image_path, camera_id, fps, file_stem),
        )
        t.start()


def _create_timelapse(encoder, filepaths, title_image_path, camera_id, fps, file_stem):
    try:
        with Image.open(title_image_path) as im:
            width, height = im.size

        with tempfile.TemporaryDirectory() as temp_dir, tempfile.NamedTemporaryFile(
            suffix=".mp4"
        ) as out_file:
            for fp in filepaths:
                shutil.copy2(fp, temp_dir)

            total_frames = len(filepaths)
            print("total frames", total_frames)
            images_input = ffmpeg.input(f"{temp_dir}/*.jpg", framerate=fps, pattern_type="glob")

            cmd = ffmpeg.output(
                images_input,
                str(out_file.name),
                s=f"{width}x{height}",
                vcodec="h264_omx",
                video_bitrate=10_000_000,
                format="mp4",
            )

            encoder.proc = cmd.overwrite_output().run_async(
                cmd=["ffmpeg", "-hide_banner", "-progress", "-", "-nostats"],
                pipe_stdout=True,
                pipe_stderr=True,
            )

            while True:
                line = encoder.proc.stdout.readline().decode("ascii").strip()

                if line == "" and encoder.proc.poll() is not None:
                    break

                if line.startswith("frame="):
                    encoder.progress = int(line.split("=")[1]) / total_frames

            # encoding complete; save it to the database
            out_file.seek(0)
            video_buff = io.BytesIO(out_file.read())
            video_buff.seek(0)

            from ...models import TimelapseVideo  # noqa

            TimelapseVideo(
                camera_id=camera_id,
                timestamp=datetime.datetime.utcnow(),
                video=video_buff,
                title_image=Image.open(title_image_path),
                file_stem=file_stem,
            )
    finally:
        print("timelapse encoding complete")
        encoder.progress = 0
        encoder.encoding = False


class YouTubeMonitor(threading.Thread):
    """Helper class for managing the health of YouTube streams.

    This class runs a background thread which periodically checks that the YouTube stream for
    any camera which is supposed to be stremaing is live and well.
    """

    def __init__(self):
        super().__init__()
        self.daemon = True
        self.start()

    def run(self):
        """Background thread for doing the actual monitoring.

        We run an infinite loop which cycles through all registered cameras and checks whether
        YouTube streaming is enabled. If it is, it checks that the stream is live and healthy. If
        not, it handles recreating the broadcast/restarting the camera's stream according to what
        the problem may be.
        """
        from ...auth.youtube_service import YouTubeHandler
        from ...models import RegisteredCamera

        print("YouTube monitoring thread running in background.")
        while True:
            for cam in RegisteredCamera.query.all():
                # this conditional means we don't waste a get_config() call on cameras which
                # can't possibly be streaming to YouTube
                if cam.youtube_stream_id is not None and cam.youtube_broadcast_id is not None:
                    try:
                        livestream_config = cam.get_config()["outputs"]["livestream"]
                    except ConnectionError:
                        # seems like the camera is offline or something
                        print(f"Failed to initialise monitoring for {cam} - connection error")
                        continue

                    # both of these are required for a camera to be properly streaming to YouTube
                    if livestream_config["youtube_mode"] and livestream_config["ingestion_url"]:
                        handler = YouTubeHandler(cam)

                        # details of broadcasts and livestreams here:
                        # https://developers.google.com/youtube/v3/live/docs
                        bc = handler.get_broadcast(parts="status")
                        # the life_cycle_status lets us know if it is live, complete, or ready
                        life_cycle_status = bc["status"]["lifeCycleStatus"]
                        # the recording status lets us know if it is notRecording, recording
                        # or recorded
                        recording_status = bc["status"]["recordingStatus"]
                        if life_cycle_status != "live" or recording_status != "recording":
                            # need to recreate the broadcast
                            print(
                                "YouTube broadcast lifecycle not live. Status =", life_cycle_status
                            )
                            print("YouTube broadcast not recording. Status =", recording_status)
                            print("Creating new broadcast with", handler)
                            # handler.create_broadcast()
                            # handler.bind()
                            print("New broadcast created")

                        vs = handler.get_video_stream(parts="status")
                        stream_status = vs["status"]["streamStatus"]
                        if stream_status != "active":
                            print("YouTube livestream inactive. Status =", stream_status)
                            # restart the camera stream
                            try:
                                print("Restarting youtube stream for", handler)
                                response = handler.restart_stream()
                            except ConnectionError:
                                print(
                                    "Connection refused whilst trying to restart YouTube stream",
                                    handler,
                                )
                            else:
                                print(response)
            # don't spam too much
            time.sleep(5)


def FolderRow(label, folders):
    return [
        dbc.Row(dbc.Col(html.H5(label))),
        dbc.Row(
            folders,
            style={
                "overflowX": "auto",
                "flexWrap": "unset",
                "marginLeft": -15,
                "marginRight": 0,
                "paddingBottom": 16,
                "paddingTop": 3,
            },
        ),
    ]


def make_folder(label):
    return dbc.Col(
        dbc.Button(
            [
                dbc.Row(
                    dbc.Col(
                        html.I(
                            "folder",
                            className="material-icons",
                            style={"fontSize": 60},
                        )
                    )
                ),
                dbc.Row(dbc.Col(html.P(label, className="no-margin", style={"marginTop": -12}))),
            ],
            id={"type": "day-folder", "index": label},
            style={"paddingTop": 0, "paddingBottom": 0},
        ),
        style={"textAlign": "center"},
        width="auto",
    )


def get_date_dropdown_values(camera, model, day=None, month=None, year=None):
    """Return a grouping of values which are used to show the selected/selectable dates of
    images/videos for a given model, where model is TimelapseImage or MotionVideo."""
    available_years = (
        camera.timelapse_images.with_entities(func.distinct(model.year))
        .order_by(model.year.desc())
        .scalars()
    )

    # we default to today if there are no timelapse images at all
    if not available_years:
        today = datetime.date.today()
        year, month, day = str(today.year), f"{today.month:02}", f"{today.day:02}"
        return DateSelectionValues(
            years=[{"label": year, "value": year}],
            months=[
                {"label": datetime.datetime.strptime(month, "%m").strftime("%B"), "value": month}
            ],
            days=FolderRow(label="Day", folders=[make_folder(day)]),
            year=year,
            month=month,
            day=day,
        )

    # at this point, we know we have at least one date, so available_{years|months|days} will
    # all have a minimum length of one
    years = [{"label": year, "value": year} for year in available_years]

    if year is None:
        year = available_years[0]

    available_months = (
        camera.timelapse_images.with_entities(func.distinct(model.month))
        .filter(model.year == year)
        .order_by(model.month.asc())
        .scalars()
    )
    months = [
        {"label": datetime.datetime.strptime(month, "%m").strftime("%B"), "value": month}
        for month in available_months
    ]

    if month is None:
        month = available_months[0]

    available_days = (
        camera.timelapse_images.with_entities(func.distinct(model.day))
        .filter(model.year == year, model.month == month)
        .order_by(model.day.desc())
        .scalars()
    )

    days = FolderRow(label="Day", folders=[make_folder(day) for day in available_days])

    if day is None:
        day = available_days[0]

    return DateSelectionValues(
        years=years,
        months=months,
        days=days,
        year=year,
        month=month,
        day=day,
    )

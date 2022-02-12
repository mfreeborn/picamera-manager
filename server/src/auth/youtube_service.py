import datetime
import os
import pickle
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ..dashboard.app import db

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


class YouTubeService:
    """Helper class providing read/write access to the YouTube API."""

    SCOPES = ["https://www.googleapis.com/auth/youtube"]
    AUTH_DIR = Path(".") / "src" / "auth"
    CREDENTIALS_PICKLE_FILENAME = "youtube_api_credentials.pickle"
    CLIENT_SECRETS_FILENAME = "client_secret.json"
    _service = None
    _flow = None

    @property
    def service(self):
        if self.flow_completed:
            if self._service is None:
                self._service = self.get_authenticated_service()
            return self._service
        raise Exception("Must run the authentication flow before using the YouTube API.")

    @property
    def flow(self):
        if self._flow is None:
            self._flow = InstalledAppFlow.from_client_secrets_file(
                self.AUTH_DIR / self.CLIENT_SECRETS_FILENAME, self.SCOPES
            )
            # set this here because it is needed across a couple of different methods
            self._flow.redirect_uri = self._flow._OOB_REDIRECT_URI
        return self._flow

    def auth_flow_url(self):
        """Return the authorization_url to begin the OAuth2 flow."""
        auth_args = {"promt": "consent", "access_type": "offline"}
        auth_url, _ = self.flow.authorization_url(**auth_args)
        return auth_url

    def complete_auth_flow(self, code):
        """Fetch and store the Google OAuth2 Credentials object with the given 'code'."""
        self.flow.fetch_token(code=code)

        # save the credentials so we don't need to rerun the auth flow again
        with open(self.AUTH_DIR / self.CREDENTIALS_PICKLE_FILENAME, "wb") as fh:
            pickle.dump(self.flow.credentials, fh)

    def get_authenticated_service(self):
        credentials = self.get_credentials()
        # pretty sure the credentials are now self-refreshing
        return build("youtube", "v3", credentials=credentials)

    @classmethod
    def get_credentials(cls):
        if cls.flow_completed:
            with open(cls.AUTH_DIR / cls.CREDENTIALS_PICKLE_FILENAME, "rb") as fh:
                credentials = pickle.load(fh)
            return credentials
        else:
            raise Exception("Must run the authentication flow before retrieving the credentials.")

    @property
    def flow_completed(self) -> bool:
        """Return whether or not the OAuth2 authentication workflow has previously been done."""
        return (self.AUTH_DIR / self.CREDENTIALS_PICKLE_FILENAME).exists()

    def get_broadcast(self, broadcast_id, parts):
        """Return a broadcast resource with the given ID from the YouTube API, if it exists."""
        parts = parts or "id,snippet,contentDetails,status"
        query = self.service.liveBroadcasts().list(part=parts, id=broadcast_id)
        response = query.execute()

        if not response["items"]:
            # no broadcast found with this id
            return None
        # we are querying by id, so we will necessarily only get one result back
        return response["items"][0]

    def create_broadcast(self, camera_name):
        """Create a broadcast using the YouTube API with the given arguments."""
        scheduled_start_time = datetime.datetime.now().isoformat()
        print(scheduled_start_time)

        request = self.service.liveBroadcasts().insert(
            part="snippet,contentDetails,status",
            body={
                "snippet": {
                    "title": f"{camera_name} Livestream",  # required
                    "description": (
                        f"Automated livestream of '{camera_name}'.\n\nProduced by PiCamera Manager."
                    ),
                    "scheduledStartTime": scheduled_start_time,  # required
                },
                "contentDetails": {
                    "latencyPreference": "ultraLow",
                    "enableAutoStart": True,
                    "enableAutoStop": False,  # we want to try and keep the same broadcast around
                },
                "status": {
                    "privacyStatus": "private",  # required
                    "selfDeclaredMadeForKids": False,
                },
            },
        )

        return request.execute()

    def get_video_stream(self, livestream_id, parts):
        """Return a livestream resource with the given ID from the YouTube API, if it exists."""
        parts = parts or "snippet,cdn,contentDetails,status"
        query = self.service.liveStreams().list(part=parts, id=livestream_id)
        response = query.execute()

        if not response["items"]:
            # no broadcast found with this id
            return None
        # we are querying by id, so we will necessarily only get one result back
        return response["items"][0]

    def create_video_stream(self, camera_name):
        """Create a video stream using the YouTube API.

        Video streams represent a stream key in the YouTube user interface.
        """
        request = self.service.liveStreams().insert(
            part="snippet,cdn,contentDetails,status",
            body={
                "cdn": {
                    "frameRate": "30fps",  # required (30fps | 60fps)
                    "ingestionType": "rtmp",  # required
                    "resolution": "1080p",  # required
                },
                "contentDetails": {"isReusable": True},  # more efficient API usage
                "snippet": {
                    "title": f"{camera_name} Stream Resource",  # required
                },
            },
        )

        return request.execute()

    def bind(self, broadcast_id, stream_id):
        """Bind together the given broadcast and stream."""
        request = self.service.liveBroadcasts().bind(
            part="id,contentDetails",
            id=broadcast_id,
            streamId=stream_id,
        )

        return request.execute()


class YouTubeHandler:
    """Carry out YouTube API calls for the given RegisteredCamera instance."""

    def __init__(self, cam):
        self.cam = cam
        self.service = YouTubeService()

    def auth_flow_url(self):
        """Return the authorization_url to begin the oauth2 flow."""
        return self.service.auth_flow_url()

    @property
    def flow_completed(self):
        """Return whether the user has completed the OAuth2 workflow for YouTube access."""
        return self.service.flow_completed

    def get_broadcast(self, parts=None):
        """Return the broadcast resource associated with this camera.

        Will return None if no broadcast resource is found.
        """
        broadcast_id = self.cam.youtube_broadcast_id

        if broadcast_id is None:
            return
        return self.service.get_broadcast(broadcast_id, parts=parts)

    def create_broadcast(self):
        """Create a new broadcast resource and save the ID to the RegisteredCamera.

        Sensible defaults are used. The livestream's name is derived from the camera name.

        TODO: description and privacyStatus would be two parameters which we should let
        users configure.
        """
        broadcast = self.service.create_broadcast(camera_name=self.cam.name)

        self.cam.youtube_broadcast_id = broadcast["id"]
        db.session.commit()

        return broadcast

    def get_video_stream(self, parts=None):
        """Return the livestream resource associated with this camera.

        Will return None if no livestream resource is found.
        """
        livestream_id = self.cam.youtube_stream_id

        if livestream_id is None:
            return
        return self.service.get_video_stream(livestream_id, parts)

    def create_video_stream(self):
        """Create a new  livestream resource and save the ID to the RegisteredCamera.

        Stream configuration is assumed to work with 1080p 30fps, whilst the title is
        derived from the camera name.
        """
        stream = self.service.create_video_stream(camera_name=self.cam.name)

        self.cam.youtube_stream_id = stream["id"]
        db.session.commit()

        return stream

    def bind(self):
        broadcast_id = self.cam.youtube_broadcast_id
        stream_id = self.cam.youtube_stream_id

        if broadcast_id is None or stream_id is None:
            raise Exception(
                "The provided RegisteredCamera has no associated stream or broadcast. "
                "Ensure that both of these resources have been created before calling this method."
            )

        return self.service.bind(broadcast_id=broadcast_id, stream_id=stream_id)

    def restart_stream(self):
        """Restart the associated camera's ffmpeg stream to YouTube."""
        return self.cam.restart_youtube_stream()

    def __repr__(self):
        name = self.__class__.__name__
        return f"<{name}(cam={self.cam})>"

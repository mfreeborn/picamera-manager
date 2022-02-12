import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    PORT = 8000
    DEBUG = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ROOT_DATA_DIR = Path("data").resolve()  # picamera-manager/server/data
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{ROOT_DATA_DIR / 'cam_manager.db'}"


class Development(Config):
    DEBUG = True
    PORT = 8001


class Production(Config):
    pass


envs = {"DEVELOPMENT": Development, "PRODUCTION": Production}


def load_settings(env="DEVELOPMENT"):
    if os.getenv("ENV") is None:
        os.environ["ENV"] = env
    env = os.environ["ENV"]

    return envs[env]()

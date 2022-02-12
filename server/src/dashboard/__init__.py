from .app import app
from .pages.base import BASE_LAYOUT
from .pages.base import callbacks as base_callbacks  # noqa: F401
from .pages.main import callbacks as main_callbacks  # noqa: F401

app.layout = BASE_LAYOUT

from enum import Enum, auto


class _BaseElement(str, Enum):
    def _generate_next_value_(name, start, count, last_values):
        return "-".join(name.lower().split("_"))


class Element(_BaseElement):
    """Enumerations for HTML elements."""

    # ---base layout---
    BASE_DIV = auto()
    PAGE_CONTENT = auto()

    CAMERA_SELECT = auto()

    ADD_CAMERA_MODAL_BUTTON_OPEN = auto()
    ADD_CAMERA_MODAL_BUTTON_CLOSE = auto()
    ADD_CAMERA_MODAL_BUTTON_SAVE = auto()
    ADD_CAMERA_MODAL = auto()

    ADD_CAMERA_IP_ADDRESS_INPUT = auto()
    ADD_CAMERA_IP_ADDRESS_INPUT_FULLY_VALID = auto()
    ADD_CAMERA_IP_ADDRESS_FORM_FEEDBACK = auto()
    ADD_CAMERA_PORT_INPUT = auto()
    ADD_CAMERA_PORT_INPUT_FULLY_VALID = auto()
    ADD_CAMERA_PORT_FORM_FEEDBACK = auto()
    ADD_CAMERA_NAME_INPUT = auto()
    ADD_CAMERA_NAME_INPUT_FULLY_VALID = auto()
    ADD_CAMERA_NAME_FORM_FEEDBACK = auto()
    ADD_CAMERA_FORM_SUBMISSION_ERROR = auto()
    ADD_CAMERA_FORM_SUBMISSION_ERROR_TEXT = auto()

    DELETE_CAMERA_MODAL_BUTTON_OPEN = auto()
    DELETE_CAMERA_MODAL_BUTTON_CLOSE = auto()
    DELETE_CAMERA_MODAL_BUTTON_CONFIRM = auto()
    DELETE_CAMERA_NAME = auto()
    DELETE_CAMERA_MODAL = auto()

    # ---side bar---
    SAVE_CAMERA_CONFIG_BUTTON = auto()
    CHANGED_CONFIG_STORE = auto()
    LIVESTREAM_OUTPUT_LINK = auto()
    TIMELAPSE_OUTPUT_LINK = auto()
    MOTION_OUTPUT_LINK = auto()

    CAMERA_NAME_INPUT = auto()
    CAMERA_URL_INPUT = auto()
    CAMERA_RESOLUTION_INPUT = auto()
    CAMERA_FRAMERATE_INPUT = auto()
    CAMERA_VIEWPORT_SIZE_INPUT = auto()
    CAMERA_AWB_MODE_INPUT = auto()
    CAMERA_EXPOSURE_MODE_INPUT = auto()
    CAMERA_VFLIP_INPUT = auto()
    CAMERA_HFLIP_INPUT = auto()

    CAMERA_NETWORK_BITRATE_INPUT = auto()

    CAMERA_TIMELAPSE_CAPTURE_INTERVAL_INPUT = auto()

    CAMERA_YOUTUBE_BITRATE_INPUT = auto()

    CAMERA_MOTION_CAPTURED_BEFORE_INPUT = auto()
    CAMERA_MOTION_CAPTURED_AFTER_INPUT = auto()
    CAMERA_MOTION_INTERVAL_INPUT = auto()
    CAMERA_MOTION_MIN_FRAMES_INPUT = auto()
    CAMERA_MOTION_MIN_BLOCKS_INPUT = auto()

    # ---output content---
    ACTIVE_OUTPUT = auto()
    RELOAD_OUTPUT_CONTENT_FLAG = auto()
    OUTPUT_CONTENT_DIV = auto()

    INIT_MSE_CLIENT = auto()
    SERVER_IP_ADDRESS = auto()
    SERVER_PORT = auto()

    TIMELAPSE_MONTH_DROPDOWN = auto()
    TIMELAPSE_YEAR_DROPDOWN = auto()
    TIMELAPSE_CAPTURES_CONTAINER = auto()

    YOUTUBE_OAUTH_BUTTON = auto()

class CameraNotAvailable(Exception):
    def __init__(self):
        message = "Unable to start camera - ensure that an instance isn't already running"
        super().__init__(message)


class UnsupportedCamera(Exception):
    def __init__(self, revision):
        message = (
            f"'{revision}' is not a supported camera revision. "
            f"Please use either the V2 or HQ camera module."
        )
        super().__init__(message)


class UnsupportedParameter(Exception):
    def __init__(self, attr):
        message = f"{{{attr!r}}} is an unsupported parameter"
        super().__init__(message)


class InvalidParameter(Exception):
    def __init__(self, parameter, allowed_parameters):
        message = (
            f"'{parameter}' is an unsupported parameter. "
            f"Must be one of: {', '.join(str(v) for v in allowed_parameters)}"
        )
        super().__init__(message)


class InvalidParameterValue(Exception):
    def __init__(
        self, parameter, new_value, allowed_values=None, allowed_range=None, custom_message=None
    ):
        message = f"'{new_value}' is not a valid value for '{parameter}'."

        if allowed_values is not None:
            message += f" Must be one of: {', '.join(str(v) for v in allowed_values)}."
        elif allowed_range is not None:
            message += f" Must be between {allowed_range[0]} and {allowed_range[1]}."
        elif custom_message is not None:
            message += f" {custom_message}"

        super().__init__(message)

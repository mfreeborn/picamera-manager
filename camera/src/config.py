from __future__ import annotations

import json
import logging
import typing as t
from pathlib import Path

import toml

from . import exceptions as exc
from . import schema as s

if t.TYPE_CHECKING:
    from .camera import Camera


class Config:
    CONFIG_TEMPLATE_PATH = Path("camera_config_template.toml")
    DEFAULT_CONFIG_PATH = Path("camera_config.toml")

    def __init__(self, camera: Camera, config_path: t.Optional[Path] = None):
        self.camera = camera
        self.config_path = (
            Path(config_path) if config_path is not None else self.DEFAULT_CONFIG_PATH
        )
        self._config = self.load(str(self.config_path))
        self.log_values()

    def init(self):
        # we need to trigger the server_address attribute early
        self.camera._server_address = self._config.server_address
        self.apply()

    @property
    def camera_settings(self) -> s.CameraConfigSchema:
        return self._config.camera

    @property
    def outputs(self) -> s.OutputsSchema:
        return self._config.outputs

    def output(self, output_name: str) -> s.aseOutputConfigSchema:
        return getattr(self.outputs, output_name)

    def load(self, config_path: Path) -> s.SavedConfigSchema:
        """Parse the toml encoded config file into a validated pydantic schema."""
        config = toml.load(config_path)
        # make sure we have an accurate camera revision by getting it directly from the hardware
        config.get("camera", {})["revision"] = self.camera.revision
        return s.SavedConfigSchema(**config)

    def update(self, new_config: dict) -> None:
        # create a new temoporary in-memory config model which we will first assign any new
        # configuration values - there is no validation when assigning directly to this model
        temp_config = self._config.copy(deep=True)
        print(temp_config)

        # start with server_address and camera, which are both top-level settings
        if "server_address" in new_config:
            temp_config.server_address = s.ServerAddress.construct(
                **new_config.pop("server_address")
            )

        for attr, val in new_config.pop("camera", {}).items():
            print(attr, val)
            try:
                setattr(temp_config.camera, attr, val)
            except ValueError as e:
                raise exc.UnsupportedParameter(f"camera.{attr}") from e

        # then update the output settings, which are nested one level deeper under the `outputs`
        # attribute on the config schema
        new_config_outputs = new_config.pop("outputs", None)
        if new_config_outputs is not None:
            for output in ["network", "timelapse", "motion", "youtube"]:
                for attr, val in new_config_outputs.pop(output, {}).items():
                    try:
                        setattr(getattr(temp_config.outputs, output), attr, val)
                    except ValueError as e:
                        raise exc.UnsupportedParameter(f"outputs.{output}.{attr}") from e

        for attr in new_config:
            raise exc.UnsupportedParameter(attr)

        # validate the temp_config now that we've assigned all the new values
        self._config = type(self._config)(**temp_config.dict())

        # apply the validated config to the camera
        self.apply()

        self.save()

    def apply(self) -> None:
        """Configure the camera with values provided."""
        camera_settings_to_update = {}
        for attr, new_val in self.camera_settings:
            current_val = getattr(self.camera, attr)
            if current_val != new_val:
                camera_settings_to_update[attr] = new_val
        if self.camera.server_address is None and self._config.server_address is not None:
            camera_settings_to_update["server_address"] = self._config.server_address

        need_to_start = False
        if self.camera.running and any(
            param in camera_settings_to_update for param in ["resolution", "bitrate", "framerate"]
        ):
            self.camera.stop()  # this also removes all outputs
            need_to_start = True

        for attr, val in camera_settings_to_update.items():
            old_val = getattr(self.camera, attr)
            setattr(self.camera, "_" + attr, val)
            logging.info("camera.%s changed from %r to %r", attr, old_val, val)

        if need_to_start:
            self.camera.start()  # this also starts all outputs
        else:
            # only need to do this if the camera is running, because they will all be started
            # afresh when the camera itself is next started
            if self.camera.running:
                # otherwise we need to check individually if any of the outputs need managing
                for output_name, output_conf in self.outputs:
                    output_enabled = self.camera.output_enabled(output_name)
                    if not output_enabled and output_conf.enabled:
                        self.camera.add_output(output_name)
                    elif output_enabled and not output_conf.enabled:
                        self.camera.remove_output(output_name)
                    elif output_enabled and output_conf.enabled:
                        # the output is currently enabled and should remain enabled. The question is
                        # whether we need to restart it due to a settings change.
                        if self.camera.output_is_stale(output_name):
                            self.camera.restart_output(output_name)
                    else:
                        # this output is both currently not active and should not be enabled
                        pass

    def save(self, path: t.Optional[Path] = None) -> None:
        """Persist the current in-memory configuration to disk, as a TOML file."""
        path = path or self.config_path
        with open(path, "w") as fh:
            # we don't persist the camera revision because that is taken directly from the camera
            # hardware on initial load
            toml.dump(self.to_dict(exclude={"camera": {"revision"}}), fh)

    def reset(self) -> None:
        """Revert the camera config back to its original default state."""
        self._config = self.load(config_path=self.CONFIG_TEMPLATE_PATH)
        self.apply()
        self.save()

    def to_dict(self, exclude: t.Optional[dict] = None) -> dict:
        """Convert the configuration schema from a pydantic model to a dictionary."""
        # the purpose of round-tripping to and from JSON is to trigger the JSON-specific encoders
        # which parse some of the pydantic types into primitives (e.g. IPv4Address -> str)
        return json.loads(self._config.json(exclude=exclude))

    def log_values(self):
        """Helper method for dumping all values to the logs."""
        logging.info(
            "TOML settings loaded from %r with the following values:", self.config_path.resolve()
        )
        logging.info("server_address")
        if self._config.server_address is not None:
            logging.info("    ip         -> %r", self._config.server_address.ip)
            logging.info("    port       -> %d", self._config.server_address.port)
        else:
            logging.info("    no server address present")
        logging.info("camera")
        for attr, val in self.camera_settings:
            logging.info("    %-10s -> %r", attr, val)
        for output, pad in [("network", 11), ("timelapse", 16), ("motion", 21), ("youtube", 11)]:
            logging.info(output)
            for attr, val in getattr(self._config.outputs, output):
                logging.info(f"    %-{pad}s -> %r", attr, val)
        logging.info("")

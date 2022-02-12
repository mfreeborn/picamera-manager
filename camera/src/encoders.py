import datetime

import picamerax
import picamerax.mmal as mmal


class TimestampedVideoEncoder(picamerax.PiCookedVideoEncoder):
    """Extended video encoder which inserts timestamps on video frames."""

    def __init__(self, parent, camera_port, input_port, format, resize, **options):
        self.camera_name = options.pop("camera_name")
        super().__init__(parent, camera_port, input_port, format, resize, **options)

    def stamp(self):
        text = f"{self.camera_name} - {datetime.datetime.now():%d/%m/%Y %H:%M:%S}"
        self.parent.annotate_text = text

    def start(self, output, motion_output=None):
        # this method is called once just before capturing commences, so here we can set
        # the initial timestamp
        self.stamp()
        super().start(output, motion_output)

    def _callback_write(self, buf):
        # this method is called at least once per frame, so here we can update the timestamp.
        # We will only do so after whole I frames and P frames, just to reduce the number of
        # calls to .stamp() a little.
        # Note that this actually sets the timestamp that will appear on the subsequent frame.
        ret = super()._callback_write(buf)
        if (buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END) and not (
            buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_CONFIG
        ):
            self.stamp()
        return ret


class TimestampedImageEncoder(picamerax.PiCookedOneImageEncoder):
    """Extended image encoder which inserts timestamps on image frames."""

    def stamp(self):
        stamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.parent.annotate_text = stamp

    def start(self, output):
        # this method is called once just before capturing commences, so here we can set
        # the initial timestamp
        self.stamp()
        super().start(output)

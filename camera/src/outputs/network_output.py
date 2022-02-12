from __future__ import annotations

import logging
import socket
import threading
import typing as t

from .bases import BaseOutput, VideoOutputHandler

if t.TYPE_CHECKING:
    from ..camera import Camera
    from ..config import NetworkOutputConfigSchema
    from ..types import VideoFrame


class _SocketThread(threading.Thread):
    def __init__(self, network_output: NetworkOutput, config: NetworkOutputConfigSchema):
        super().__init__(daemon=True, name="NetworkSocketThread")
        self.closed = False
        self.network_output = network_output
        self.socket = socket.socket()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port = config.socket_port
        self.socket.bind(("0.0.0.0", port))
        self.socket.listen(0)
        self.start()

    def run(self) -> None:
        # this primary loop repeatedly re-establishes connections once broken
        while not self.closed:
            logging.info(f"Waiting for connection on port {self.socket.getsockname()[1]}")
            stream_initialised = False

            try:
                # this call to .accept() is blocking, but an OSError is raised when the socket
                # is shutdown (e.g. by the parent thread)
                conn, addr = self.socket.accept()
            except OSError:
                break

            logging.info(f"Received connection from {addr}")

            # this subloop is responsible for continuously sending frame data once connected
            while not self.closed:
                with self.network_output.process_frame_cv:
                    if self.network_output.process_frame_cv.wait(timeout=1):
                        frame = self.network_output.frame
                    else:
                        logging.warning("Timed out waiting for frame")
                        continue

                # discard frames until the first SPS header comes through, at which point
                # we can stream subsequent frames continuously
                if not stream_initialised:
                    if not frame.sps_header:
                        logging.info("Skipping initial non-header frame")
                        continue
                    else:
                        # this frame is the first SPS header since the new connection
                        stream_initialised = True
                try:
                    conn.sendall(frame.data)
                except ConnectionError:
                    # the connection is broken, for whatever reason, so we break out
                    # of the subloop and return to the main loop
                    logging.info("Connection terminated")
                    break

    def close(self) -> None:
        """Close the socket thread and release any underlying resources.

        This method is called by MainThread.
        """
        self.closed = True
        # this raises an OSError in a thread blocked on socket.accept()
        self.socket.shutdown(2)
        self.socket.close()
        super().join()


class NetworkOutput(BaseOutput):
    def __init__(self, camera: Camera):
        """Initialise the network output.

        This method is called by MainThread.
        """
        logging.info("Network output initialising")
        super().__init__(output_name="network", camera=camera)

        self.video_handler = VideoOutputHandler(
            camera.video_output, self.process_frame, "NetworkVideoThread"
        )

        # this is used to communicate with the socket thread
        self.process_frame_cv = threading.Condition()

        # updated with the most recent frame and contains the data which the socket
        # thread will use
        self.frame: t.Optional[VideoFrame] = None

        # use a separate thread to handle connections and writing data
        self.socket_thread = _SocketThread(network_output=self, config=self.config)

    def process_frame(self, frame: VideoFrame) -> None:
        """Make the current frame available to the socket thread.

        This method is called by NetworkVideoThread.
        """
        with self.process_frame_cv:
            self.frame = frame
            self.process_frame_cv.notify()

    def close(self) -> None:
        """Tidily release all resources.

        This method is called by MainThread.
        """
        logging.info("Network output closing down")
        # close the VideoOutputMeta thread which is listening out for notifications
        # of new frames
        self.video_handler.close()

        # shutdown the socket thread which is listening out for connections to send
        # frames to or actively sending frames to a connection
        self.socket_thread.close()

        logging.info("Network output closed")

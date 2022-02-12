import time

from src.outputs import NetworkOutput, MotionDetectionOutput


def test_local_network(default_camera):
    # view stream with vlc tcp/h264://192.168.1.21:8000 --h264-fps=25
    default_camera.start()
    no = NetworkOutput(default_camera)
    time.sleep(10)
    no.close()


def test_motion_detection_output(default_camera):
    default_camera.start()
    time.sleep(0.5)
    mo = MotionDetectionOutput(default_camera)
    no = NetworkOutput(default_camera)
    time.sleep(15)
    no.close()
    mo.close()

import numpy as np
import timeit
from scipy import signal
import time
from functools import partial

magnitudes = np.loadtxt("out.txt")

print(magnitudes)

motion_mask = magnitudes >= 10
kernel = np.ones(9).reshape(3, 3).astype(np.uint8)
kernel[1, 1] = 0

print(motion_mask.shape)
print(kernel.shape)


def denoise(mask, kernel, min_neighbours=2):
    """Return a mask with the same shape and size with isolated 'True' blocks removed.

    'min_neighbours' - any True value in the original mask will be removed unless it has
                       at least min_neighbours number of neighbouring blocks in which
                       motion was also detected.
    """
    # move a 3x3 kernel across the mask to return a new matrix where each cell contains the number
    # of positive neighbours it has
    signal.convolve2d(mask, kernel, mode="same")


num_runs = 200
duration = timeit.Timer(partial(denoise, motion_mask, kernel), timer=time.perf_counter_ns).timeit(
    number=num_runs
)
avg_duration = int((duration / num_runs) / 1_000)
print(f"On average it took {avg_duration}μs")

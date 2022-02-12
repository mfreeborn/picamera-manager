import asyncio
import concurrent.futures
import functools
import sys

_PROCESS_POOL = concurrent.futures.ProcessPoolExecutor()


def run_in_background_thread(fn):
    """Decorate a blocking io-bound function and convert it to a non-blocking function.

    When applied to a non-async function, this decorater schedules the function
    to run in the current event loop's thread pool executor in a non-blocking fashion.
    """

    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        return asyncio.get_running_loop().run_in_executor(
            None, functools.partial(fn, *args, **kwargs)
        )

    return wrapped


def run_in_background_process(fn):
    """Decorate a blocking cpu-bound function and convert it to a non-blocking function.

    When applied to a non-async function, this decorater schedules the function
    to run in the current event loop's process pool executor in a non-blocking fashion.
    """

    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        return asyncio.get_running_loop().run_in_executor(
            _PROCESS_POOL, functools.partial(fn, *args, **kwargs)
        )

    return wrapped

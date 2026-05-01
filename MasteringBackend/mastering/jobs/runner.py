from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock
from typing import Any


class JobQueueFullError(RuntimeError):
    pass


class JobReservation:
    def __init__(self, runner: "LocalJobRunner") -> None:
        self._runner = runner
        self._used = False

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future:
        if self._used:
            raise RuntimeError("Job reservation has already been used")
        self._used = True
        future = self._runner._executor.submit(fn, *args, **kwargs)
        future.add_done_callback(lambda _: self._runner._release_slot())
        return future

    def release(self) -> None:
        if self._used:
            return
        self._used = True
        self._runner._release_slot()


class LocalJobRunner:
    def __init__(self, max_workers: int = 1, max_queued_jobs: int = 2) -> None:
        self.max_workers = max_workers
        self.max_queued_jobs = max_queued_jobs
        self._in_flight = 0
        self._lock = Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future:
        return self.reserve().submit(fn, *args, **kwargs)

    def reserve(self) -> JobReservation:
        self._reserve_slot()
        return JobReservation(self)

    def ensure_capacity(self) -> None:
        with self._lock:
            if self._in_flight >= self.capacity:
                raise JobQueueFullError("Processing queue is full. Please try again later.")

    def shutdown(self, wait: bool = False) -> None:
        self._executor.shutdown(wait=wait)

    @property
    def capacity(self) -> int:
        return self.max_workers + self.max_queued_jobs

    @property
    def in_flight(self) -> int:
        with self._lock:
            return self._in_flight

    @property
    def available_slots(self) -> int:
        return max(0, self.capacity - self.in_flight)

    def _release_slot(self) -> None:
        with self._lock:
            self._in_flight = max(0, self._in_flight - 1)

    def _reserve_slot(self) -> None:
        with self._lock:
            if self._in_flight >= self.capacity:
                raise JobQueueFullError("Processing queue is full. Please try again later.")
            self._in_flight += 1

# -*- coding: utf-8 -*-
"""
maya_faceit.utils.threading
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Threading utilities for background processing.
"""

import threading
import queue
from typing import Callable, List, Any, Optional, Iterator
from concurrent.futures import ThreadPoolExecutor, Future


class ThreadPool:
    """
    Simple thread pool for parallel execution.
    """

    def __init__(self, max_workers: Optional[int] = None):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._futures: List[Future] = []

    def submit(self, func: Callable, *args, **kwargs) -> Future:
        """Submit a task to the pool."""
        future = self.executor.submit(func, *args, **kwargs)
        self._futures.append(future)
        return future

    def wait(self, timeout: Optional[float] = None) -> List[Any]:
        """Wait for all tasks to complete and return results."""
        results = []
        for f in self._futures:
            try:
                results.append(f.result(timeout))
            except Exception as e:
                results.append(e)
        self._futures.clear()
        return results

    def shutdown(self, wait: bool = True):
        """Shutdown the thread pool."""
        self.executor.shutdown(wait=wait)


class AsyncWorker:
    """
    Async worker using a background thread with a queue.
    """

    def __init__(self):
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._running = False
        self._results: List[Any] = []

    def start(self):
        """Start the worker thread."""
        if not self._running:
            self._running = True
            self._thread.start()

    def stop(self, wait: bool = True):
        """Stop the worker thread."""
        self._running = False
        if wait:
            self._thread.join()

    def submit(self, func: Callable, *args, **kwargs):
        """Submit a task to the queue."""
        self._queue.put((func, args, kwargs))

    def _run(self):
        while self._running:
            try:
                func, args, kwargs = self._queue.get(timeout=0.1)
                result = func(*args, **kwargs)
                self._results.append(result)
            except queue.Empty:
                continue
            except Exception as e:
                self._results.append(e)

    def get_results(self) -> List[Any]:
        """Get results from completed tasks."""
        results = self._results
        self._results = []
        return results
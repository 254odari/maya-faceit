# -*- coding: utf-8 -*-
"""
maya_faceit.utils.decorators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Decorators for common patterns: timing, logging, retry, singleton.
"""

import functools
import time
import logging
from typing import Callable, Any, Type, Optional

logger = logging.getLogger("maya_faceit")


def timer(func: Callable) -> Callable:
    """Time the execution of a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = (time.time() - start) * 1000
        logger.debug(f"{func.__name__} took {elapsed:.2f} ms")
        return result
    return wrapper


def timeit(func: Callable) -> Callable:
    """Alias for timer."""
    return timer(func)


def debug_log(func: Callable) -> Callable:
    """Log entry and exit of a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Entering {func.__name__}")
        result = func(*args, **kwargs)
        logger.debug(f"Exiting {func.__name__}")
        return result
    return wrapper


def retry(max_attempts: int = 3, delay: float = 0.5, exceptions: tuple = (Exception,)) -> Callable:
    """Retry a function on exceptions."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay * (attempt + 1))
            return None
        return wrapper
    return decorator


def deprecated(reason: str = "") -> Callable:
    """Mark a function as deprecated."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            msg = f"{func.__name__} is deprecated"
            if reason:
                msg += f": {reason}"
            logger.warning(msg)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def singleton(cls: Type) -> Type:
    """Convert a class to a singleton."""
    instances = {}

    @functools.wraps(cls)
    def wrapper(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return wrapper
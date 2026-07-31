import functools
import logging
import time
from contextlib import contextmanager
from typing import Any, Callable, Iterator, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


@contextmanager
def log_duration(logger: logging.Logger, event: str, level: int = logging.INFO, **fields: Any) -> Iterator[None]:
    """Time a block and log its duration as a numeric duration_ms field.

    On success, logs `event` at `level`. On exception, logs `f"{event}_failed"`
    at ERROR with the traceback attached, then re-raises unchanged.
    """
    start = time.perf_counter()
    try:
        yield
    except Exception:
        logger.error(
            f"{event}_failed",
            extra={"event": f"{event}_failed", "duration_ms": elapsed_ms(start), **fields},
            exc_info=True,
        )
        raise
    else:
        logger.log(
            level,
            event,
            extra={"event": event, "duration_ms": elapsed_ms(start), **fields},
        )


def timed(logger: logging.Logger, event: str, **static_fields: Any) -> Callable[[F], F]:
    """Decorator form of log_duration, for wrapping a whole function call."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with log_duration(logger, event, **static_fields):
                return func(*args, **kwargs)

        return wrapper

    return decorator

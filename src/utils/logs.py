from __future__ import annotations

import logging
import logging.config
from collections.abc import MutableMapping
from typing import Any, TypeAlias

import structlog
import uvicorn

from src.config import app_config

EventDict: TypeAlias = MutableMapping[str, Any]

LOG_LEVEL = "DEBUG" if app_config.debug else str(app_config.LOG_LEVEL)


def remove_color_message(_, __, event_dict: EventDict) -> EventDict:
    event_dict.pop("color_message", None)
    return event_dict


_SHARED_PROCESSORS: tuple[structlog.typing.Processor, ...] = (
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    # Add extra attributes of LogRecord objects to the event dictionary
    # so that values passed in the extra parameter of log methods pass
    # through to log output.
    structlog.stdlib.ExtraAdder(),
    # Add a timestamp in ISO 8601 format.
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    remove_color_message,
)

LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            # Render the final event dict as JSON.
            "processor": structlog.processors.JSONRenderer(),
            "foreign_pre_chain": _SHARED_PROCESSORS,
        },
        "colored": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                remove_color_message,
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            "foreign_pre_chain": _SHARED_PROCESSORS,
        },
        **uvicorn.config.LOGGING_CONFIG["formatters"],
    },
    "handlers": {
        "default": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "json" if not app_config.debug else "colored",
        },
    },
    "loggers": {
        "": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": True,
        },
        "uvicorn.error": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


def configure_logging() -> None:
    logging.config.dictConfig(LOGGING_CONFIG)
    # noinspection PyTypeChecker
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *_SHARED_PROCESSORS,
            structlog.stdlib.PositionalArgumentsFormatter(),
            # If the "stack_info" key in the event dict is true, remove it and
            # render the current stack trace in the "stack" key.
            structlog.processors.StackInfoRenderer(),
            # If the "exc_info" key in the event dict is either true or a
            # sys.exc_info() tuple, remove "exc_info" and render the exception
            # with traceback into the "exception" key.
            structlog.processors.format_exc_info,
            # If some value is in bytes, decode it to a unicode str.
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        # `wrapper_class` is the bound logger that you get back from
        # get_logger(). This one imitates the API of `logging.Logger`.
        wrapper_class=structlog.stdlib.BoundLogger,
        # `logger_factory` is used to create wrapped loggers that are used for OUTPUT.
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Effectively freeze configuration after creating the first bound logger.
        cache_logger_on_first_use=True,
    )

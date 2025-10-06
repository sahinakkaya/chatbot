import logging
from contextvars import ContextVar
from logging.config import dictConfig

# List of packages to configure logging for
packages = ["websocket_server", "kafka", "uvicorn"]

# Context variable for correlation ID in non-ASGI services
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")


class CorrelationIdFilter(logging.Filter):
    """Custom filter for non-ASGI services to inject correlation_id from context"""

    def filter(self, record):
        record.correlation_id = correlation_id_var.get()
        return True


def setup_logger(settings, use_asgi_correlation_id=True):
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "correlation_id": {
                    "()": "asgi_correlation_id.CorrelationIdFilter",
                    "uuid_length": 16,
                    "default_value": "-",
                } if use_asgi_correlation_id else {"()": "logger.CorrelationIdFilter"}
            },
            "formatters": {
                "console": {
                    "class": "logging.Formatter",
                    "datefmt": "%H:%M:%S",
                    "format": "[%(correlation_id)s] %(name)s:%(lineno)d - %(message)s",
                },
                "file": {
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    # "datefmt": "%Y-%m-%d %H:%M:%S",
                    # "format": "%(asctime)s.%(msecs)03dZ %(levelname) [%(correlation_id)s] %(name)s:%(lineno)d %(message)s",  # NOQA E501
                    # "class": "logging.Formatter",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                    "format": f"%(asctime)s.%(msecs)03dZ [%(correlation_id)s] %(levelname)s %(name)s:%(lineno)d - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "class": "rich.logging.RichHandler",
                    "formatter": "console",
                    "level": "DEBUG",
                    "filters": ["correlation_id"],
                },
                "rotating_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "file",
                    "level": "DEBUG",
                    "filename": f"{settings.log_folder}/{settings.app_name}.log",
                    "maxBytes": 1024 * 1024,
                    "backupCount": 3,
                    "encoding": "utf8",
                    "filters": ["correlation_id"],
                },
            },
            # use the root logger to catch all logs
            "root": {
                "handlers": ["default", "rotating_file"],
                "level": settings.log_level,
                "propagate": False,
            },
            # "loggers": {
            #     **{
            #         package: {
            #             "handlers": ["default", "rotating_file"],
            #             "level": settings.log_level,
            #             "propagate": False,
            #         }
            #         for package in packages
            #     },
            # },
        }
    )

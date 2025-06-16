"""Logging configuration for Uvicorn - Container Manager compatible"""
import logging
from typing import Dict, Any


def get_uvicorn_log_config() -> Dict[str, Any]:
    """Get logging configuration for Uvicorn - optimized for Container Manager
    
    This configuration ensures all logs are sent to stdout without any filtering,
    making them visible in Synology Container Manager and other container platforms.
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(process)d] [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S %z"
            },
            "access": {
                "format": "%(asctime)s [%(process)d] [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S %z"
            }
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout"
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout"
            }
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": True  # Allow propagation for container managers
            },
            "uvicorn.access": {
                "handlers": ["access"],
                "level": "INFO",
                "propagate": True  # Allow propagation for container managers
            },
            "uvicorn.error": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": True  # Allow propagation for container managers
            }
        }
    }
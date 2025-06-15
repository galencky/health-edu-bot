"""Logging configuration for Uvicorn - Container Manager compatible"""
import logging
import os
from typing import Dict, Any

class HealthCheckFilter(logging.Filter):
    """Filter out health check logs (HEAD / and GET /) - only when FILTER_HEALTH_CHECKS=true"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Only filter if explicitly enabled via environment variable
        if not os.getenv("FILTER_HEALTH_CHECKS", "false").lower() == "true":
            return True  # Don't filter anything by default
        
        # Check if this is an access log
        if hasattr(record, 'args') and record.args:
            # Uvicorn access logs have args like: ('127.0.0.1:56789', 'HEAD', '/', 'HTTP/1.1', 200)
            if len(record.args) >= 3:
                method = record.args[1]
                path = record.args[2]
                # Filter out health check requests
                if path == "/" and method in ["HEAD", "GET"]:
                    return False
        
        # Also check the message directly for health check patterns
        try:
            message = record.getMessage()
        except (TypeError, ValueError):
            # If getMessage() fails, try to get the raw message
            message = str(record.msg)
        
        if any(pattern in message for pattern in [
            "HEAD / HTTP/1.1",
            "GET / HTTP/1.1\" 200",
            "HEAD / HTTP/1.1\" 200",
            "GET /ping HTTP/1.1\" 200",
            "HEAD /ping HTTP/1.1\" 200"
        ]):
            return False
        
        # Keep all other logs
        return True


def get_uvicorn_log_config() -> Dict[str, Any]:
    """Get logging configuration for Uvicorn - optimized for Container Manager"""
    # Check if we should use container-friendly logging
    container_mode = os.getenv("CONTAINER_LOGGING", "true").lower() == "true"
    
    if container_mode:
        # Simple configuration for container environments
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
    else:
        # Original configuration with filtering for local development
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S"
                },
                "access": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S"
                }
            },
            "filters": {
                "health_check_filter": {
                    "()": "utils.uvicorn_logging.HealthCheckFilter"
                }
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "filters": ["health_check_filter"]
                },
                "access": {
                    "formatter": "access",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "filters": ["health_check_filter"]
                }
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["default"],
                    "level": "INFO",
                    "propagate": False
                },
                "uvicorn.access": {
                    "handlers": ["access"],
                    "level": "INFO",
                    "propagate": False
                },
                "uvicorn.error": {
                    "handlers": ["default"],
                    "level": "INFO",
                    "propagate": False
                }
            }
        }
"""Custom logging configuration for Uvicorn to suppress health check logs"""
import logging
from typing import Dict, Any

class HealthCheckFilter(logging.Filter):
    """Filter out health check logs (HEAD / and GET /)"""
    
    def filter(self, record: logging.LogRecord) -> bool:
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
    """Get custom logging configuration for Uvicorn"""
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
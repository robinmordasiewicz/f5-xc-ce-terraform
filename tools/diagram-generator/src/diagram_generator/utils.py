"""
Utility functions and logging configuration.

Provides structured logging, retry logic, and common helper functions.
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, TypeVar

import structlog
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from diagram_generator.exceptions import DiagramGeneratorError

# Type variable for generic function decoration
F = TypeVar("F", bound=Callable[..., Any])


def configure_logging(verbose: bool = False) -> None:
    """
    Configure structured logging for the application.

    Args:
        verbose: Enable debug-level logging if True
    """
    log_level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        format="%(message)s",
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structured logger
    """
    return structlog.get_logger(name)


def create_http_session_with_retries(
    retries: int = 3,
    backoff_factor: float = 0.3,
    status_forcelist: tuple[int, ...] = (500, 502, 503, 504),
) -> Any:
    """
    Create requests Session with automatic retry logic.

    Args:
        retries: Number of retry attempts
        backoff_factor: Backoff multiplier for retries
        status_forcelist: HTTP status codes to retry on

    Returns:
        Configured requests Session
    """
    import requests

    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST", "PUT"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def retry_on_exception(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """
    Decorator to retry function calls on specified exceptions.

    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay on each retry
        exceptions: Tuple of exception types to catch and retry

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt_delay = delay
            logger = get_logger(func.__module__)

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(
                            "Function failed after max attempts",
                            function=func.__name__,
                            attempts=max_attempts,
                            error=str(e),
                        )
                        raise

                    logger.warning(
                        "Function failed, retrying",
                        function=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay=attempt_delay,
                        error=str(e),
                    )
                    time.sleep(attempt_delay)
                    attempt_delay *= backoff

            raise DiagramGeneratorError(f"Unexpected state in retry logic for {func.__name__}")

        return wrapper  # type: ignore

    return decorator


def sanitize_resource_id(resource_id: str) -> str:
    """
    Sanitize resource ID for use as node ID in graphs.

    Replaces characters that might cause issues in graph processing or diagram rendering.

    Args:
        resource_id: Original resource ID

    Returns:
        Sanitized resource ID safe for use as node identifier
    """
    return resource_id.replace(".", "_").replace("[", "_").replace("]", "_").replace("/", "_")


def get_resource_short_name(resource: Any) -> str:
    """
    Get a short, human-readable name for a resource.

    Args:
        resource: Resource object (TerraformResource, AzureResource, or F5XCResource)

    Returns:
        Short name for display
    """
    if hasattr(resource, "name"):
        return resource.name
    if hasattr(resource, "address"):
        # For Terraform resources, extract name from address
        parts = resource.address.split(".")
        return parts[-1] if parts else "unknown"
    return "unknown"


def format_resource_label(source: str, resource_type: str, name: str, max_length: int = 40) -> str:
    """
    Format resource label for diagram display.

    Args:
        source: Resource source (terraform, azure, f5xc)
        resource_type: Type of resource
        name: Resource name
        max_length: Maximum label length

    Returns:
        Formatted label string
    """
    label = f"{source.upper()}\n{resource_type}\n{name}"

    if len(label) > max_length:
        # Truncate name if too long
        available_length = max_length - len(source) - len(resource_type) - 4
        truncated_name = name[:available_length] + "..." if len(name) > available_length else name
        label = f"{source.upper()}\n{resource_type}\n{truncated_name}"

    return label


def extract_ip_addresses(resource_dict: dict[str, Any]) -> list[str]:
    """
    Extract IP addresses from resource properties.

    Recursively searches for IP-like values in nested dictionaries.

    Args:
        resource_dict: Resource properties dictionary

    Returns:
        List of found IP addresses
    """
    import re

    ip_pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    ips: list[str] = []

    def search_dict(d: dict[str, Any]) -> None:
        for _key, value in d.items():
            if isinstance(value, str):
                matches = ip_pattern.findall(value)
                ips.extend(matches)
            elif isinstance(value, dict):
                search_dict(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        search_dict(item)
                    elif isinstance(item, str):
                        matches = ip_pattern.findall(item)
                        ips.extend(matches)

    search_dict(resource_dict)
    return list(set(ips))  # Remove duplicates

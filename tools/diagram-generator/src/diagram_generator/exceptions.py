"""
Custom exceptions for the diagram generator.

Provides specific exception types for different error scenarios to enable
better error handling and debugging.
"""


class DiagramGeneratorError(Exception):
    """Base exception for all diagram generator errors."""

    pass


class ConfigurationError(DiagramGeneratorError):
    """Configuration validation or loading error."""

    pass


class AuthenticationError(DiagramGeneratorError):
    """Authentication failure with external services."""

    pass


class TerraformStateError(DiagramGeneratorError):
    """Error parsing or accessing Terraform state."""

    pass


class AzureAPIError(DiagramGeneratorError):
    """Error communicating with Azure APIs."""

    pass


class F5XCAPIError(DiagramGeneratorError):
    """Error communicating with F5 Distributed Cloud API."""

    pass


class LucidAPIError(DiagramGeneratorError):
    """Error communicating with Lucidchart API."""

    pass


class CorrelationError(DiagramGeneratorError):
    """Error during resource correlation process."""

    pass


class DiagramGenerationError(DiagramGeneratorError):
    """Error during diagram generation or upload."""

    pass

"""
Data models for infrastructure resources and configuration.

This module defines Pydantic models for type-safe data handling and validation
across Terraform, Azure, and F5 XC resources.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class ResourceSource(str, Enum):
    """Source system for infrastructure resources."""

    TERRAFORM = "terraform"
    AZURE = "azure"
    F5XC = "f5xc"


class RelationshipType(str, Enum):
    """Type of relationship between resources."""

    TERRAFORM_DEPENDENCY = "terraform_dependency"
    TERRAFORM_AZURE = "terraform_azure"
    F5XC_ORIGIN_TO_AZURE_VM = "f5xc_origin_to_azure_vm"
    F5XC_SITE_TO_AZURE_VNET = "f5xc_site_to_azure_vnet"
    GENERIC_DEPENDENCY = "generic_dependency"


class TerraformResource(BaseModel):
    """Terraform resource from state file."""

    model_config = ConfigDict(frozen=False)

    source: ResourceSource = Field(default=ResourceSource.TERRAFORM)
    type: str = Field(..., description="Terraform resource type (e.g., azurerm_virtual_network)")
    name: str = Field(..., description="Resource name")
    address: str = Field(..., description="Full Terraform address")
    values: Dict[str, Any] = Field(default_factory=dict, description="Resource attributes")
    depends_on: List[str] = Field(default_factory=list, description="Terraform dependencies")


class AzureResource(BaseModel):
    """Azure resource from Resource Graph."""

    model_config = ConfigDict(frozen=False)

    source: ResourceSource = Field(default=ResourceSource.AZURE)
    id: str = Field(..., description="Azure resource ID")
    name: str = Field(..., description="Resource name")
    type: str = Field(..., description="Azure resource type")
    location: str = Field(..., description="Azure region")
    resource_group: str = Field(..., description="Resource group name")
    tags: Dict[str, str] = Field(default_factory=dict)
    properties: Dict[str, Any] = Field(default_factory=dict)


class F5XCResource(BaseModel):
    """F5 Distributed Cloud resource from REST API."""

    model_config = ConfigDict(frozen=False)

    source: ResourceSource = Field(default=ResourceSource.F5XC)
    type: str = Field(
        ...,
        description="F5 XC resource type (e.g., http_loadbalancer, origin_pool, virtual_site)",
    )
    namespace: str = Field(..., description="F5 XC namespace")
    name: str = Field(..., description="Resource name")
    spec: Dict[str, Any] = Field(default_factory=dict, description="Resource specification")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Resource metadata")


class ResourceRelationship(BaseModel):
    """Relationship between two resources."""

    source_id: str = Field(..., description="Source resource identifier")
    target_id: str = Field(..., description="Target resource identifier")
    relationship_type: RelationshipType
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConfigurationDrift(BaseModel):
    """Detected configuration drift between sources."""

    resource_address: str = Field(..., description="Resource identifier")
    drift_type: str = Field(..., description="Type of drift detected")
    terraform_value: Any = Field(None, description="Value in Terraform state")
    azure_value: Any = Field(None, description="Value in Azure")
    details: str = Field(..., description="Human-readable drift description")


class CorrelatedResources(BaseModel):
    """Result of cross-referencing multiple data sources."""

    resources: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[ResourceRelationship] = Field(default_factory=list)
    drift: List[ConfigurationDrift] = Field(default_factory=list)


class AzureAuthMethod(str, Enum):
    """Azure authentication methods."""

    AZURE_CLI = "azure_cli"
    SERVICE_PRINCIPAL = "service_principal"
    MANAGED_IDENTITY = "managed_identity"


class F5XCAuthMethod(str, Enum):
    """F5 XC authentication methods."""

    API_TOKEN = "api_token"
    P12_CERTIFICATE = "p12_certificate"


class DiagramConfig(BaseModel):
    """Configuration for diagram generation."""

    model_config = ConfigDict(validate_assignment=True, use_enum_values=False)

    # Terraform configuration
    terraform_state_path: Optional[str] = Field(
        None, description="Path to Terraform state (uses current directory if not specified)"
    )

    # Azure configuration
    azure_subscription_id: str = Field(..., description="Azure subscription ID")
    azure_auth_method: AzureAuthMethod = Field(
        default=AzureAuthMethod.AZURE_CLI, description="Azure authentication method"
    )

    # F5 XC configuration
    f5xc_tenant: str = Field(..., description="F5 XC tenant name")
    f5xc_auth_method: F5XCAuthMethod = Field(
        default=F5XCAuthMethod.API_TOKEN, description="F5 XC authentication method"
    )
    f5xc_api_token: Optional[str] = Field(None, description="F5 XC API token")
    f5xc_p12_cert_path: Optional[str] = Field(None, description="Path to P12 certificate")
    f5xc_p12_password: Optional[str] = Field(None, description="P12 certificate password")

    # Lucidchart configuration
    lucid_client_id: str = Field(..., description="Lucidchart OAuth client ID")
    lucid_client_secret: str = Field(..., description="Lucidchart OAuth client secret")
    lucid_redirect_uri: HttpUrl = Field(
        default="http://localhost:8080/callback", description="OAuth redirect URI"
    )
    lucid_access_token: Optional[str] = Field(None, description="Pre-obtained access token")

    # Diagram settings
    diagram_title: str = Field(default="Azure + F5 XC Infrastructure", description="Diagram title")
    auto_layout: bool = Field(default=True, description="Enable automatic layout")
    group_by_platform: bool = Field(default=True, description="Group resources by platform")
    group_by_resource_group: bool = Field(default=True, description="Group by Azure RG")
    group_by_namespace: bool = Field(default=True, description="Group by F5 XC namespace")

    # Correlation settings
    enable_drift_detection: bool = Field(default=True, description="Detect configuration drift")
    match_by_tags: bool = Field(default=True, description="Correlate using tags/labels")
    match_by_ip: bool = Field(default=True, description="Correlate using IP addresses")

    @field_validator("f5xc_api_token", "f5xc_p12_cert_path")
    @classmethod
    def validate_f5xc_auth(cls, v: Optional[str], info: Any) -> Optional[str]:
        """Validate F5 XC authentication configuration."""
        values = info.data
        auth_method = values.get("f5xc_auth_method")

        if auth_method == F5XCAuthMethod.API_TOKEN and info.field_name == "f5xc_api_token":
            if not v:
                raise ValueError("f5xc_api_token required when using API_TOKEN auth method")
        elif (
            auth_method == F5XCAuthMethod.P12_CERTIFICATE
            and info.field_name == "f5xc_p12_cert_path"
        ):
            if not v:
                raise ValueError(
                    "f5xc_p12_cert_path required when using P12_CERTIFICATE auth method"
                )

        return v


class LucidShape(BaseModel):
    """Lucidchart shape definition."""

    id: str
    shape_type: str
    bounding_box: Dict[str, float]
    text: str
    fill_color: str
    stroke_color: str = "#000000"


class LucidLine(BaseModel):
    """Lucidchart line (connector) definition."""

    id: str
    source_shape_id: str
    target_shape_id: str
    stroke_color: str
    stroke_width: int = 2
    label: Optional[str] = None


class LucidDocument(BaseModel):
    """Lucidchart document structure."""

    document_id: Optional[str] = None
    title: str
    pages: List[Dict[str, Any]] = Field(default_factory=list)
    url: Optional[HttpUrl] = None

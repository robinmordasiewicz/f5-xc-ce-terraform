"""
Azure Architecture Icons integration module.

Maps Azure resource types to official Microsoft icons and provides
SVG-to-mxGraph conversion for Draw.io diagrams.
"""

import base64
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from diagram_generator.utils import get_logger

logger = get_logger(__name__)

# Path to Azure icons relative to package root
ICONS_BASE_PATH = (
    Path(__file__).parent.parent.parent
    / "assets"
    / "azure-icons"
    / "Azure_Public_Service_Icons"
    / "Icons"
)

# Azure resource type to icon file mapping
# Maps our internal resource types to official Azure icon filenames
AZURE_ICON_MAP = {
    # Virtual Machines and Compute
    "virtual_machine": "compute/10021-icon-service-Virtual-Machine.svg",
    "vm": "compute/10021-icon-service-Virtual-Machine.svg",
    "availabilit_set": "compute/10023-icon-service-Availability-Sets.svg",
    # Networking
    "virtual_network": "networking/10061-icon-service-Virtual-Networks.svg",
    "vnet": "networking/10061-icon-service-Virtual-Networks.svg",
    "subnet": "networking/10061-icon-service-Virtual-Networks.svg",  # Use VNet icon for subnets
    "load_balancer": "networking/10062-icon-service-Load-Balancers.svg",
    "lb": "networking/10062-icon-service-Load-Balancers.svg",
    "network_interface": "networking/10080-icon-service-Network-Interfaces.svg",
    "nic": "networking/10080-icon-service-Network-Interfaces.svg",
    "public_ip": "networking/10069-icon-service-Public-IP-Addresses.svg",
    "nsg": "networking/10067-icon-service-Network-Security-Groups.svg",
    "network_security_group": "networking/10067-icon-service-Network-Security-Groups.svg",
    "route_table": "networking/10071-icon-service-Route-Tables.svg",
    "virtual_network_gateway": "networking/10063-icon-service-Virtual-Network-Gateways.svg",
    "application_gateway": "networking/10076-icon-service-Application-Gateways.svg",
    # Resource Groups
    "resource_group": "general/10007-icon-service-Resource-Groups.svg",
    # F5 XC - using generic cloud/networking icons
    "f5xc_ce": "compute/10132-icon-service-VM-Scale-Sets.svg",  # Use VM scale set for multi-node
    "f5xc_site": "general/00001-icon-service-Cloud.svg",  # Generic cloud for F5 XC sites
    "f5xc_lb": "networking/10076-icon-service-Application-Gateways.svg",  # App gateway for F5 XC LB
}


class AzureIconConverter:
    """Converts Azure SVG icons to Draw.io mxGraph format."""

    def __init__(self, icons_path: Optional[Path] = None):
        """
        Initialize icon converter.

        Args:
            icons_path: Path to Azure icons directory (defaults to bundled icons)
        """
        self.icons_path = icons_path or ICONS_BASE_PATH

        if not self.icons_path.exists():
            logger.warning(
                "Azure icons not found",
                path=str(self.icons_path),
                message="Icons will be downloaded on first use",
            )

    def get_icon_path(self, resource_type: str) -> Optional[Path]:
        """
        Get path to icon file for resource type.

        Args:
            resource_type: Azure resource type (e.g., 'virtual_machine', 'load_balancer')

        Returns:
            Path to SVG icon file, or None if not found
        """
        # Normalize resource type
        resource_type = resource_type.lower().replace("-", "_").replace(" ", "_")

        # Look up icon mapping
        icon_file = AZURE_ICON_MAP.get(resource_type)
        if not icon_file:
            logger.debug(f"No icon mapping for resource type: {resource_type}")
            return None

        icon_path = self.icons_path / icon_file
        if not icon_path.exists():
            logger.warning(f"Icon file not found: {icon_path}")
            return None

        return icon_path

    def svg_to_base64_data_uri(self, svg_path: Path) -> str:
        """
        Convert SVG file to base64 data URI for embedding.

        Args:
            svg_path: Path to SVG file

        Returns:
            Base64-encoded data URI string
        """
        with open(svg_path, "rb") as f:
            svg_data = f.read()

        # Base64 encode
        b64_data = base64.b64encode(svg_data).decode("utf-8")

        return f"data:image/svg+xml;base64,{b64_data}"

    def extract_svg_dimensions(self, svg_path: Path) -> tuple[float, float]:
        """
        Extract width and height from SVG file.

        Args:
            svg_path: Path to SVG file

        Returns:
            Tuple of (width, height) in pixels
        """
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()

            # Try to get width/height attributes
            width = root.get("width", "18")
            height = root.get("height", "18")

            # Remove units (px, pt, etc.) and convert to float
            width = float(re.sub(r"[^\d.]", "", str(width)))
            height = float(re.sub(r"[^\d.]", "", str(height)))

            return (width, height)

        except Exception as e:
            logger.warning(f"Failed to extract SVG dimensions: {e}")
            return (18, 18)  # Default Azure icon size

    def create_icon_shape_style(self, svg_path: Path, base_style: Optional[str] = None) -> str:
        """
        Create Draw.io shape style string with embedded SVG icon.

        Args:
            svg_path: Path to SVG icon file
            base_style: Optional base style string to extend

        Returns:
            Draw.io style string with icon embedded
        """
        data_uri = self.svg_to_base64_data_uri(svg_path)
        width, height = self.extract_svg_dimensions(svg_path)

        # Default style if none provided
        if not base_style:
            base_style = "rounded=0;whiteSpace=wrap;html=1"

        # Add image shape with SVG
        icon_style = f"{base_style};shape=image;verticalLabelPosition=bottom;labelBackgroundColor=default;verticalAlign=top;aspect=fixed;imageAspect=0;image={data_uri}"

        return icon_style

    def get_icon_for_resource(
        self, resource_type: str, base_style: Optional[str] = None
    ) -> Optional[dict[str, any]]:
        """
        Get icon data for Azure resource type.

        Args:
            resource_type: Azure resource type
            base_style: Optional base Draw.io style string

        Returns:
            Dictionary with 'style' and 'dimensions' keys, or None if icon not available
        """
        icon_path = self.get_icon_path(resource_type)
        if not icon_path:
            return None

        style = self.create_icon_shape_style(icon_path, base_style)
        width, height = self.extract_svg_dimensions(icon_path)

        return {
            "style": style,
            "dimensions": {"width": width, "height": height},
            "icon_path": str(icon_path),
        }


def get_azure_icon_converter() -> AzureIconConverter:
    """
    Get singleton instance of Azure icon converter.

    Returns:
        AzureIconConverter instance
    """
    if not hasattr(get_azure_icon_converter, "_instance"):
        get_azure_icon_converter._instance = AzureIconConverter()

    return get_azure_icon_converter._instance

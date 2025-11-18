"""
Azure Shape Library integration for Draw.io diagrams.

Loads Azure icons from mxlibrary format (yaegashi/icon-collection-mxlibrary)
and provides shape references for use in diagrams.
"""

import base64
import json
import zlib
from pathlib import Path
from typing import Optional

from diagram_generator.utils import get_logger

logger = get_logger(__name__)

# Path to Azure shape library
SHAPE_LIBRARY_PATH = Path(__file__).parent.parent.parent / "assets" / "azure-icons.mxlibrary"

# Azure resource type to shape library title mapping
# Maps our internal resource types to exact icon titles in the Azure shape library
AZURE_SHAPE_MAP = {
    # Compute
    "virtual_machine": "Virtual Machine",
    "vm": "Virtual Machine",
    "virtualmachines": "Virtual Machine",
    "availabilit_set": "Availability Sets",
    # Networking
    "virtual_network": "Virtual Networks",
    "vnet": "Virtual Networks",
    "virtualnetworks": "Virtual Networks",
    "subnet": "Virtual Networks",  # Use VNet icon for subnets
    "load_balancer": "Load Balancers",
    "lb": "Load Balancers",
    "loadbalancers": "Load Balancers",
    "network_interface": "Network Interfaces",
    "nic": "Network Interfaces",
    "networkinterfaces": "Network Interfaces",
    "public_ip": "Public IP Addresses",
    "publicipaddresses": "Public IP Addresses",
    "nsg": "Network Security Groups",
    "network_security_group": "Network Security Groups",
    "networksecuritygroups": "Network Security Groups",
    "route_table": "Route Tables",
    "routetables": "Route Tables",
    "virtual_network_gateway": "Virtual Network Gateways",
    "application_gateway": "Application Gateways",
    # Resource Groups
    "resource_group": "Resource Groups",
    "resourcegroups": "Resource Groups",
}


class AzureShapeLibrary:
    """Manages Azure shape library for Draw.io diagrams."""

    def __init__(self, library_path: Optional[Path] = None):
        """
        Initialize Azure shape library.

        Args:
            library_path: Path to mxlibrary file (defaults to bundled library)
        """
        self.library_path = library_path or SHAPE_LIBRARY_PATH
        self._shapes: dict[str, dict] = {}
        self._load_library()

    def _load_library(self) -> None:
        """Load shapes from mxlibrary file."""
        if not self.library_path.exists():
            logger.warning(
                "Azure shape library not found",
                path=str(self.library_path),
                message="Icons will not be available",
            )
            return

        try:
            with open(self.library_path, encoding="utf-8") as f:
                content = f.read()

            # Extract JSON array from <mxlibrary>[...]</mxlibrary>
            start = content.find("[")
            end = content.rfind("]") + 1

            if start == -1 or end == 0:
                logger.error("Invalid mxlibrary format", path=str(self.library_path))
                return

            shapes_list = json.loads(content[start:end])

            # Index shapes by title for fast lookup
            for shape in shapes_list:
                title = shape.get("title", "")
                if title:
                    self._shapes[title] = shape

            logger.info(
                f"Loaded {len(self._shapes)} shapes from Azure library", path=str(self.library_path)
            )

        except Exception as e:
            logger.error(f"Failed to load Azure shape library: {e}", path=str(self.library_path))

    def get_shape(self, resource_type: str) -> Optional[dict]:
        """
        Get shape definition for Azure resource type.

        Args:
            resource_type: Azure resource type (e.g., 'virtual_machine', 'load_balancer')

        Returns:
            Dictionary with shape data (title, xml, w, h) or None if not found
        """
        # Normalize resource type
        resource_type = resource_type.lower().replace("-", "_").replace(" ", "_")

        # Look up shape title
        shape_title = AZURE_SHAPE_MAP.get(resource_type)
        if not shape_title:
            logger.debug(f"No shape mapping for resource type: {resource_type}")
            return None

        # Get shape from library
        shape = self._shapes.get(shape_title)
        if not shape:
            logger.debug(f"Shape not found in library: {shape_title}")
            return None

        return shape

    def decompress_shape_xml(self, compressed_xml: str) -> Optional[str]:
        """
        Decompress mxGraph XML from mxlibrary format.

        The mxlibrary format stores shapes as base64-encoded, deflate-compressed XML.

        Args:
            compressed_xml: Base64-encoded compressed XML string

        Returns:
            Decompressed XML string, or None if decompression fails
        """
        try:
            # Decode base64
            decoded = base64.b64decode(compressed_xml)

            # Decompress using deflate (zlib with -MAX_WBITS for raw deflate)
            decompressed = zlib.decompress(decoded, -zlib.MAX_WBITS)

            # Convert to string
            return decompressed.decode("utf-8")

        except Exception as e:
            logger.error(f"Failed to decompress shape XML: {e}")
            return None

    def get_shape_xml(self, resource_type: str) -> Optional[str]:
        """
        Get decompressed mxGraph XML for Azure resource type.

        This returns the full mxGraph cell XML that can be inserted
        directly into a diagram.

        Args:
            resource_type: Azure resource type (e.g., 'virtual_machine', 'load_balancer')

        Returns:
            Decompressed mxGraph XML string, or None if shape not found
        """
        shape = self.get_shape(resource_type)
        if not shape:
            return None

        compressed_xml = shape.get("xml")
        if not compressed_xml:
            logger.error(f"Shape has no XML data: {shape.get('title')}")
            return None

        return self.decompress_shape_xml(compressed_xml)


# Module-level singleton instance
_azure_shape_library_instance: AzureShapeLibrary | None = None


def get_azure_shape_library() -> AzureShapeLibrary:
    """
    Get singleton instance of Azure shape library.

    Returns:
        AzureShapeLibrary instance
    """
    global _azure_shape_library_instance
    if _azure_shape_library_instance is None:
        _azure_shape_library_instance = AzureShapeLibrary()

    return _azure_shape_library_instance

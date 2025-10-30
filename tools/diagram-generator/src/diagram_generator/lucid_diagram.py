"""
Lucidchart diagram generation and upload module.

Converts correlated resources into Lucidchart diagrams with layout and grouping.
"""

import uuid
from typing import Any

import requests

from diagram_generator.exceptions import DiagramGenerationError, LucidAPIError
from diagram_generator.lucid_auth import LucidAuthClient
from diagram_generator.models import (
    CorrelatedResources,
    LucidDocument,
    LucidLine,
    LucidShape,
    ResourceRelationship,
    ResourceSource,
)
from diagram_generator.utils import format_resource_label, get_logger, get_resource_short_name

logger = get_logger(__name__)


class LucidDiagramGenerator:
    """Generates and uploads Lucidchart diagrams from correlated resources."""

    LUCID_API_BASE = "https://api.lucid.co"

    # Shape colors by resource source
    SOURCE_COLORS = {
        ResourceSource.TERRAFORM: "#FF6B6B",  # Red
        ResourceSource.AZURE: "#4A90E2",  # Blue
        ResourceSource.F5XC: "#50C878",  # Green
    }

    # Relationship colors
    RELATIONSHIP_COLORS = {
        "terraform_dependency": "#FF6B6B",
        "terraform_azure": "#9B59B6",
        "f5xc_origin_to_azure_vm": "#3498DB",
        "f5xc_site_to_azure_vnet": "#1ABC9C",
        "generic_dependency": "#95A5A6",
    }

    def __init__(
        self,
        auth_client: LucidAuthClient,
        title: str = "Azure + F5 XC Infrastructure",
        auto_layout: bool = True,
        group_by_platform: bool = True,
    ):
        """
        Initialize Lucid diagram generator.

        Args:
            auth_client: Authenticated Lucidchart OAuth client
            title: Diagram title
            auto_layout: Enable automatic layout
            group_by_platform: Group resources by platform (Terraform/Azure/F5 XC)
        """
        self.auth_client = auth_client
        self.title = title
        self.auto_layout = auto_layout
        self.group_by_platform = group_by_platform
        self.session = requests.Session()

        logger.info(
            "Lucid diagram generator initialized",
            title=title,
            auto_layout=auto_layout,
        )

    def generate_and_upload(self, correlated_resources: CorrelatedResources) -> LucidDocument:
        """
        Generate diagram from correlated resources and upload to Lucidchart.

        Args:
            correlated_resources: Correlated infrastructure resources

        Returns:
            LucidDocument with document ID and URL

        Raises:
            DiagramGenerationError: If diagram generation fails
            LucidAPIError: If upload fails
        """
        logger.info(
            "Generating Lucid diagram",
            resource_count=len(correlated_resources.resources),
            relationship_count=len(correlated_resources.relationships),
        )

        try:
            # Generate shapes and lines
            shapes = self._generate_shapes(correlated_resources.resources)
            lines = self._generate_lines(correlated_resources.relationships, shapes)

            # Build document structure
            document_data = self._build_document_data(shapes, lines)

            # Upload to Lucidchart
            document = self._upload_document(document_data)

            logger.info("Diagram uploaded successfully", document_id=document.document_id)
            return document

        except Exception as e:
            logger.error("Diagram generation failed", error=str(e))
            raise DiagramGenerationError(f"Failed to generate diagram: {e}") from e

    def _generate_shapes(self, resources: list[dict[str, Any]]) -> dict[str, LucidShape]:
        """
        Generate Lucid shapes from resources.

        Args:
            resources: List of resource dictionaries

        Returns:
            Dictionary mapping resource IDs to LucidShape objects
        """
        shapes = {}
        x_offset = 100
        y_offset = 100
        shape_width = 150
        shape_height = 80
        x_spacing = 200
        y_spacing = 120

        # Group resources by source if enabled
        if self.group_by_platform:
            grouped = self._group_resources_by_source(resources)
        else:
            grouped = {"all": resources}

        group_index = 0

        for _group_name, group_resources in grouped.items():
            for i, resource in enumerate(group_resources):
                # Calculate position
                row = i // 5
                col = i % 5
                x = x_offset + (group_index * 1000) + (col * x_spacing)
                y = y_offset + (row * y_spacing)

                # Get resource details
                source = resource.get("source", "unknown")
                resource_type = resource.get("type", "unknown")
                name = get_resource_short_name(type("Resource", (), resource))

                # Create shape ID
                if source == "terraform":
                    shape_id = resource.get("address", str(uuid.uuid4()))
                elif source == "azure":
                    shape_id = resource.get("id", str(uuid.uuid4()))
                else:  # f5xc
                    namespace = resource.get("namespace", "")
                    shape_id = f"{namespace}/{resource_type}/{name}"

                # Generate label
                label = format_resource_label(source, resource_type, name)

                # Create shape
                shape = LucidShape(
                    id=shape_id,
                    shape_type="rectangle",
                    bounding_box={
                        "x": x,
                        "y": y,
                        "width": shape_width,
                        "height": shape_height,
                    },
                    text=label,
                    fill_color=self.SOURCE_COLORS.get(source, "#CCCCCC"),
                    stroke_color="#000000",
                )
                shapes[shape_id] = shape

            group_index += 1

        logger.info("Generated shapes", count=len(shapes))
        return shapes

    def _generate_lines(
        self,
        relationships: list[ResourceRelationship],
        shapes: dict[str, LucidShape],
    ) -> list[LucidLine]:
        """
        Generate Lucid connector lines from relationships.

        Args:
            relationships: List of ResourceRelationship objects
            shapes: Dictionary of shapes

        Returns:
            List of LucidLine objects
        """
        lines = []

        for relationship in relationships:
            source_id = relationship.source_id
            target_id = relationship.target_id
            rel_type = relationship.relationship_type

            # Skip if shapes don't exist
            if source_id not in shapes or target_id not in shapes:
                continue

            # Create line
            line = LucidLine(
                id=str(uuid.uuid4()),
                source_shape_id=source_id,
                target_shape_id=target_id,
                stroke_color=self.RELATIONSHIP_COLORS.get(rel_type, "#95A5A6"),
                stroke_width=2,
                label=rel_type.replace("_", " ").title(),
            )
            lines.append(line)

        logger.info("Generated connector lines", count=len(lines))
        return lines

    def _group_resources_by_source(self, resources: list[dict[str, Any]]) -> dict[str, list[dict]]:
        """
        Group resources by their source (terraform, azure, f5xc).

        Args:
            resources: List of resource dictionaries

        Returns:
            Dictionary mapping source to resources
        """
        groups: dict[str, list[Any]] = {
            "terraform": [],
            "azure": [],
            "f5xc": [],
        }

        for resource in resources:
            source = resource.get("source", "unknown")
            if source in groups:
                groups[source].append(resource)

        return groups

    def _build_document_data(
        self, shapes: dict[str, LucidShape], lines: list[LucidLine]
    ) -> dict[str, Any]:
        """
        Build Lucidchart document data structure.

        Args:
            shapes: Dictionary of shapes
            lines: List of connector lines

        Returns:
            Document data for API upload
        """
        # Convert shapes to API format
        shape_objects = []
        for shape in shapes.values():
            shape_obj = {
                "id": shape.id,
                "type": "shape",
                "boundingBox": shape.bounding_box,
                "style": {
                    "fill": shape.fill_color,
                    "stroke": shape.stroke_color,
                },
                "text": {
                    "text": shape.text,
                },
            }
            shape_objects.append(shape_obj)

        # Convert lines to API format
        line_objects = []
        for line in lines:
            line_obj = {
                "id": line.id,
                "type": "line",
                "endpoint1": {"id": line.source_shape_id},
                "endpoint2": {"id": line.target_shape_id},
                "style": {
                    "stroke": line.stroke_color,
                    "strokeWidth": line.stroke_width,
                },
            }
            if line.label:
                line_obj["text"] = {"text": line.label}
            line_objects.append(line_obj)

        # Build page
        page = {
            "id": str(uuid.uuid4()),
            "title": "Infrastructure",
            "objects": shape_objects + line_objects,
        }

        # Build document
        document_data: dict[str, Any] = {
            "title": self.title,
            "pages": [page],
        }

        if self.auto_layout:
            document_data["autoLayout"] = True

        return document_data

    def _upload_document(self, document_data: dict[str, Any]) -> LucidDocument:
        """
        Upload document to Lucidchart.

        Args:
            document_data: Document data structure

        Returns:
            LucidDocument with ID and URL

        Raises:
            LucidAPIError: If upload fails
        """
        url = f"{self.LUCID_API_BASE}/documents"
        headers = self.auth_client.get_auth_header()
        headers["Content-Type"] = "application/json"

        try:
            logger.info("Uploading document to Lucidchart")
            response = self.session.post(
                url,
                json=document_data,
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()

            result = response.json()
            document_id = result.get("documentId")
            document_url = result.get("url")

            if not document_id:
                raise LucidAPIError("No document ID in response")

            document = LucidDocument(
                document_id=document_id,
                title=self.title,
                url=document_url,
            )

            logger.info(
                "Document uploaded successfully",
                document_id=document_id,
                url=document_url,
            )
            return document

        except requests.exceptions.HTTPError as e:
            # Handle token expiration
            if e.response.status_code == 401:
                logger.warning("Access token expired, refreshing")
                self.auth_client.refresh_access_token()
                # Retry upload
                return self._upload_document(document_data)

            logger.error("Document upload failed", status=e.response.status_code, error=str(e))
            raise LucidAPIError(f"Document upload failed: {e}") from e

        except requests.exceptions.RequestException as e:
            logger.error("Document upload request failed", error=str(e))
            raise LucidAPIError(f"Document upload request failed: {e}") from e

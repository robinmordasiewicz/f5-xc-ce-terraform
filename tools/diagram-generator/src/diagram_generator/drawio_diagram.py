"""
Draw.io diagram generation module.

Converts correlated resources into draw.io (diagrams.net) mxGraph XML format.
"""

import subprocess
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional
from xml.dom import minidom

from diagram_generator.exceptions import DiagramGenerationError
from diagram_generator.models import CorrelatedResources, DrawioDocument, ResourceSource
from diagram_generator.utils import format_resource_label, get_logger, get_resource_short_name

logger = get_logger(__name__)


class DrawioDiagramGenerator:
    """Generates draw.io (mxGraph XML) diagrams from correlated resources."""

    # Shape colors by resource source
    SOURCE_COLORS = {
        ResourceSource.TERRAFORM: "#FF6B6B",  # Red
        ResourceSource.AZURE: "#4A90E2",  # Blue
        ResourceSource.F5XC: "#50C878",  # Green
    }

    # Shape styles by resource type
    SHAPE_STYLES = {
        "vnet": "rounded=1;whiteSpace=wrap;html=1;fillColor={color};strokeColor=#000000;",
        "subnet": "rounded=0;whiteSpace=wrap;html=1;fillColor={color};strokeColor=#000000;dashed=1;",
        "vm": "shape=mxgraph.azure.virtual_machine;fillColor={color};strokeColor=#000000;",
        "lb": "shape=mxgraph.azure.load_balancer;fillColor={color};strokeColor=#000000;",
        "site": "shape=cloud;fillColor={color};strokeColor=#000000;",
        "default": "rounded=1;whiteSpace=wrap;html=1;fillColor={color};strokeColor=#000000;",
    }

    # Relationship line styles
    RELATIONSHIP_STYLES = {
        "terraform_dependency": "endArrow=classic;html=1;strokeColor=#FF6B6B;strokeWidth=2;",
        "terraform_azure": "endArrow=classic;html=1;strokeColor=#9B59B6;strokeWidth=2;dashed=1;",
        "f5xc_origin_to_azure_vm": "endArrow=classic;html=1;strokeColor=#3498DB;strokeWidth=2;",
        "f5xc_site_to_azure_vnet": "endArrow=classic;html=1;strokeColor=#1ABC9C;strokeWidth=2;",
        "peering": "endArrow=none;html=1;strokeColor=#34495E;strokeWidth=3;endFill=0;startArrow=classic;startFill=1;",
        "generic_dependency": "endArrow=classic;html=1;strokeColor=#95A5A6;strokeWidth=1;",
    }

    def __init__(
        self,
        title: str = "Azure + F5 XC Infrastructure",
        auto_layout: bool = True,
        group_by_platform: bool = True,
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize draw.io diagram generator.

        Args:
            title: Diagram title
            auto_layout: Enable automatic layout (hierarchical)
            group_by_platform: Group resources by platform (Terraform/Azure/F5 XC)
            output_dir: Output directory for diagram files (default: current directory)
        """
        self.title = title
        self.auto_layout = auto_layout
        self.group_by_platform = group_by_platform
        self.output_dir = output_dir or Path.cwd()

        # Layout configuration
        self.layout = {
            "page_width": 1600,
            "page_height": 1200,
            "shape_width": 160,
            "shape_height": 80,
            "horizontal_spacing": 200,
            "vertical_spacing": 120,
            "group_padding": 40,
        }

        logger.info(
            "Draw.io diagram generator initialized",
            title=title,
            auto_layout=auto_layout,
            output_dir=str(self.output_dir),
        )

    def generate(self, correlated_resources: CorrelatedResources) -> DrawioDocument:
        """
        Generate draw.io diagram from correlated resources.

        Args:
            correlated_resources: Correlated infrastructure resources

        Returns:
            DrawioDocument with file path

        Raises:
            DiagramGenerationError: If diagram generation fails
        """
        logger.info(
            "Generating draw.io diagram",
            resource_count=len(correlated_resources.resources),
            relationship_count=len(correlated_resources.relationships),
        )

        try:
            # Create mxGraph XML structure
            diagram_xml = self._create_diagram_xml(correlated_resources)

            # Save to file
            output_file = self._save_diagram(diagram_xml)

            # Export to PNG
            png_file = self._export_to_png(output_file)

            logger.info(
                "Draw.io diagram generated successfully",
                file_path=str(output_file),
                image_file_path=str(png_file),
            )

            return DrawioDocument(
                file_path=output_file,
                image_file_path=png_file,
                title=self.title,
            )

        except Exception as e:
            logger.error("Draw.io diagram generation failed", error=str(e))
            raise DiagramGenerationError(f"Failed to generate draw.io diagram: {e}") from e

    def _create_diagram_xml(self, correlated_resources: CorrelatedResources) -> ET.Element:
        """Create mxGraph XML structure."""
        # Root mxfile element
        mxfile = ET.Element("mxfile", host="app.diagrams.net", type="device")

        # Diagram element
        diagram = ET.SubElement(
            mxfile,
            "diagram",
            id=str(uuid.uuid4()),
            name=self.title,
        )

        # mxGraphModel
        graph_model = ET.SubElement(
            diagram,
            "mxGraphModel",
            dx="1434",
            dy="796",
            grid="1",
            gridSize="10",
            guides="1",
            tooltips="1",
            connect="1",
            arrows="1",
            fold="1",
            page="1",
            pageScale="1",
            pageWidth=str(self.layout["page_width"]),
            pageHeight=str(self.layout["page_height"]),
            math="0",
            shadow="0",
        )

        # Root element
        root = ET.SubElement(graph_model, "root")
        ET.SubElement(root, "mxCell", id="0")
        ET.SubElement(root, "mxCell", id="1", parent="0")

        # Generate shapes
        shapes = self._generate_shapes(root, correlated_resources.resources)

        # Generate connections
        self._generate_connections(root, correlated_resources.relationships, shapes)

        return mxfile

    def _generate_shapes(self, root: ET.Element, resources: list[Any]) -> dict[str, str]:
        """Generate mxGraph shapes for resources."""
        shapes = {}
        cell_id_counter = 2  # Start after the default cells (0 and 1)

        # Group resources by platform if enabled
        if self.group_by_platform:
            grouped = self._group_resources_by_platform(resources)
            x_offset = 50
            y_offset = 50

            for platform, platform_resources in grouped.items():
                # Create platform container/group
                group_id = str(cell_id_counter)
                cell_id_counter += 1

                group_width = 600
                group_height = 400

                # Map platform name to ResourceSource for color lookup
                platform_to_source = {
                    "Terraform": ResourceSource.TERRAFORM,
                    "Azure": ResourceSource.AZURE,
                    "F5 XC": ResourceSource.F5XC,
                }
                source = platform_to_source.get(platform, ResourceSource.TERRAFORM)

                ET.SubElement(
                    root,
                    "mxCell",
                    id=group_id,
                    value=platform,
                    style=f"swimlane;fontStyle=1;align=center;verticalAlign=top;childLayout=stackLayout;horizontal=1;startSize=26;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;fillColor={self.SOURCE_COLORS.get(source, '#FFFFFF')};strokeColor=#000000;fontSize=14;fontColor=#000000;",
                    vertex="1",
                    parent="1",
                )

                ET.SubElement(
                    root[-1],
                    "mxGeometry",
                    x=str(x_offset),
                    y=str(y_offset),
                    width=str(group_width),
                    height=str(group_height),
                    attrib={"as": "geometry"},
                )

                # Add resources within group
                resource_x = 20
                resource_y = 40
                for resource in platform_resources:
                    cell_id = str(cell_id_counter)
                    cell_id_counter += 1

                    resource_label = format_resource_label(
                        source=resource.get("source", ""),
                        resource_type=resource.get("type", ""),
                        name=resource.get("name", ""),
                    )
                    resource_style = self._get_resource_style(resource)

                    ET.SubElement(
                        root,
                        "mxCell",
                        id=cell_id,
                        value=resource_label,
                        style=resource_style,
                        vertex="1",
                        parent=group_id,
                    )

                    ET.SubElement(
                        root[-1],
                        "mxGeometry",
                        x=str(resource_x),
                        y=str(resource_y),
                        width=str(self.layout["shape_width"]),
                        height=str(self.layout["shape_height"]),
                        attrib={"as": "geometry"},
                    )

                    shapes[resource.get("id", resource.get("name", "unknown"))] = cell_id

                    # Update position for next resource
                    resource_y += self.layout["vertical_spacing"]
                    if resource_y > group_height - 100:
                        resource_y = 40
                        resource_x += self.layout["horizontal_spacing"]

                x_offset += group_width + 100

        else:
            # Simple layout without grouping
            x = 50
            y = 50
            for resource in resources:
                cell_id = str(cell_id_counter)
                cell_id_counter += 1

                resource_label = format_resource_label(
                    source=resource.get("source", ""),
                    resource_type=resource.get("type", ""),
                    name=resource.get("name", ""),
                )
                resource_style = self._get_resource_style(resource)

                ET.SubElement(
                    root,
                    "mxCell",
                    id=cell_id,
                    value=resource_label,
                    style=resource_style,
                    vertex="1",
                    parent="1",
                )

                ET.SubElement(
                    root[-1],
                    "mxGeometry",
                    x=str(x),
                    y=str(y),
                    width=str(self.layout["shape_width"]),
                    height=str(self.layout["shape_height"]),
                    attrib={"as": "geometry"},
                )

                shapes[resource.get("id", resource.get("name", "unknown"))] = cell_id

                # Update position
                y += self.layout["vertical_spacing"]
                if y > 800:
                    y = 50
                    x += self.layout["horizontal_spacing"]

        return shapes

    def _generate_connections(
        self,
        root: ET.Element,
        relationships: list[Any],
        shapes: dict[str, str],
    ) -> None:
        """Generate mxGraph connections for relationships."""
        cell_id = len(root) + 1

        for relationship in relationships:
            source_id = shapes.get(relationship.source_id)
            target_id = shapes.get(relationship.target_id)

            if not source_id or not target_id:
                logger.warning(
                    "Skipping relationship - shape not found",
                    source=relationship.source_id,
                    target=relationship.target_id,
                )
                continue

            # Determine relationship style
            style = self.RELATIONSHIP_STYLES.get(
                relationship.relationship_type,
                self.RELATIONSHIP_STYLES["generic_dependency"],
            )

            # Get label from metadata or use relationship type
            label = relationship.metadata.get("label", str(relationship.relationship_type))

            ET.SubElement(
                root,
                "mxCell",
                id=str(cell_id),
                value=label,
                style=style,
                edge="1",
                parent="1",
                source=source_id,
                target=target_id,
            )

            ET.SubElement(
                root[-1],
                "mxGeometry",
                relative="1",
                attrib={"as": "geometry"},
            )

            cell_id += 1

    def _get_resource_style(self, resource: Any) -> str:
        """Get draw.io style for resource type."""
        resource_type = get_resource_short_name(resource.get("type", "")).lower()
        color = self.SOURCE_COLORS.get(resource.get("source", ""), "#FFFFFF")

        # Determine shape style based on resource type
        if "vnet" in resource_type or "network" in resource_type:
            style_template = self.SHAPE_STYLES["vnet"]
        elif "subnet" in resource_type:
            style_template = self.SHAPE_STYLES["subnet"]
        elif "vm" in resource_type or "virtual_machine" in resource_type:
            style_template = self.SHAPE_STYLES["vm"]
        elif "loadbalancer" in resource_type or "lb" in resource_type:
            style_template = self.SHAPE_STYLES["lb"]
        elif "site" in resource_type:
            style_template = self.SHAPE_STYLES["site"]
        else:
            style_template = self.SHAPE_STYLES["default"]

        return style_template.format(color=color)

    def _group_resources_by_platform(self, resources: list[Any]) -> dict[str, list[Any]]:
        """Group resources by source platform."""
        grouped: dict[str, list[Any]] = {
            "Terraform": [],
            "Azure": [],
            "F5 XC": [],
        }

        for resource in resources:
            source = resource.get("source", "")
            if source == ResourceSource.TERRAFORM or source == "terraform":
                grouped["Terraform"].append(resource)
            elif source == ResourceSource.AZURE or source == "azure":
                grouped["Azure"].append(resource)
            elif source == ResourceSource.F5XC or source == "f5xc":
                grouped["F5 XC"].append(resource)

        # Remove empty groups
        return {k: v for k, v in grouped.items() if v}

    def _save_diagram(self, diagram_xml: ET.Element) -> Path:
        """Save diagram XML to file."""
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        safe_title = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in self.title)
        output_file = self.output_dir / f"{safe_title}.drawio"

        # Pretty print XML
        xml_string = ET.tostring(diagram_xml, encoding="unicode")
        dom = minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent="  ")

        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(pretty_xml)

        logger.info("Diagram saved to file", path=str(output_file))
        return output_file

    def _export_to_png(self, drawio_file: Path) -> Path:
        """
        Export .drawio file to PNG using drawio CLI.

        Args:
            drawio_file: Path to the .drawio file to export

        Returns:
            Path to the exported PNG file

        Raises:
            DiagramGenerationError: If PNG export fails
        """
        png_file = drawio_file.with_suffix(".png")

        try:
            # Use drawio CLI to export PNG
            # --export: export mode
            # --format png: output format
            # --transparent: transparent background
            # --border 10: add border around diagram
            # --crop: crop to diagram size
            subprocess.run(
                [
                    "drawio",
                    "--export",
                    "--format",
                    "png",
                    "--transparent",
                    "--border",
                    "10",
                    "--crop",
                    "--output",
                    str(png_file),
                    str(drawio_file),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            logger.info("PNG export successful", png_file=str(png_file))
            return png_file

        except subprocess.CalledProcessError as e:
            error_msg = f"PNG export failed: {e.stderr}"
            logger.error(error_msg, returncode=e.returncode)
            raise DiagramGenerationError(error_msg) from e
        except FileNotFoundError:
            error_msg = "drawio CLI not found. Install with: brew install --cask drawio"
            logger.error(error_msg)
            raise DiagramGenerationError(error_msg) from None

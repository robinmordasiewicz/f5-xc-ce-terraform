"""
Command-line interface for Azure + F5 XC diagram generator.

Orchestrates data collection, correlation, and diagram generation.
"""

import sys
from pathlib import Path
from typing import Optional

import click
from pydantic import ValidationError

from diagram_generator.azure_collector import AzureResourceGraphCollector
from diagram_generator.correlation import ResourceCorrelator
from diagram_generator.drawio_diagram import DrawioDiagramGenerator
from diagram_generator.f5xc_collector import F5XCCollector
from diagram_generator.models import (
    AzureAuthMethod,
    DiagramConfig,
    F5XCAuthMethod,
)
from diagram_generator.terraform_collector import TerraformStateCollector
from diagram_generator.utils import configure_logging, get_logger

logger = get_logger(__name__)


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file (YAML or JSON)",
)
@click.option(
    "--terraform-path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to Terraform directory (default: current directory)",
)
@click.option(
    "--azure-subscription",
    envvar="AZURE_SUBSCRIPTION_ID",
    required=True,
    help="Azure subscription ID",
)
@click.option(
    "--azure-auth",
    type=click.Choice(["azure_cli", "service_principal", "managed_identity"]),
    default="azure_cli",
    help="Azure authentication method",
)
@click.option(
    "--f5xc-tenant",
    envvar="F5XC_TENANT",
    required=True,
    help="F5 XC tenant name",
)
@click.option(
    "--f5xc-auth",
    type=click.Choice(["api_token", "p12_certificate"]),
    default="api_token",
    help="F5 XC authentication method",
)
@click.option(
    "--f5xc-api-token",
    envvar="F5XC_API_TOKEN",
    help="F5 XC API token (required if using api_token auth)",
)
@click.option(
    "--f5xc-p12-path",
    type=click.Path(exists=True, path_type=Path),
    envvar="F5XC_P12_CERT_PATH",
    help="Path to F5 XC P12 certificate (required if using p12_certificate auth)",
)
@click.option(
    "--f5xc-p12-password",
    envvar="F5XC_P12_PASSWORD",
    help="F5 XC P12 certificate password",
)
@click.option(
    "--diagram-title",
    default="Azure + F5 XC Infrastructure",
    help="Diagram title",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    help="Output directory for diagram files (default: current directory)",
)
@click.option(
    "--no-auto-layout",
    is_flag=True,
    help="Disable automatic layout",
)
@click.option(
    "--no-grouping",
    is_flag=True,
    help="Disable resource grouping by platform",
)
@click.option(
    "--no-drift-detection",
    is_flag=True,
    help="Disable configuration drift detection",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def main(
    config: Optional[Path],
    terraform_path: Optional[Path],
    azure_subscription: str,
    azure_auth: str,
    f5xc_tenant: str,
    f5xc_auth: str,
    f5xc_api_token: Optional[str],
    f5xc_p12_path: Optional[Path],
    f5xc_p12_password: Optional[str],
    diagram_title: str,
    output_dir: Optional[Path],
    no_auto_layout: bool,
    no_grouping: bool,
    no_drift_detection: bool,
    verbose: bool,
) -> None:
    """
    Generate Draw.io diagrams from Azure and F5 XC infrastructure.

    Collects resources from Terraform state, Azure Resource Graph, and F5 XC API,
    correlates them, and generates a comprehensive infrastructure diagram in Draw.io format.
    """
    # Configure logging
    configure_logging(verbose=verbose)

    logger.info(
        "Starting diagram generation",
        azure_subscription=azure_subscription,
        f5xc_tenant=f5xc_tenant,
    )

    try:
        # Build configuration
        config_data = _build_config(
            terraform_path=terraform_path,
            azure_subscription=azure_subscription,
            azure_auth=azure_auth,
            f5xc_tenant=f5xc_tenant,
            f5xc_auth=f5xc_auth,
            f5xc_api_token=f5xc_api_token,
            f5xc_p12_path=f5xc_p12_path,
            f5xc_p12_password=f5xc_p12_password,
            diagram_title=diagram_title,
            auto_layout=not no_auto_layout,
            group_by_platform=not no_grouping,
            enable_drift_detection=not no_drift_detection,
        )

        # Phase 1: Collect resources from all sources
        click.echo("📊 Phase 1: Collecting infrastructure resources...")

        terraform_collector = TerraformStateCollector(
            state_path=(
                str(config_data.terraform_state_path) if config_data.terraform_state_path else None
            )
        )
        terraform_resources = terraform_collector.collect_resources()
        click.echo(f"  ✓ Collected {len(terraform_resources)} Terraform resources")

        azure_collector = AzureResourceGraphCollector(
            subscription_id=config_data.azure_subscription_id,
            auth_method=config_data.azure_auth_method,
        )
        azure_resources = azure_collector.collect_resources()
        click.echo(f"  ✓ Collected {len(azure_resources)} Azure resources")

        f5xc_collector = F5XCCollector(
            tenant=config_data.f5xc_tenant,
            auth_method=config_data.f5xc_auth_method,
            api_token=config_data.f5xc_api_token,
            p12_cert_path=config_data.f5xc_p12_cert_path,
            p12_password=config_data.f5xc_p12_password,
        )
        f5xc_resources = f5xc_collector.collect_resources()
        click.echo(f"  ✓ Collected {len(f5xc_resources)} F5 XC resources")

        # Phase 2: Correlate resources
        click.echo("\n🔗 Phase 2: Correlating resources across platforms...")

        correlator = ResourceCorrelator(
            match_by_tags=config_data.match_by_tags,
            match_by_ip=config_data.match_by_ip,
            enable_drift_detection=config_data.enable_drift_detection,
        )
        correlated = correlator.correlate(
            terraform_resources=terraform_resources,
            azure_resources=azure_resources,
            f5xc_resources=f5xc_resources,
        )
        click.echo(f"  ✓ Found {len(correlated.relationships)} relationships")

        if correlated.drift:
            click.echo(f"  ⚠ Detected {len(correlated.drift)} configuration drift issues")
            for drift in correlated.drift[:5]:  # Show first 5
                click.echo(f"    - {drift.drift_type}: {drift.resource_address}")

        # Phase 3: Generate Draw.io diagram
        click.echo("\n🎨 Phase 3: Generating Draw.io diagram...")

        # Generate diagram
        diagram_generator = DrawioDiagramGenerator(
            title=config_data.diagram_title,
            auto_layout=config_data.auto_layout,
            group_by_platform=config_data.group_by_platform,
            output_dir=output_dir,
        )
        document = diagram_generator.generate(correlated)

        click.echo("\n✅ Diagram generated successfully!")
        click.echo(f"   📄 Draw.io file: {document.file_path}")
        click.echo(f"   🖼️  PNG image: {document.image_file_path}")
        click.echo(f"   💡 Display PNG in README, link to .drawio for editing")

        # Summary
        click.echo("\n📈 Summary:")
        click.echo(f"   Total resources: {len(correlated.resources)}")
        click.echo(f"   Terraform: {len(terraform_resources)}")
        click.echo(f"   Azure: {len(azure_resources)}")
        click.echo(f"   F5 XC: {len(f5xc_resources)}")
        click.echo(f"   Relationships: {len(correlated.relationships)}")
        click.echo(f"   Drift issues: {len(correlated.drift)}")

    except ValidationError as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.exception("Diagram generation failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


def _build_config(
    terraform_path: Optional[Path],
    azure_subscription: str,
    azure_auth: str,
    f5xc_tenant: str,
    f5xc_auth: str,
    f5xc_api_token: Optional[str],
    f5xc_p12_path: Optional[Path],
    f5xc_p12_password: Optional[str],
    diagram_title: str,
    auto_layout: bool,
    group_by_platform: bool,
    enable_drift_detection: bool,
) -> DiagramConfig:
    """
    Build and validate configuration.

    Returns:
        Validated DiagramConfig

    Raises:
        ValidationError: If configuration is invalid
    """
    config = DiagramConfig(
        terraform_state_path=str(terraform_path) if terraform_path else None,
        azure_subscription_id=azure_subscription,
        azure_auth_method=AzureAuthMethod(azure_auth),
        f5xc_tenant=f5xc_tenant,
        f5xc_auth_method=F5XCAuthMethod(f5xc_auth),
        f5xc_api_token=f5xc_api_token,
        f5xc_p12_cert_path=str(f5xc_p12_path) if f5xc_p12_path else None,
        f5xc_p12_password=f5xc_p12_password,
        diagram_title=diagram_title,
        auto_layout=auto_layout,
        group_by_platform=group_by_platform,
        enable_drift_detection=enable_drift_detection,
    )

    return config


if __name__ == "__main__":
    main()

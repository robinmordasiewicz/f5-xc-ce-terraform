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
from diagram_generator.models import AzureAuthMethod, DiagramConfig, F5XCAuthMethod
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
    required=False,  # Allow environment variable to satisfy requirement
    help="Azure subscription ID (can be set via AZURE_SUBSCRIPTION_ID env var)",
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
    required=False,  # Allow environment variable to satisfy requirement
    help="F5 XC tenant name (can be set via F5XC_TENANT or TF_VAR_f5_xc_tenant env var)",
)
@click.option(
    "--f5xc-auth",
    type=click.Choice(["api_token", "certificate", "p12_certificate"]),
    default="p12_certificate",  # Default to P12 (matches setup-backend.sh)
    help="F5 XC authentication method",
)
@click.option(
    "--f5xc-api-token",
    envvar="F5XC_API_TOKEN",
    help="F5 XC API token (can be set via F5XC_API_TOKEN or VOLT_API_KEY env var)",
)
@click.option(
    "--f5xc-p12-path",
    type=click.Path(exists=True, path_type=Path),
    envvar="F5XC_P12_CERT_PATH",
    help="Path to F5 XC P12 certificate (can be set via F5XC_P12_CERT_PATH env var)",
)
@click.option(
    "--f5xc-p12-password",
    envvar="VES_P12_PASSWORD",  # Match setup-backend.sh environment variable
    help="F5 XC P12 certificate password (can be set via VES_P12_PASSWORD env var)",
)
@click.option(
    "--f5xc-cert-path",
    type=click.Path(exists=True, path_type=Path),
    envvar="F5XC_CERT_PATH",
    help="Path to F5 XC certificate file (alternative to P12)",
)
@click.option(
    "--f5xc-key-path",
    type=click.Path(exists=True, path_type=Path),
    envvar="F5XC_KEY_PATH",
    help="Path to F5 XC key file (alternative to P12)",
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
    config: Optional[Path],  # noqa: ARG001 - Reserved for future configuration file support
    terraform_path: Optional[Path],
    azure_subscription: str,
    azure_auth: str,
    f5xc_tenant: str,
    f5xc_auth: str,
    f5xc_api_token: Optional[str],
    f5xc_p12_path: Optional[Path],
    f5xc_p12_password: Optional[str],
    f5xc_cert_path: Optional[Path],
    f5xc_key_path: Optional[Path],
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

    Authentication can be provided via CLI arguments or environment variables.
    Environment variables take precedence for terraform integration.
    """
    import os

    # Configure logging
    configure_logging(verbose=verbose)

    # Handle environment variable fallbacks for terraform integration
    if not azure_subscription:
        azure_subscription = os.getenv("AZURE_SUBSCRIPTION_ID")
        if not azure_subscription:
            click.echo(
                "❌ Azure subscription ID required via --azure-subscription or AZURE_SUBSCRIPTION_ID env var",
                err=True,
            )
            sys.exit(1)

    if not f5xc_tenant:
        # Try both F5XC_TENANT and TF_VAR_F5_XC_TENANT (terraform variable)
        f5xc_tenant = os.getenv("F5XC_TENANT") or os.getenv("TF_VAR_F5_XC_TENANT")
        if not f5xc_tenant:
            click.echo(
                "❌ F5 XC tenant required via --f5xc-tenant or F5XC_TENANT/TF_VAR_F5_XC_TENANT env var",
                err=True,
            )
            sys.exit(1)

    # Handle F5 XC P12 authentication from environment (setup-backend.sh pattern)
    if f5xc_auth == "p12_certificate":
        if not f5xc_p12_password:
            f5xc_p12_password = os.getenv("VES_P12_PASSWORD")

        # Check for P12 content in environment (base64 encoded from setup-backend.sh)
        p12_content_env = os.getenv("VES_P12_CONTENT")
        if p12_content_env and not f5xc_p12_path:
            # VES_P12_CONTENT is set, we'll need to decode it to a temp file
            import base64
            import tempfile

            logger.info("Using P12 certificate from VES_P12_CONTENT environment variable")
            try:
                p12_bytes = base64.b64decode(p12_content_env)
                # Create temporary P12 file
                temp_p12 = tempfile.NamedTemporaryFile(delete=False, suffix=".p12")
                temp_p12.write(p12_bytes)
                temp_p12.close()
                f5xc_p12_path = Path(temp_p12.name)
                logger.info(f"Extracted P12 certificate to temporary file: {f5xc_p12_path}")
            except Exception as e:
                logger.error(f"Failed to decode VES_P12_CONTENT: {e}")
                click.echo(f"❌ Failed to process P12 certificate from environment: {e}", err=True)
                sys.exit(1)

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
            f5xc_cert_path=f5xc_cert_path,
            f5xc_key_path=f5xc_key_path,
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

        # Extract resource groups from Terraform to scope Azure queries
        resource_groups = terraform_collector.extract_resource_groups()
        if resource_groups:
            click.echo(
                f"  ✓ Found {len(resource_groups)} resource group(s): {', '.join(resource_groups)}"
            )
        else:
            click.echo("  ⚠ No resource groups found in Terraform, querying entire subscription")

        azure_collector = AzureResourceGraphCollector(
            subscription_id=config_data.azure_subscription_id,
            auth_method=config_data.azure_auth_method,
            resource_groups=resource_groups,
        )
        azure_resources = azure_collector.collect_resources()
        click.echo(f"  ✓ Collected {len(azure_resources)} Azure resources")

        # Collect Azure relationships for traffic flow visualization
        lb_relationships = azure_collector.collect_load_balancer_relationships()
        route_relationships = azure_collector.collect_route_table_relationships()
        click.echo(f"  ✓ Collected {len(lb_relationships)} LB relationships")
        click.echo(f"  ✓ Collected {len(route_relationships)} route table relationships")

        f5xc_collector = F5XCCollector(
            tenant=config_data.f5xc_tenant,
            auth_method=config_data.f5xc_auth_method,
            api_token=config_data.f5xc_api_token,
            p12_cert_path=config_data.f5xc_p12_cert_path,
            p12_password=config_data.f5xc_p12_password,
            cert_path=str(f5xc_cert_path) if f5xc_cert_path else None,
            key_path=str(f5xc_key_path) if f5xc_key_path else None,
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

        # Generate diagram with traffic flow relationships
        diagram_generator = DrawioDiagramGenerator(
            title=config_data.diagram_title,
            auto_layout=config_data.auto_layout,
            group_by_platform=config_data.group_by_platform,
            output_dir=output_dir,
        )
        document = diagram_generator.generate(
            correlated,
            lb_relationships=lb_relationships,
            route_relationships=route_relationships,
        )

        click.echo("\n✅ Diagram generated successfully!")
        click.echo(f"   📄 Draw.io file: {document.file_path}")
        click.echo(f"   🖼️  PNG image: {document.image_file_path}")
        click.echo("   💡 Display PNG in README, link to .drawio for editing")

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
    f5xc_cert_path: Optional[Path],
    f5xc_key_path: Optional[Path],
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
        f5xc_cert_path=str(f5xc_cert_path) if f5xc_cert_path else None,
        f5xc_key_path=str(f5xc_key_path) if f5xc_key_path else None,
        diagram_title=diagram_title,
        auto_layout=auto_layout,
        group_by_platform=group_by_platform,
        enable_drift_detection=enable_drift_detection,
    )

    return config


if __name__ == "__main__":
    main()

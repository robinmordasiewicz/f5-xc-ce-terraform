# Azure + F5 XC Infrastructure Diagram Generator

Automated infrastructure diagram generation from Terraform state, Azure Resource Graph, and F5 Distributed Cloud API with Lucidchart integration.

## Features

- **Multi-Source Data Collection**
  - Terraform state parsing (`terraform show -json`)
  - Azure Resource Graph queries (KQL)
  - F5 Distributed Cloud REST API

- **Intelligent Correlation**
  - Cross-reference resources across all three sources
  - Match by resource IDs, tags/labels, and IP addresses
  - Detect configuration drift between Terraform and Azure
  - Build unified resource graph with relationships

- **Professional Diagram Generation**
  - Upload to Lucidchart via OAuth 2.0
  - Automatic layout and grouping by platform
  - Color-coded by source (Terraform, Azure, F5 XC)
  - Relationship visualization with typed connectors

- **Modern Python Practices**
  - Type hints throughout (PEP 484)
  - Pydantic v2 for data validation
  - Structured logging with structlog
  - Comprehensive error handling
  - Retry logic for API calls

## Prerequisites

- **Python**: 3.9 or higher
- **Terraform**: Initialized Terraform workspace with state
- **Azure**:
  - Azure subscription with resources
  - Azure CLI installed (for authentication)
  - Or Service Principal credentials
- **F5 Distributed Cloud**:
  - F5 XC tenant access
  - API token or P12 certificate
- **Lucidchart**:
  - Lucidchart account
  - OAuth app credentials (client ID and secret)
- **OpenSSL**: Required for P12 certificate extraction (if using cert auth)

## Installation

### From Source

```bash
# Clone repository
cd tools/diagram-generator

# Install in development mode
pip install -e ".[dev]"

# Or for production
pip install .
```

### Dependencies

Core dependencies are automatically installed:
- `azure-identity` - Azure authentication
- `azure-mgmt-resourcegraph` - Azure Resource Graph API
- `requests` - HTTP client with retry logic
- `pydantic>=2.5.0` - Data validation
- `networkx` - Graph processing
- `click` - CLI interface
- `structlog` - Structured logging

## Configuration

### Environment Variables

Set the following environment variables:

```bash
# Azure
export AZURE_SUBSCRIPTION_ID="your-subscription-id"

# F5 XC
export F5XC_TENANT="your-tenant-name"
export F5XC_API_TOKEN="your-api-token"  # If using API token auth
# OR
export F5XC_P12_CERT_PATH="/path/to/cert.p12"  # If using P12 cert
export F5XC_P12_PASSWORD="cert-password"

# Lucidchart
export LUCID_CLIENT_ID="your-lucid-client-id"
export LUCID_CLIENT_SECRET="your-lucid-client-secret"
export LUCID_REDIRECT_URI="http://localhost:8080/callback"
```

### Lucidchart OAuth Setup

1. Go to [Lucidchart Developer Portal](https://lucid.app/developers)
2. Create a new OAuth app
3. Set redirect URI to `http://localhost:8080/callback`
4. Note your client ID and client secret
5. Required scopes:
   - `lucidchart.document.content`
   - `lucidchart.document.create`

## Usage

### Basic Usage

```bash
# Generate diagram from current directory Terraform state
generate-diagram \
  --azure-subscription $AZURE_SUBSCRIPTION_ID \
  --f5xc-tenant $F5XC_TENANT \
  --lucid-client-id $LUCID_CLIENT_ID \
  --lucid-client-secret $LUCID_CLIENT_SECRET
```

### With Terraform Path

```bash
# Generate from specific Terraform directory
generate-diagram \
  --terraform-path /path/to/terraform \
  --azure-subscription $AZURE_SUBSCRIPTION_ID \
  --f5xc-tenant $F5XC_TENANT \
  --lucid-client-id $LUCID_CLIENT_ID \
  --lucid-client-secret $LUCID_CLIENT_SECRET
```

### With P12 Certificate Authentication

```bash
# Use P12 certificate for F5 XC auth
generate-diagram \
  --azure-subscription $AZURE_SUBSCRIPTION_ID \
  --f5xc-tenant $F5XC_TENANT \
  --f5xc-auth p12_certificate \
  --f5xc-p12-path /path/to/cert.p12 \
  --f5xc-p12-password "cert-password" \
  --lucid-client-id $LUCID_CLIENT_ID \
  --lucid-client-secret $LUCID_CLIENT_SECRET
```

### Custom Diagram Options

```bash
# Customize diagram generation
generate-diagram \
  --azure-subscription $AZURE_SUBSCRIPTION_ID \
  --f5xc-tenant $F5XC_TENANT \
  --lucid-client-id $LUCID_CLIENT_ID \
  --lucid-client-secret $LUCID_CLIENT_SECRET \
  --diagram-title "Production Infrastructure" \
  --no-auto-layout \
  --no-grouping \
  --no-drift-detection \
  --verbose
```

### CLI Options

```
Options:
  -c, --config PATH              Configuration file path (YAML or JSON)
  --terraform-path PATH          Terraform directory path
  --azure-subscription TEXT      Azure subscription ID [required]
  --azure-auth TEXT              Azure auth method (azure_cli|service_principal|managed_identity)
  --f5xc-tenant TEXT             F5 XC tenant name [required]
  --f5xc-auth TEXT               F5 XC auth method (api_token|p12_certificate)
  --f5xc-api-token TEXT          F5 XC API token
  --f5xc-p12-path PATH           F5 XC P12 certificate path
  --f5xc-p12-password TEXT       F5 XC P12 password
  --lucid-client-id TEXT         Lucidchart OAuth client ID [required]
  --lucid-client-secret TEXT     Lucidchart OAuth client secret [required]
  --lucid-redirect-uri TEXT      Lucidchart OAuth redirect URI
  --diagram-title TEXT           Diagram title
  --no-auto-layout               Disable automatic layout
  --no-grouping                  Disable resource grouping
  --no-drift-detection           Disable drift detection
  -v, --verbose                  Enable verbose logging
  --help                         Show this message and exit
```

## Output

The tool generates a Lucidchart diagram with:

1. **Resources** grouped by source:
   - 🔴 **Terraform** resources (red)
   - 🔵 **Azure** resources (blue)
   - 🟢 **F5 XC** resources (green)

2. **Relationships** shown as connectors:
   - Terraform dependencies (red)
   - Terraform ↔ Azure correlation (purple)
   - F5 XC origin pools → Azure VMs (blue)
   - F5 XC sites → Azure VNets (teal)
   - Generic dependencies (gray)

3. **Drift Detection** (if enabled):
   - Tag mismatches
   - Location differences
   - Configuration inconsistencies

## Example Workflow

```bash
# 1. Deploy infrastructure with Terraform
cd terraform/
terraform apply

# 2. Generate diagram
generate-diagram \
  --terraform-path . \
  --azure-subscription $AZURE_SUBSCRIPTION_ID \
  --f5xc-tenant $F5XC_TENANT \
  --lucid-client-id $LUCID_CLIENT_ID \
  --lucid-client-secret $LUCID_CLIENT_SECRET \
  --diagram-title "Production Infrastructure - $(date +%Y-%m-%d)"

# Output:
# 📊 Phase 1: Collecting infrastructure resources...
#   ✓ Collected 45 Terraform resources
#   ✓ Collected 38 Azure resources
#   ✓ Collected 12 F5 XC resources
#
# 🔗 Phase 2: Correlating resources across platforms...
#   ✓ Found 87 relationships
#   ⚠ Detected 3 configuration drift issues
#
# 🎨 Phase 3: Generating Lucidchart diagram...
#   ✓ Authenticated with Lucidchart
#
# ✅ Diagram generated successfully!
#    Document ID: abc123-def456-ghi789
#    URL: https://lucid.app/documents/view/abc123-def456-ghi789
#
# 📈 Summary:
#    Total resources: 95
#    Terraform: 45
#    Azure: 38
#    F5 XC: 12
#    Relationships: 87
#    Drift issues: 3
```

## Development

### Setup Development Environment

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Run Tests

```bash
# Run all tests with coverage
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_terraform_collector.py
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

### Project Structure

```
diagram-generator/
├── src/
│   └── diagram_generator/
│       ├── __init__.py
│       ├── cli.py                    # CLI entry point
│       ├── models.py                 # Pydantic data models
│       ├── exceptions.py             # Custom exceptions
│       ├── utils.py                  # Utilities and logging
│       ├── terraform_collector.py    # Terraform state collector
│       ├── azure_collector.py        # Azure Resource Graph collector
│       ├── f5xc_collector.py         # F5 XC REST API collector
│       ├── correlation.py            # Resource correlation engine
│       ├── lucid_auth.py             # Lucidchart OAuth client
│       └── lucid_diagram.py          # Diagram generation and upload
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # pytest fixtures
│   └── test_*.py                     # Test modules
├── pyproject.toml                    # Project configuration
└── README.md                         # This file
```

## Architecture

### Data Collection Phase
1. **Terraform Collector**: Executes `terraform show -json` and parses state into `TerraformResource` models
2. **Azure Collector**: Queries Azure Resource Graph with KQL and parses into `AzureResource` models
3. **F5 XC Collector**: Calls F5 XC REST API endpoints and parses into `F5XCResource` models

### Correlation Phase
1. **Resource Indexing**: Adds all resources to NetworkX graph
2. **Relationship Discovery**:
   - Terraform dependencies from `depends_on`
   - Terraform ↔ Azure by resource IDs
   - F5 XC ↔ Azure by IP addresses and network configuration
   - Tag-based correlation across all sources
3. **Drift Detection**: Compares Terraform state vs Azure actual state

### Diagram Generation Phase
1. **Shape Generation**: Creates Lucid shapes from resources with positioning
2. **Connector Generation**: Creates lines from relationships
3. **Grouping & Layout**: Organizes by platform with auto-layout
4. **Upload**: Authenticates with OAuth and uploads via Lucidchart API

## Troubleshooting

### Authentication Issues

**Azure CLI not authenticated:**
```bash
az login
az account set --subscription $AZURE_SUBSCRIPTION_ID
```

**F5 XC API token issues:**
- Verify token is valid and not expired
- Check token has required permissions
- Try regenerating token in F5 XC console

**Lucidchart OAuth callback not working:**
- Ensure redirect URI matches exactly in app settings
- Check firewall allows localhost:8080
- Try force re-authentication: `rm ~/.lucid_token_cache.json`

### Terraform State Issues

**State file not found:**
```bash
cd terraform/
terraform init
terraform show -json > /tmp/state.json
```

**State is empty:**
- Ensure `terraform apply` has been run
- Check Terraform backend is configured correctly

### Network Issues

**Timeout errors:**
- Increase timeout in code if needed
- Check network connectivity to Azure, F5 XC, and Lucidchart APIs
- Verify firewall rules

**API rate limits:**
- Implement exponential backoff (already included in retry logic)
- Reduce concurrent requests
- Check API quota limits

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass: `pytest`
6. Format code: `black . && isort .`
7. Submit pull request

## License

[Your License Here]

## Support

For issues and questions:
- GitHub Issues: [Link to issues]
- Documentation: [Link to docs]
- F5 XC API Docs: https://docs.cloud.f5.com/docs/api
- Azure Resource Graph: https://docs.microsoft.com/azure/governance/resource-graph/
- Lucidchart API: https://developer.lucid.co/

## Acknowledgments

- Built with modern Python best practices
- Leverages Azure Resource Graph for efficient querying
- Uses F5 Distributed Cloud REST API (not deprecated vesctl)
- Integrates with Lucidchart for professional diagrams

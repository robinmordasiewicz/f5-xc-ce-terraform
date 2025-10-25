# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of Azure + F5 XC Infrastructure Diagram Generator
- Three-source data collection:
  - Terraform state parsing via `terraform show -json`
  - Azure Resource Graph queries with KQL
  - F5 Distributed Cloud REST API integration
- Intelligent resource correlation:
  - Cross-reference resources by IDs, tags, and IP addresses
  - Detect configuration drift between Terraform and Azure
  - Build unified resource graph with NetworkX
- Lucidchart integration:
  - OAuth 2.0 authentication with token refresh
  - Automatic diagram generation and upload
  - Color-coded shapes by resource source
  - Relationship visualization with typed connectors
- Modern Python implementation:
  - Full type hints (PEP 484)
  - Pydantic v2 for data validation
  - Structured logging with structlog
  - Retry logic for API resilience
  - Comprehensive error handling
- Development tooling:
  - pytest test suite with fixtures
  - pre-commit hooks for code quality
  - GitHub Actions CI/CD pipeline
  - Ruff for fast linting
  - Black and isort for formatting
  - mypy for type checking
- Documentation:
  - Comprehensive README with examples
  - Contributing guidelines
  - Example configuration file
  - Inline docstrings throughout

## [0.1.0] - 2025-01-XX

### Added
- Initial implementation of diagram generator
- Support for Terraform, Azure, and F5 XC data sources
- Lucidchart diagram generation and upload
- CLI interface with Click
- Configuration via environment variables or config file
- Comprehensive test suite
- CI/CD automation with GitHub Actions

### Security
- Secure credential handling
- Token caching for Lucidchart OAuth
- P12 certificate extraction with OpenSSL
- Environment variable support for sensitive data

---

## Version History

### Versioning Scheme

- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality (backwards compatible)
- **PATCH** version for backwards compatible bug fixes

### Release Notes Format

Each release includes:
- **Added** - New features
- **Changed** - Changes to existing functionality
- **Deprecated** - Soon-to-be removed features
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Security improvements

---

## Roadmap

### Future Enhancements

**v0.2.0 - Enhanced Visualization**
- [ ] Support for additional diagram formats (Draw.io, Mermaid)
- [ ] Custom shape libraries
- [ ] Advanced layout algorithms
- [ ] Interactive diagram annotations

**v0.3.0 - Extended Data Sources**
- [ ] AWS resource support
- [ ] GCP resource support
- [ ] Kubernetes cluster integration
- [ ] Multi-cloud correlation

**v0.4.0 - Advanced Features**
- [ ] Real-time diagram updates
- [ ] Version control integration
- [ ] Cost analysis overlay
- [ ] Security posture visualization

**v0.5.0 - Automation & Integration**
- [ ] CI/CD pipeline integration
- [ ] Scheduled diagram generation
- [ ] Slack/Teams notifications
- [ ] Webhook support for updates

### Community Requests

Track feature requests and enhancements in [GitHub Issues](https://github.com/robinmordasiewicz/f5-xc-ce-terraform/issues).

---

## Migration Guides

### Upgrading to v0.2.0 (Future)

When v0.2.0 is released, migration instructions will be provided here.

---

## Support

For questions, issues, or feature requests:
- GitHub Issues: [Report issues](https://github.com/robinmordasiewicz/f5-xc-ce-terraform/issues)
- GitHub Discussions: [Ask questions](https://github.com/robinmordasiewicz/f5-xc-ce-terraform/discussions)

"""
F5 Distributed Cloud REST API collection module.

Retrieves resources from F5 XC via REST API (not vesctl CLI).
"""

import tempfile
from pathlib import Path
from typing import Optional

import requests

from diagram_generator.exceptions import AuthenticationError, F5XCAPIError
from diagram_generator.models import F5XCAuthMethod, F5XCResource
from diagram_generator.utils import create_http_session_with_retries, get_logger

logger = get_logger(__name__)


class F5XCCollector:
    """Collects and parses F5 Distributed Cloud resources via REST API."""

    def __init__(
        self,
        tenant: str,
        auth_method: F5XCAuthMethod = F5XCAuthMethod.API_TOKEN,
        api_token: Optional[str] = None,
        p12_cert_path: Optional[str] = None,
        p12_password: Optional[str] = None,
        cert_path: Optional[str] = None,
        key_path: Optional[str] = None,
    ):
        """
        Initialize F5 XC REST API collector.

        Args:
            tenant: F5 XC tenant name
            auth_method: Authentication method to use
            api_token: API token (required if using API_TOKEN auth)
            p12_cert_path: Path to P12 certificate file (for P12_CERTIFICATE auth if cert/key not provided)
            p12_password: Password for P12 certificate
            cert_path: Path to PEM certificate file (alternative to P12, for P12_CERTIFICATE auth)
            key_path: Path to PEM key file (alternative to P12, for P12_CERTIFICATE auth)

        Raises:
            AuthenticationError: If authentication configuration is invalid
        """
        self.tenant = tenant
        self.auth_method = auth_method
        self.base_url = f"https://{tenant}.console.ves.volterra.io/api"

        if auth_method == F5XCAuthMethod.API_TOKEN:
            if not api_token:
                raise AuthenticationError("API token required for API_TOKEN auth method")
            self.api_token = api_token
            self.session = self._initialize_token_session()
        elif auth_method == F5XCAuthMethod.CERTIFICATE:
            # Certificate authentication using pre-extracted cert/key files
            if not (cert_path and key_path):
                raise AuthenticationError("CERTIFICATE auth requires both cert_path and key_path")
            self.cert_path = cert_path
            self.key_path = key_path
            logger.info("Using certificate and key files for authentication")
            self.session = self._initialize_cert_session()
        elif auth_method == F5XCAuthMethod.P12_CERTIFICATE:
            # P12 certificate extraction
            if not p12_cert_path:
                raise AuthenticationError("P12_CERTIFICATE auth requires p12_cert_path")
            self.p12_cert_path = p12_cert_path
            self.p12_password = p12_password
            logger.info("Will extract certificate and key from P12 file")
            self.session = self._initialize_cert_session()

        logger.info(
            "F5 XC collector initialized",
            tenant=tenant,
            auth_method=auth_method.value,
        )

    def _initialize_token_session(self) -> requests.Session:
        """
        Initialize HTTP session with API token authentication.

        Returns:
            Configured requests Session
        """
        session = create_http_session_with_retries()
        session.headers.update(
            {
                "Authorization": f"APIToken {self.api_token}",
                "Content-Type": "application/json",
            }
        )
        return session

    def _initialize_cert_session(self) -> requests.Session:
        """
        Initialize HTTP session with certificate authentication.

        Uses pre-extracted cert/key files if available, otherwise extracts from P12.

        Returns:
            Configured requests Session

        Raises:
            AuthenticationError: If certificate processing fails
        """
        try:
            # Use pre-extracted cert/key if provided, otherwise extract from P12
            if hasattr(self, "cert_path") and hasattr(self, "key_path"):
                cert_path = self.cert_path
                key_path = self.key_path
                logger.info(
                    "Using provided certificate and key files", cert=cert_path, key=key_path
                )
            else:
                # Extract cert and key from P12 file
                cert_path, key_path = self._extract_p12_certificate()
                logger.info("Extracted certificate and key from P12 file")

            # Verify files exist
            from pathlib import Path

            if not Path(cert_path).exists():
                raise AuthenticationError(f"Certificate file not found: {cert_path}")
            if not Path(key_path).exists():
                raise AuthenticationError(f"Key file not found: {key_path}")

            session = create_http_session_with_retries()
            session.cert = (cert_path, key_path)
            session.headers.update({"Content-Type": "application/json"})

            return session

        except Exception as e:
            logger.error("Failed to initialize certificate authentication", error=str(e))
            raise AuthenticationError(
                f"Certificate authentication initialization failed: {e}"
            ) from e

    def _extract_p12_certificate(self) -> tuple[str, str]:
        """
        Extract certificate and key from P12 file.

        Returns:
            Tuple of (cert_path, key_path)

        Raises:
            AuthenticationError: If extraction fails
        """
        import subprocess

        try:
            # Create temporary files for cert and key
            temp_dir = Path(tempfile.gettempdir())
            cert_path = temp_dir / "f5xc_cert.pem"
            key_path = temp_dir / "f5xc_key.pem"

            # Extract certificate (with legacy provider for OpenSSL 3.x compatibility)
            subprocess.run(
                [
                    "openssl",
                    "pkcs12",
                    "-in",
                    self.p12_cert_path,
                    "-clcerts",
                    "-nokeys",
                    "-out",
                    str(cert_path),
                    "-passin",
                    f"pass:{self.p12_password or ''}",
                    "-legacy",  # Support legacy algorithms like RC2-40-CBC
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            # Extract private key (with legacy provider for OpenSSL 3.x compatibility)
            subprocess.run(
                [
                    "openssl",
                    "pkcs12",
                    "-in",
                    self.p12_cert_path,
                    "-nocerts",
                    "-nodes",
                    "-out",
                    str(key_path),
                    "-passin",
                    f"pass:{self.p12_password or ''}",
                    "-legacy",  # Support legacy algorithms like RC2-40-CBC
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            logger.info("P12 certificate extracted successfully")
            return str(cert_path), str(key_path)

        except subprocess.CalledProcessError as e:
            raise AuthenticationError(f"Failed to extract P12 certificate: {e.stderr}") from e
        except FileNotFoundError as e:
            raise AuthenticationError(
                "openssl command not found - ensure OpenSSL is installed"
            ) from e

    def _make_request(self, endpoint: str, namespace: str = "system") -> dict:
        """
        Make authenticated request to F5 XC API.

        Args:
            endpoint: API endpoint path (may contain {namespace} placeholder)
            namespace: F5 XC namespace (default: system)

        Returns:
            JSON response data

        Raises:
            F5XCAPIError: If API request fails
        """
        # Replace {namespace} placeholder in endpoint with actual namespace value
        endpoint = endpoint.replace("{namespace}", namespace)
        url = f"{self.base_url}/{endpoint}"
        params = {"namespace": namespace}

        try:
            logger.debug("Making F5 XC API request", url=url, namespace=namespace)
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error("F5 XC API HTTP error", status=e.response.status_code, error=str(e))
            raise F5XCAPIError(f"F5 XC API request failed: {e}") from e
        except requests.exceptions.RequestException as e:
            logger.error("F5 XC API request error", error=str(e))
            raise F5XCAPIError(f"F5 XC API request error: {e}") from e

    def collect_resources(self, namespace: str = "system") -> list[F5XCResource]:
        """
        Collect all F5 XC resources from multiple resource types.

        Args:
            namespace: F5 XC namespace to query (default: system)

        Returns:
            List of F5 XC resources

        Raises:
            F5XCAPIError: If collection fails
        """
        logger.info("Collecting F5 XC resources", namespace=namespace)

        try:
            resources = []

            # Collect HTTP load balancers
            resources.extend(self.collect_http_loadbalancers(namespace))

            # Collect origin pools
            resources.extend(self.collect_origin_pools(namespace))

            # Collect virtual sites
            resources.extend(self.collect_virtual_sites(namespace))

            # Collect sites
            resources.extend(self.collect_sites())

            logger.info("F5 XC resources collected", count=len(resources), namespace=namespace)
            return resources

        except Exception as e:
            logger.error("Failed to collect F5 XC resources", error=str(e))
            raise F5XCAPIError(f"Failed to collect F5 XC resources: {e}") from e

    def collect_http_loadbalancers(self, namespace: str = "system") -> list[F5XCResource]:
        """
        Collect HTTP load balancers.

        Args:
            namespace: F5 XC namespace

        Returns:
            List of HTTP load balancer resources
        """
        logger.info("Collecting HTTP load balancers", namespace=namespace)

        try:
            response = self._make_request(
                "config/namespaces/{namespace}/http_loadbalancers", namespace
            )
            items = response.get("items", [])

            resources = []
            for item in items:
                metadata = item.get("metadata", {})
                spec = item.get("spec", {})

                resource = F5XCResource(
                    type="http_loadbalancer",
                    namespace=namespace,
                    name=metadata.get("name", "unknown"),
                    spec=spec,
                    metadata=metadata,
                )
                resources.append(resource)
                logger.debug("Collected HTTP load balancer", name=resource.name)

            return resources

        except Exception as e:
            logger.warning("Failed to collect HTTP load balancers", error=str(e))
            return []

    def collect_origin_pools(self, namespace: str = "system") -> list[F5XCResource]:
        """
        Collect origin pools.

        Args:
            namespace: F5 XC namespace

        Returns:
            List of origin pool resources
        """
        logger.info("Collecting origin pools", namespace=namespace)

        try:
            response = self._make_request("config/namespaces/{namespace}/origin_pools", namespace)
            items = response.get("items", [])

            resources = []
            for item in items:
                metadata = item.get("metadata", {})
                spec = item.get("spec", {})

                resource = F5XCResource(
                    type="origin_pool",
                    namespace=namespace,
                    name=metadata.get("name", "unknown"),
                    spec=spec,
                    metadata=metadata,
                )
                resources.append(resource)
                logger.debug("Collected origin pool", name=resource.name)

            return resources

        except Exception as e:
            logger.warning("Failed to collect origin pools", error=str(e))
            return []

    def collect_virtual_sites(self, namespace: str = "system") -> list[F5XCResource]:
        """
        Collect virtual sites.

        Args:
            namespace: F5 XC namespace

        Returns:
            List of virtual site resources
        """
        logger.info("Collecting virtual sites", namespace=namespace)

        try:
            response = self._make_request("config/namespaces/{namespace}/virtual_sites", namespace)
            items = response.get("items", [])

            resources = []
            for item in items:
                metadata = item.get("metadata", {})
                spec = item.get("spec", {})

                resource = F5XCResource(
                    type="virtual_site",
                    namespace=namespace,
                    name=metadata.get("name", "unknown"),
                    spec=spec,
                    metadata=metadata,
                )
                resources.append(resource)
                logger.debug("Collected virtual site", name=resource.name)

            return resources

        except Exception as e:
            logger.warning("Failed to collect virtual sites", error=str(e))
            return []

    def collect_sites(self) -> list[F5XCResource]:
        """
        Collect sites (physical or edge sites).

        Returns:
            List of site resources
        """
        logger.info("Collecting sites")

        try:
            response = self._make_request("config/namespaces/system/sites", "system")
            items = response.get("items", [])

            resources = []
            for item in items:
                metadata = item.get("metadata", {})
                spec = item.get("spec", {})

                resource = F5XCResource(
                    type="site",
                    namespace="system",
                    name=metadata.get("name", "unknown"),
                    spec=spec,
                    metadata=metadata,
                )
                resources.append(resource)
                logger.debug("Collected site", name=resource.name)

            return resources

        except Exception as e:
            logger.warning("Failed to collect sites", error=str(e))
            return []

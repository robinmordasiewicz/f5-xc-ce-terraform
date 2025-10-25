"""
Tests for F5 XC REST API collector.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from diagram_generator.exceptions import AuthenticationError, F5XCAPIError
from diagram_generator.f5xc_collector import F5XCCollector
from diagram_generator.models import F5XCAuthMethod


def test_f5xc_collector_init_with_token():
    """Test F5XCCollector initialization with API token."""
    collector = F5XCCollector(
        tenant="test-tenant",
        auth_method=F5XCAuthMethod.API_TOKEN,
        api_token="test-token",
    )
    assert collector.tenant == "test-tenant"
    assert collector.api_token == "test-token"
    assert collector.base_url == "https://test-tenant.console.ves.volterra.io/api"


def test_f5xc_collector_init_without_token():
    """Test initialization fails without required API token."""
    with pytest.raises(AuthenticationError, match="API token required"):
        F5XCCollector(
            tenant="test-tenant",
            auth_method=F5XCAuthMethod.API_TOKEN,
        )


def test_f5xc_collector_init_with_p12():
    """Test initialization with P12 certificate."""
    with patch.object(F5XCCollector, "_extract_p12_certificate") as mock_extract:
        mock_extract.return_value = ("/tmp/cert.pem", "/tmp/key.pem")

        collector = F5XCCollector(
            tenant="test-tenant",
            auth_method=F5XCAuthMethod.P12_CERTIFICATE,
            p12_cert_path="/path/to/cert.p12",
            p12_password="password",
        )
        assert collector.tenant == "test-tenant"
        assert mock_extract.called


def test_f5xc_collector_init_without_p12():
    """Test initialization fails without P12 certificate path."""
    with pytest.raises(AuthenticationError, match="P12 certificate path required"):
        F5XCCollector(
            tenant="test-tenant",
            auth_method=F5XCAuthMethod.P12_CERTIFICATE,
        )


def test_token_session_headers():
    """Test that token session has correct headers."""
    collector = F5XCCollector(
        tenant="test-tenant",
        auth_method=F5XCAuthMethod.API_TOKEN,
        api_token="test-token",
    )

    assert "Authorization" in collector.session.headers
    assert collector.session.headers["Authorization"] == "APIToken test-token"
    assert collector.session.headers["Content-Type"] == "application/json"


def test_collect_resources_success(mock_f5xc_session):
    """Test successful resource collection."""
    with patch("diagram_generator.f5xc_collector.create_http_session_with_retries") as mock_session:
        mock_session.return_value = mock_f5xc_session

        collector = F5XCCollector(
            tenant="test-tenant",
            auth_method=F5XCAuthMethod.API_TOKEN,
            api_token="test-token",
        )

        # Mock all collection methods
        with patch.object(collector, "collect_http_loadbalancers", return_value=[]):
            with patch.object(collector, "collect_origin_pools", return_value=[]):
                with patch.object(collector, "collect_virtual_sites", return_value=[]):
                    with patch.object(collector, "collect_sites", return_value=[]):
                        resources = collector.collect_resources()

        assert isinstance(resources, list)


def test_make_request_success():
    """Test successful API request."""
    with patch(
        "diagram_generator.f5xc_collector.create_http_session_with_retries"
    ) as mock_session_fn:
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response
        mock_session_fn.return_value = mock_session

        collector = F5XCCollector(
            tenant="test-tenant",
            auth_method=F5XCAuthMethod.API_TOKEN,
            api_token="test-token",
        )

        result = collector._make_request("test/endpoint", namespace="production")

        assert result == {"test": "data"}
        assert mock_session.get.called


def test_make_request_http_error():
    """Test handling of HTTP errors."""
    with patch(
        "diagram_generator.f5xc_collector.create_http_session_with_retries"
    ) as mock_session_fn:
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Not found")
        mock_session.get.return_value = mock_response
        mock_session_fn.return_value = mock_session

        collector = F5XCCollector(
            tenant="test-tenant",
            auth_method=F5XCAuthMethod.API_TOKEN,
            api_token="test-token",
        )

        with pytest.raises(F5XCAPIError, match="F5 XC API request failed"):
            collector._make_request("test/endpoint")


def test_make_request_timeout():
    """Test handling of request timeout."""
    with patch(
        "diagram_generator.f5xc_collector.create_http_session_with_retries"
    ) as mock_session_fn:
        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.Timeout("Timeout")
        mock_session_fn.return_value = mock_session

        collector = F5XCCollector(
            tenant="test-tenant",
            auth_method=F5XCAuthMethod.API_TOKEN,
            api_token="test-token",
        )

        with pytest.raises(F5XCAPIError, match="F5 XC API request error"):
            collector._make_request("test/endpoint")


def test_collect_http_loadbalancers():
    """Test HTTP load balancer collection."""
    with patch(
        "diagram_generator.f5xc_collector.create_http_session_with_retries"
    ) as mock_session_fn:
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [
                {
                    "metadata": {"name": "lb-test"},
                    "spec": {"domains": ["example.com"]},
                }
            ]
        }
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response
        mock_session_fn.return_value = mock_session

        collector = F5XCCollector(
            tenant="test-tenant",
            auth_method=F5XCAuthMethod.API_TOKEN,
            api_token="test-token",
        )

        resources = collector.collect_http_loadbalancers("production")

        assert len(resources) == 1
        assert resources[0].type == "http_loadbalancer"
        assert resources[0].name == "lb-test"


def test_collect_origin_pools():
    """Test origin pool collection."""
    with patch(
        "diagram_generator.f5xc_collector.create_http_session_with_retries"
    ) as mock_session_fn:
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [
                {
                    "metadata": {"name": "pool-test"},
                    "spec": {"origin_servers": []},
                }
            ]
        }
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response
        mock_session_fn.return_value = mock_session

        collector = F5XCCollector(
            tenant="test-tenant",
            auth_method=F5XCAuthMethod.API_TOKEN,
            api_token="test-token",
        )

        resources = collector.collect_origin_pools("production")

        assert len(resources) == 1
        assert resources[0].type == "origin_pool"
        assert resources[0].name == "pool-test"


def test_collect_virtual_sites():
    """Test virtual site collection."""
    with patch(
        "diagram_generator.f5xc_collector.create_http_session_with_retries"
    ) as mock_session_fn:
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [
                {
                    "metadata": {"name": "vsite-test"},
                    "spec": {"site_type": "REGIONAL_EDGE"},
                }
            ]
        }
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response
        mock_session_fn.return_value = mock_session

        collector = F5XCCollector(
            tenant="test-tenant",
            auth_method=F5XCAuthMethod.API_TOKEN,
            api_token="test-token",
        )

        resources = collector.collect_virtual_sites("production")

        assert len(resources) == 1
        assert resources[0].type == "virtual_site"
        assert resources[0].name == "vsite-test"


def test_collect_sites():
    """Test site collection."""
    with patch(
        "diagram_generator.f5xc_collector.create_http_session_with_retries"
    ) as mock_session_fn:
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [
                {
                    "metadata": {"name": "site-test"},
                    "spec": {"latitude": 37.7749, "longitude": -122.4194},
                }
            ]
        }
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response
        mock_session_fn.return_value = mock_session

        collector = F5XCCollector(
            tenant="test-tenant",
            auth_method=F5XCAuthMethod.API_TOKEN,
            api_token="test-token",
        )

        resources = collector.collect_sites()

        assert len(resources) == 1
        assert resources[0].type == "site"
        assert resources[0].name == "site-test"


def test_collection_handles_api_failure():
    """Test that collection methods handle API failures gracefully."""
    with patch(
        "diagram_generator.f5xc_collector.create_http_session_with_retries"
    ) as mock_session_fn:
        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.RequestException("API Error")
        mock_session_fn.return_value = mock_session

        collector = F5XCCollector(
            tenant="test-tenant",
            auth_method=F5XCAuthMethod.API_TOKEN,
            api_token="test-token",
        )

        # Should return empty list instead of raising
        resources = collector.collect_http_loadbalancers()
        assert resources == []


def test_extract_p12_certificate_success():
    """Test successful P12 certificate extraction."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0)

        with patch("diagram_generator.f5xc_collector.create_http_session_with_retries"):
            collector = F5XCCollector(
                tenant="test-tenant",
                auth_method=F5XCAuthMethod.API_TOKEN,
                api_token="test-token",
            )

            cert_path, key_path = collector._extract_p12_certificate()

            assert cert_path.endswith("f5xc_cert.pem")
            assert key_path.endswith("f5xc_key.pem")


def test_extract_p12_certificate_openssl_not_found():
    """Test P12 extraction when OpenSSL not installed."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("openssl not found")

        with patch("diagram_generator.f5xc_collector.create_http_session_with_retries"):
            collector = F5XCCollector(
                tenant="test-tenant",
                auth_method=F5XCAuthMethod.API_TOKEN,
                api_token="test-token",
            )

            with pytest.raises(AuthenticationError, match="openssl command not found"):
                collector._extract_p12_certificate()

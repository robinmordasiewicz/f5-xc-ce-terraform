"""
Lucidchart OAuth 2.0 authentication client.

Handles OAuth flow, token management, and refresh logic.
"""

import http.server
import json
import secrets
import socketserver
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Optional

import requests

from diagram_generator.exceptions import AuthenticationError
from diagram_generator.utils import get_logger

logger = get_logger(__name__)


class LucidAuthClient:
    """Handles Lucidchart OAuth 2.0 authentication."""

    AUTH_URL = "https://lucid.app/oauth2/authorize"
    TOKEN_URL = (
        "https://api.lucid.co/oauth2/token"  # nosec B105 - Public API endpoint URL, not password
    )
    TOKEN_CACHE_FILE = Path.home() / ".lucid_token_cache.json"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://localhost:8080/callback",
    ):
        """
        Initialize Lucid OAuth client.

        Args:
            client_id: Lucidchart OAuth client ID
            client_secret: Lucidchart OAuth client secret
            redirect_uri: OAuth redirect URI (must match app configuration)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

        logger.info("Lucid OAuth client initialized", redirect_uri=redirect_uri)

    def authenticate(self, force_reauth: bool = False) -> str:
        """
        Authenticate with Lucidchart and obtain access token.

        Args:
            force_reauth: Force re-authentication even if cached token exists

        Returns:
            Access token

        Raises:
            AuthenticationError: If authentication fails
        """
        # Try to load cached token
        if not force_reauth and self._load_cached_token():
            logger.info("Using cached Lucid access token")
            return self.access_token

        # Perform OAuth flow
        logger.info("Starting Lucid OAuth flow")

        try:
            # Generate state for CSRF protection
            state = secrets.token_urlsafe(32)

            # Start authorization flow
            auth_code = self._get_authorization_code(state)

            # Exchange authorization code for tokens
            self._exchange_code_for_tokens(auth_code)

            # Cache tokens
            self._cache_tokens()

            logger.info("Lucid authentication successful")
            return self.access_token

        except Exception as e:
            logger.error("Lucid authentication failed", error=str(e))
            raise AuthenticationError(f"Lucid OAuth failed: {e}") from e

    def _get_authorization_code(self, state: str) -> str:
        """
        Get authorization code via browser-based OAuth flow.

        Args:
            state: CSRF protection state

        Returns:
            Authorization code

        Raises:
            AuthenticationError: If authorization fails
        """
        # Build authorization URL
        auth_params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": "lucidchart.document.content lucidchart.document.create",
        }
        auth_url = f"{self.AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

        # Open browser for user authorization
        logger.info("Opening browser for authorization")
        webbrowser.open(auth_url)

        # Start local server to receive callback
        callback_data = {}

        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                # Parse query parameters
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)

                # Store callback data
                callback_data["code"] = params.get("code", [None])[0]
                callback_data["state"] = params.get("state", [None])[0]
                callback_data["error"] = params.get("error", [None])[0]

                # Send response
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                if callback_data["code"]:
                    html = "<html><body><h1>Authentication successful!</h1><p>You can close this window.</p></body></html>"
                else:
                    html = f"<html><body><h1>Authentication failed!</h1><p>Error: {callback_data['error']}</p></body></html>"

                self.wfile.write(html.encode())

            def log_message(self, format, *args):
                # Suppress logging
                pass

        # Parse port from redirect URI
        parsed = urllib.parse.urlparse(self.redirect_uri)
        port = parsed.port or 8080

        # Start server
        with socketserver.TCPServer(("", port), CallbackHandler) as httpd:
            logger.info(f"Waiting for OAuth callback on port {port}")
            httpd.handle_request()

        # Validate response
        if callback_data.get("error"):
            raise AuthenticationError(f"OAuth authorization failed: {callback_data['error']}")

        if not callback_data.get("code"):
            raise AuthenticationError("No authorization code received")

        if callback_data.get("state") != state:
            raise AuthenticationError("State mismatch - possible CSRF attack")

        return callback_data["code"]

    def _exchange_code_for_tokens(self, auth_code: str) -> None:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            auth_code: Authorization code from OAuth flow

        Raises:
            AuthenticationError: If token exchange fails
        """
        token_data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            response = requests.post(self.TOKEN_URL, data=token_data, timeout=30)
            response.raise_for_status()

            tokens = response.json()
            self.access_token = tokens.get("access_token")
            self.refresh_token = tokens.get("refresh_token")

            if not self.access_token:
                raise AuthenticationError("No access token in response")

            logger.info("Tokens obtained successfully")

        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Token exchange failed: {e}") from e

    def refresh_access_token(self) -> str:
        """
        Refresh access token using refresh token.

        Returns:
            New access token

        Raises:
            AuthenticationError: If refresh fails
        """
        if not self.refresh_token:
            raise AuthenticationError("No refresh token available")

        logger.info("Refreshing Lucid access token")

        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            response = requests.post(self.TOKEN_URL, data=token_data, timeout=30)
            response.raise_for_status()

            tokens = response.json()
            self.access_token = tokens.get("access_token")

            # Update refresh token if provided
            if tokens.get("refresh_token"):
                self.refresh_token = tokens["refresh_token"]

            # Update cache
            self._cache_tokens()

            logger.info("Access token refreshed successfully")
            return self.access_token

        except requests.exceptions.RequestException as e:
            logger.error("Token refresh failed", error=str(e))
            raise AuthenticationError(f"Token refresh failed: {e}") from e

    def _cache_tokens(self) -> None:
        """Save tokens to cache file."""
        try:
            cache_data = {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
            }

            self.TOKEN_CACHE_FILE.write_text(json.dumps(cache_data, indent=2))
            logger.debug("Tokens cached", cache_file=str(self.TOKEN_CACHE_FILE))

        except Exception as e:
            logger.warning("Failed to cache tokens", error=str(e))

    def _load_cached_token(self) -> bool:
        """
        Load tokens from cache file.

        Returns:
            True if tokens loaded successfully, False otherwise
        """
        try:
            if not self.TOKEN_CACHE_FILE.exists():
                return False

            cache_data = json.loads(self.TOKEN_CACHE_FILE.read_text())
            self.access_token = cache_data.get("access_token")
            self.refresh_token = cache_data.get("refresh_token")

            if not self.access_token:
                return False

            # Try to validate token by making test API call
            if self._validate_token():
                return True

            # Token invalid, try refresh
            if self.refresh_token:
                try:
                    self.refresh_access_token()
                    return True
                except AuthenticationError:
                    pass

            return False

        except Exception as e:
            logger.warning("Failed to load cached tokens", error=str(e))
            return False

    def _validate_token(self) -> bool:
        """
        Validate access token by making test API call.

        Returns:
            True if token is valid, False otherwise
        """
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(
                "https://api.lucid.co/documents",
                headers=headers,
                timeout=10,
            )
            return response.status_code == 200
        except Exception:
            return False

    def get_auth_header(self) -> dict[str, str]:
        """
        Get authorization header for API requests.

        Returns:
            Dictionary with Authorization header

        Raises:
            AuthenticationError: If no valid token available
        """
        if not self.access_token:
            raise AuthenticationError("No access token available - authenticate first")

        return {"Authorization": f"Bearer {self.access_token}"}

"""OAuth2 Authorization Code + PKCE flow with localhost callback."""

from __future__ import annotations

import hashlib
import secrets
import socket
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event, Thread
from typing import Optional

import httpx

from ..config.environments import Credentials, Environment
from ..config.settings import (
    OAUTH_CALLBACK_HOST,
    OAUTH_CALLBACK_PATH,
    OAUTH_CALLBACK_PORT_RANGE,
    OAUTH_SCOPES,
)


class OAuthError(Exception):
    """Raised when the OAuth flow fails."""


def _generate_pkce_pair() -> tuple[str, str]:
    """Generate a PKCE code_verifier and code_challenge (S256)."""
    import base64

    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def _find_available_port() -> int:
    """Find an available port in the configured range."""
    for port in range(*OAUTH_CALLBACK_PORT_RANGE):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((OAUTH_CALLBACK_HOST, port))
                return port
        except OSError:
            continue
    raise OAuthError(
        f"No available port found in range "
        f"{OAUTH_CALLBACK_PORT_RANGE[0]}-{OAUTH_CALLBACK_PORT_RANGE[1]}. "
        "Close other applications or adjust CC_CALLBACK_PORT_RANGE."
    )


class _CallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler that captures the OAuth callback."""

    auth_code: Optional[str] = None
    error: Optional[str] = None
    received = Event()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path != OAUTH_CALLBACK_PATH:
            self.send_response(404)
            self.end_headers()
            return

        if "error" in params:
            _CallbackHandler.error = params["error"][0]
            error_desc = params.get("error_description", ["Unknown error"])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                f"<html><body><h2>Authentication Failed</h2>"
                f"<p>{error_desc}</p>"
                f"<p>You can close this window.</p></body></html>".encode()
            )
            _CallbackHandler.received.set()
            return

        if "code" in params:
            _CallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2>Authentication Successful</h2>"
                b"<p>You can close this window and return to the terminal.</p>"
                b"</body></html>"
            )
            _CallbackHandler.received.set()
            return

        self.send_response(400)
        self.end_headers()

    def log_message(self, format, *args):
        # Suppress default HTTP server logging
        pass


def perform_oauth_login(
    environment: Environment,
    scopes: str | None = None,
) -> Credentials:
    """Run the full OAuth2 Authorization Code + PKCE flow.

    1. Start a localhost HTTP server for the callback
    2. Open the browser to the authorization URL
    3. Wait for the callback with the auth code
    4. Exchange the auth code for tokens
    5. Return Credentials

    Args:
        environment: The CommCare HQ environment to authenticate against.
        scopes: OAuth scopes to request. Defaults to OAUTH_SCOPES.

    Returns:
        Credentials with access_token, refresh_token, etc.

    Raises:
        OAuthError: If the flow fails at any step.
    """
    if not environment.client_id:
        raise OAuthError(
            f"No OAuth client_id configured for environment '{environment.name}'. "
            f"Register an OAuth application on {environment.url} and run:\n"
            f"  cc env add {environment.name} {environment.url} --client-id YOUR_CLIENT_ID"
        )

    scopes = scopes or OAUTH_SCOPES
    code_verifier, code_challenge = _generate_pkce_pair()
    state = secrets.token_urlsafe(32)

    # Find a port and build the redirect URI
    port = _find_available_port()
    redirect_uri = f"http://{OAUTH_CALLBACK_HOST}:{port}{OAUTH_CALLBACK_PATH}"

    # Reset handler state
    _CallbackHandler.auth_code = None
    _CallbackHandler.error = None
    _CallbackHandler.received = Event()

    # Start the callback server
    server = HTTPServer((OAUTH_CALLBACK_HOST, port), _CallbackHandler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        # Build the authorization URL
        auth_params = {
            "response_type": "code",
            "client_id": environment.client_id,
            "redirect_uri": redirect_uri,
            "scope": scopes,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        auth_url = (
            f"{environment.oauth_authorize_url()}?"
            f"{urllib.parse.urlencode(auth_params)}"
        )

        # Open the browser
        print("Opening browser for authentication...")
        print(f"If the browser doesn't open, visit:\n  {auth_url}\n")
        webbrowser.open(auth_url)

        # Wait for the callback (timeout after 5 minutes)
        if not _CallbackHandler.received.wait(timeout=300):
            raise OAuthError("Authentication timed out after 5 minutes.")

        if _CallbackHandler.error:
            raise OAuthError(f"Authentication failed: {_CallbackHandler.error}")

        if not _CallbackHandler.auth_code:
            raise OAuthError("No authorization code received.")

        auth_code = _CallbackHandler.auth_code

        # Exchange the auth code for tokens
        token_data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": redirect_uri,
            "client_id": environment.client_id,
            "code_verifier": code_verifier,
        }

        with httpx.Client() as client:
            response = client.post(
                environment.oauth_token_url(),
                data=token_data,
                headers={"Accept": "application/json"},
            )

        if response.status_code != 200:
            error_detail = response.text
            raise OAuthError(
                f"Token exchange failed (HTTP {response.status_code}): {error_detail}"
            )

        token_response = response.json()
        expires_in = token_response.get("expires_in", 900)

        return Credentials(
            access_token=token_response["access_token"],
            refresh_token=token_response.get("refresh_token", ""),
            expires_at=time.time() + expires_in,
            user="",  # Will be populated by a whoami call
            scopes=token_response.get("scope", scopes).split(),
        )

    finally:
        server.shutdown()


def refresh_access_token(
    environment: Environment,
    credentials: Credentials,
) -> Credentials:
    """Use the refresh token to get a new access token.

    Args:
        environment: The CommCare HQ environment.
        credentials: Current credentials with a valid refresh_token.

    Returns:
        Updated Credentials with new access_token and expires_at.

    Raises:
        OAuthError: If the refresh fails (user may need to re-login).
    """
    if not credentials.refresh_token:
        raise OAuthError("No refresh token available. Run 'cc auth login' to authenticate.")

    token_data = {
        "grant_type": "refresh_token",
        "refresh_token": credentials.refresh_token,
        "client_id": environment.client_id,
    }

    with httpx.Client() as client:
        response = client.post(
            environment.oauth_token_url(),
            data=token_data,
            headers={"Accept": "application/json"},
        )

    if response.status_code != 200:
        raise OAuthError(
            f"Token refresh failed (HTTP {response.status_code}). "
            "Your session may have expired. Run 'cc auth login' to re-authenticate."
        )

    token_response = response.json()
    expires_in = token_response.get("expires_in", 900)

    return Credentials(
        access_token=token_response["access_token"],
        refresh_token=token_response.get("refresh_token", credentials.refresh_token),
        expires_at=time.time() + expires_in,
        user=credentials.user,
        scopes=token_response.get("scope", " ".join(credentials.scopes)).split(),
    )


def revoke_token(environment: Environment, credentials: Credentials) -> None:
    """Revoke the access token on the server."""
    if not credentials.access_token:
        return

    try:
        with httpx.Client() as client:
            client.post(
                environment.oauth_revoke_url(),
                data={
                    "token": credentials.access_token,
                    "client_id": environment.client_id,
                },
            )
    except httpx.HTTPError:
        # Best-effort revocation -- don't fail if server is unreachable
        pass

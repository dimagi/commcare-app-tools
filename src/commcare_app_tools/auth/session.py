"""Authenticated HTTP session with automatic token refresh."""

from __future__ import annotations

import time
from typing import Any

import httpx

from ..config.environments import ConfigManager
from .oauth import OAuthError, refresh_access_token
from .token_store import REFRESH_BUFFER_SECONDS


class AuthenticatedClient:
    """An httpx-based HTTP client that automatically injects OAuth Bearer tokens
    and refreshes them when they expire.

    Usage:
        config = ConfigManager()
        client = AuthenticatedClient(config)
        response = client.get("/a/my-domain/api/case/v2/")
    """

    def __init__(
        self,
        config: ConfigManager,
        env_name: str | None = None,
    ):
        self.config = config
        self.env_name = env_name or config.get_active_environment_name()
        self._env = config.get_environment(self.env_name)
        self._creds = config.get_credentials(self.env_name)
        self._client = httpx.Client(
            base_url=self._env.url,
            timeout=30.0,
            follow_redirects=True,
        )

    def _ensure_valid_token(self) -> str:
        """Ensure we have a valid access token, refreshing if needed."""
        if not self._creds.is_authenticated:
            raise OAuthError(
                f"Not authenticated for environment '{self.env_name}'. "
                "Run 'cc auth login' to authenticate."
            )

        if self._creds.expires_at <= time.time() + REFRESH_BUFFER_SECONDS:
            self._creds = refresh_access_token(self._env, self._creds)
            self.config.save_credentials(self.env_name, self._creds)

        return self._creds.access_token

    def _auth_headers(self) -> dict[str, str]:
        token = self._ensure_valid_token()
        # Support API key tokens (stored as "ApiKey user:key")
        if token.startswith("ApiKey "):
            return {"Authorization": token}
        return {"Authorization": f"Bearer {token}"}

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make an authenticated GET request."""
        headers = {**self._auth_headers(), **kwargs.pop("headers", {})}
        return self._client.get(path, headers=headers, **kwargs)

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make an authenticated POST request."""
        headers = {**self._auth_headers(), **kwargs.pop("headers", {})}
        return self._client.post(path, headers=headers, **kwargs)

    def put(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make an authenticated PUT request."""
        headers = {**self._auth_headers(), **kwargs.pop("headers", {})}
        return self._client.put(path, headers=headers, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make an authenticated DELETE request."""
        headers = {**self._auth_headers(), **kwargs.pop("headers", {})}
        return self._client.delete(path, headers=headers, **kwargs)

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

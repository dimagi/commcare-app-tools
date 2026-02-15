"""Token storage and retrieval, with automatic refresh."""

from __future__ import annotations

import time

from ..config.environments import ConfigManager, Credentials
from .oauth import OAuthError, refresh_access_token

# Buffer before expiry to trigger refresh (60 seconds)
REFRESH_BUFFER_SECONDS = 60


def get_valid_credentials(
    config: ConfigManager,
    env_name: str | None = None,
) -> Credentials:
    """Get credentials for an environment, refreshing if needed.

    Args:
        config: The ConfigManager instance.
        env_name: Environment name. Uses active environment if None.

    Returns:
        Valid Credentials with a non-expired access token.

    Raises:
        OAuthError: If no credentials exist or refresh fails.
    """
    if env_name is None:
        env_name = config.get_active_environment_name()

    creds = config.get_credentials(env_name)

    if not creds.is_authenticated:
        raise OAuthError(
            f"Not authenticated for environment '{env_name}'. "
            "Run 'cc auth login' to authenticate."
        )

    # Check if token needs refresh
    if creds.expires_at <= time.time() + REFRESH_BUFFER_SECONDS:
        env = config.get_environment(env_name)
        creds = refresh_access_token(env, creds)
        config.save_credentials(env_name, creds)

    return creds


def is_authenticated(config: ConfigManager, env_name: str | None = None) -> bool:
    """Check if we have stored credentials for an environment."""
    if env_name is None:
        env_name = config.get_active_environment_name()
    creds = config.get_credentials(env_name)
    return creds.is_authenticated


def token_status(
    config: ConfigManager,
    env_name: str | None = None,
) -> dict:
    """Get a summary of the authentication status for an environment.

    Returns a dict with keys: authenticated, user, environment, expires_in, scopes.
    """
    if env_name is None:
        env_name = config.get_active_environment_name()

    creds = config.get_credentials(env_name)
    env = config.get_environment(env_name)

    if not creds.is_authenticated:
        return {
            "authenticated": False,
            "user": "",
            "environment": env_name,
            "url": env.url,
            "expires_in": 0,
            "scopes": [],
        }

    expires_in = max(0, int(creds.expires_at - time.time()))

    return {
        "authenticated": True,
        "user": creds.user or "(unknown)",
        "environment": env_name,
        "url": env.url,
        "expires_in": expires_in,
        "scopes": creds.scopes,
    }

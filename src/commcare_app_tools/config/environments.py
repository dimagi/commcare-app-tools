"""Environment management -- read/write config and credential files."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .settings import (
    CONFIG_FILE,
    CREDENTIALS_FILE,
    DEFAULT_ACTIVE_ENVIRONMENT,
    DEFAULT_ENVIRONMENTS,
)


@dataclass
class Environment:
    """A CommCare HQ environment configuration."""

    name: str
    url: str
    client_id: str = ""
    formplayer_url: Optional[str] = None

    def oauth_authorize_url(self) -> str:
        return f"{self.url.rstrip('/')}/oauth/authorize/"

    def oauth_token_url(self) -> str:
        return f"{self.url.rstrip('/')}/oauth/token/"

    def oauth_revoke_url(self) -> str:
        return f"{self.url.rstrip('/')}/oauth/revoke_token/"

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "client_id": self.client_id,
            "formplayer_url": self.formplayer_url,
        }


@dataclass
class Credentials:
    """Stored OAuth tokens for a single environment."""

    access_token: str = ""
    refresh_token: str = ""
    expires_at: float = 0.0
    user: str = ""
    scopes: list[str] = field(default_factory=list)

    @property
    def is_authenticated(self) -> bool:
        return bool(self.access_token)

    def to_dict(self) -> dict:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "user": self.user,
            "scopes": self.scopes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Credentials:
        return cls(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", ""),
            expires_at=data.get("expires_at", 0.0),
            user=data.get("user", ""),
            scopes=data.get("scopes", []),
        )


class ConfigManager:
    """Manages environment configuration and credentials files.

    Config file (~/.commcare/config.json):
        Stores environment definitions and the active environment name.

    Credentials file (~/.commcare/credentials.json):
        Stores per-environment OAuth tokens. File permissions are
        restricted to owner-only on Unix systems.
    """

    def __init__(
        self,
        config_path: Path | None = None,
        credentials_path: Path | None = None,
    ):
        self.config_path = config_path or CONFIG_FILE
        self.credentials_path = credentials_path or CREDENTIALS_FILE

    # -- Config file operations --

    def _read_config(self) -> dict:
        if self.config_path.exists():
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        return {
            "active_environment": DEFAULT_ACTIVE_ENVIRONMENT,
            "environments": {
                name: env_data
                for name, env_data in DEFAULT_ENVIRONMENTS.items()
            },
        }

    def _write_config(self, config: dict) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(config, indent=2) + "\n",
            encoding="utf-8",
        )

    def get_active_environment_name(self) -> str:
        config = self._read_config()
        return config.get("active_environment", DEFAULT_ACTIVE_ENVIRONMENT)

    def get_active_environment(self) -> Environment:
        config = self._read_config()
        name = config.get("active_environment", DEFAULT_ACTIVE_ENVIRONMENT)
        return self._env_from_config(name, config)

    def get_environment(self, name: str) -> Environment:
        config = self._read_config()
        return self._env_from_config(name, config)

    def _env_from_config(self, name: str, config: dict) -> Environment:
        envs = config.get("environments", {})
        if name not in envs:
            raise ValueError(
                f"Environment '{name}' not found. "
                "Run 'cc env list' to see available environments."
            )
        env_data = envs[name]
        return Environment(
            name=name,
            url=env_data["url"],
            client_id=env_data.get("client_id", ""),
            formplayer_url=env_data.get("formplayer_url"),
        )

    def list_environments(self) -> list[Environment]:
        config = self._read_config()
        envs = config.get("environments", {})
        return [
            Environment(
                name=name,
                url=data["url"],
                client_id=data.get("client_id", ""),
                formplayer_url=data.get("formplayer_url"),
            )
            for name, data in envs.items()
        ]

    def add_environment(
        self,
        name: str,
        url: str,
        client_id: str = "",
        formplayer_url: str | None = None,
    ) -> Environment:
        config = self._read_config()
        envs = config.setdefault("environments", {})
        if name in envs:
            raise ValueError(f"Environment '{name}' already exists. Use 'cc env remove' first.")
        env = Environment(
            name=name,
            url=url.rstrip("/"),
            client_id=client_id,
            formplayer_url=formplayer_url,
        )
        envs[name] = env.to_dict()
        self._write_config(config)
        return env

    def remove_environment(self, name: str) -> None:
        config = self._read_config()
        envs = config.get("environments", {})
        if name not in envs:
            raise ValueError(f"Environment '{name}' not found.")
        if name in DEFAULT_ENVIRONMENTS:
            raise ValueError(
                f"Cannot remove built-in environment '{name}'. "
                "You can add a custom one instead."
            )
        del envs[name]
        if config.get("active_environment") == name:
            config["active_environment"] = DEFAULT_ACTIVE_ENVIRONMENT
        self._write_config(config)
        # Also remove credentials for this environment
        self._remove_credentials(name)

    def set_active_environment(self, name: str) -> Environment:
        config = self._read_config()
        envs = config.get("environments", {})
        if name not in envs:
            raise ValueError(
                f"Environment '{name}' not found. "
                "Run 'cc env list' to see available environments."
            )
        config["active_environment"] = name
        self._write_config(config)
        return self._env_from_config(name, config)

    # -- Credentials file operations --

    def _read_credentials(self) -> dict:
        if self.credentials_path.exists():
            return json.loads(self.credentials_path.read_text(encoding="utf-8"))
        return {}

    def _write_credentials(self, creds: dict) -> None:
        self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
        self.credentials_path.write_text(
            json.dumps(creds, indent=2) + "\n",
            encoding="utf-8",
        )
        # Restrict file permissions on Unix (owner read/write only)
        if os.name != "nt":
            self.credentials_path.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def get_credentials(self, env_name: str | None = None) -> Credentials:
        if env_name is None:
            env_name = self.get_active_environment_name()
        creds = self._read_credentials()
        if env_name in creds:
            return Credentials.from_dict(creds[env_name])
        return Credentials()

    def save_credentials(self, env_name: str, credentials: Credentials) -> None:
        creds = self._read_credentials()
        creds[env_name] = credentials.to_dict()
        self._write_credentials(creds)

    def _remove_credentials(self, env_name: str) -> None:
        creds = self._read_credentials()
        if env_name in creds:
            del creds[env_name]
            self._write_credentials(creds)

    def clear_credentials(self, env_name: str | None = None) -> None:
        """Clear credentials for an environment. If env_name is None, use active."""
        if env_name is None:
            env_name = self.get_active_environment_name()
        self._remove_credentials(env_name)

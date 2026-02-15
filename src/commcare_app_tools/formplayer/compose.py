"""Generate Docker Compose configuration for FormPlayer."""

from pathlib import Path
from typing import Optional

import yaml

from .settings import (
    COMPOSE_FILE,
    DEFAULT_AUTH_KEY,
    DEFAULT_EXTERNAL_REQUEST_MODE,
    DEFAULT_FORMPLAYER_DEBUG_PORT,
    DEFAULT_FORMPLAYER_PORT,
    DEFAULT_POSTGRES_PORT,
    DEFAULT_REDIS_PORT,
    FORMPLAYER_CONTAINER,
    FORMPLAYER_DATA_DIR,
    FORMPLAYER_IMAGE,
    NETWORK_NAME,
    POSTGRES_CONTAINER,
    POSTGRES_DATA_DIR,
    POSTGRES_IMAGE,
    REDIS_CONTAINER,
    REDIS_DATA_DIR,
    REDIS_IMAGE,
)


class FormPlayerComposeGenerator:
    """Generates Docker Compose configuration for local FormPlayer."""

    def __init__(
        self,
        commcare_host: str,
        formplayer_port: int = DEFAULT_FORMPLAYER_PORT,
        debug_port: int = DEFAULT_FORMPLAYER_DEBUG_PORT,
        postgres_port: int = DEFAULT_POSTGRES_PORT,
        redis_port: int = DEFAULT_REDIS_PORT,
        auth_key: str = DEFAULT_AUTH_KEY,
        alternate_origins: Optional[list[str]] = None,
    ):
        """
        Initialize compose generator.

        Args:
            commcare_host: The CommCare HQ URL to connect to (e.g., https://www.commcarehq.org)
            formplayer_port: Port to expose FormPlayer on
            debug_port: Port for FormPlayer debug/management endpoint
            postgres_port: Port to expose Postgres on
            redis_port: Port to expose Redis on
            auth_key: Authentication key for FormPlayer
            alternate_origins: Additional allowed CORS origins
        """
        self.commcare_host = commcare_host.rstrip("/")
        self.formplayer_port = formplayer_port
        self.debug_port = debug_port
        self.postgres_port = postgres_port
        self.redis_port = redis_port
        self.auth_key = auth_key
        self.alternate_origins = alternate_origins or [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]

    def generate_compose_dict(self) -> dict:
        """Generate the Docker Compose configuration as a dictionary."""
        return {
            "version": "3.8",
            "services": {
                "formplayer": {
                    "image": FORMPLAYER_IMAGE,
                    "container_name": FORMPLAYER_CONTAINER,
                    "environment": {
                        "COMMCARE_HOST": self.commcare_host,
                        "COMMCARE_ALTERNATE_ORIGINS": ",".join(self.alternate_origins),
                        "AUTH_KEY": self.auth_key,
                        "EXTERNAL_REQUEST_MODE": DEFAULT_EXTERNAL_REQUEST_MODE,
                        "POSTGRES_HOST": "postgres",
                        "POSTGRES_PORT": "5432",
                        "POSTGRES_USER": "formplayer",
                        "POSTGRES_PASSWORD": "formplayer",
                        "POSTGRES_DB": "formplayer",
                        "REDIS_HOST": "redis",
                        "REDIS_PORT": "6379",
                    },
                    "ports": [
                        f"{self.formplayer_port}:8080",
                        f"{self.debug_port}:8081",
                    ],
                    "depends_on": {
                        "postgres": {"condition": "service_healthy"},
                        "redis": {"condition": "service_healthy"},
                    },
                    "networks": [NETWORK_NAME],
                    "restart": "unless-stopped",
                },
                "postgres": {
                    "image": POSTGRES_IMAGE,
                    "container_name": POSTGRES_CONTAINER,
                    "environment": {
                        "POSTGRES_USER": "formplayer",
                        "POSTGRES_PASSWORD": "formplayer",
                        "POSTGRES_DB": "formplayer",
                    },
                    "ports": [f"{self.postgres_port}:5432"],
                    "volumes": [
                        f"{POSTGRES_DATA_DIR.as_posix()}:/var/lib/postgresql/data",
                    ],
                    "healthcheck": {
                        "test": ["CMD-SHELL", "pg_isready -U formplayer"],
                        "interval": "10s",
                        "timeout": "5s",
                        "retries": 5,
                    },
                    "networks": [NETWORK_NAME],
                    "restart": "unless-stopped",
                },
                "redis": {
                    "image": REDIS_IMAGE,
                    "container_name": REDIS_CONTAINER,
                    "ports": [f"{self.redis_port}:6379"],
                    "volumes": [
                        f"{REDIS_DATA_DIR.as_posix()}:/data",
                    ],
                    "healthcheck": {
                        "test": ["CMD", "redis-cli", "ping"],
                        "interval": "10s",
                        "timeout": "5s",
                        "retries": 5,
                    },
                    "networks": [NETWORK_NAME],
                    "restart": "unless-stopped",
                },
            },
            "networks": {
                NETWORK_NAME: {
                    "driver": "bridge",
                },
            },
        }

    def generate_compose_yaml(self) -> str:
        """Generate Docker Compose YAML string."""
        return yaml.dump(
            self.generate_compose_dict(),
            default_flow_style=False,
            sort_keys=False,
        )

    def write_compose_file(self, path: Optional[Path] = None) -> Path:
        """
        Write Docker Compose file to disk.

        Args:
            path: Optional path to write to. Defaults to COMPOSE_FILE.

        Returns:
            Path to the written file.
        """
        output_path = path or COMPOSE_FILE
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.generate_compose_yaml())
        return output_path

    @staticmethod
    def ensure_data_dirs():
        """Create data directories if they don't exist."""
        FORMPLAYER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        POSTGRES_DATA_DIR.mkdir(parents=True, exist_ok=True)
        REDIS_DATA_DIR.mkdir(parents=True, exist_ok=True)

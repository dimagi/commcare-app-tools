"""FormPlayer Docker configuration settings."""

import os
from pathlib import Path

from ..config.settings import DATA_DIR

# Docker image
FORMPLAYER_IMAGE = "docker.io/dimagi/formplayer"
POSTGRES_IMAGE = "docker.io/postgres:15"
REDIS_IMAGE = "docker.io/redis:7"

# Container names (prefixed for easy identification)
CONTAINER_PREFIX = "cc-formplayer"
FORMPLAYER_CONTAINER = f"{CONTAINER_PREFIX}-app"
POSTGRES_CONTAINER = f"{CONTAINER_PREFIX}-postgres"
REDIS_CONTAINER = f"{CONTAINER_PREFIX}-redis"

# Network name
NETWORK_NAME = f"{CONTAINER_PREFIX}-network"

# Default ports (can be overridden)
DEFAULT_FORMPLAYER_PORT = 8080
DEFAULT_FORMPLAYER_DEBUG_PORT = 8081
DEFAULT_POSTGRES_PORT = 5433  # Different from typical 5432 to avoid conflicts
DEFAULT_REDIS_PORT = 6380  # Different from typical 6379 to avoid conflicts

# FormPlayer environment variables
DEFAULT_AUTH_KEY = "localdevkey"
DEFAULT_EXTERNAL_REQUEST_MODE = "replace-host"

# Data directories for persistent volumes
FORMPLAYER_DATA_DIR = Path(os.environ.get(
    "CC_FORMPLAYER_DATA_DIR",
    DATA_DIR / "formplayer",
))
POSTGRES_DATA_DIR = FORMPLAYER_DATA_DIR / "postgres"
REDIS_DATA_DIR = FORMPLAYER_DATA_DIR / "redis"

# Docker compose file location
COMPOSE_FILE = FORMPLAYER_DATA_DIR / "docker-compose.yml"

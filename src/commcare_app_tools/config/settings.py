"""Default settings and configuration paths for commcare-app-tools."""

import os
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

APP_NAME = "commcare"
APP_AUTHOR = "dimagi"

# Configuration directories
CONFIG_DIR = Path(os.environ.get(
    "CC_CONFIG_DIR",
    user_config_dir(APP_NAME, APP_AUTHOR),
))
DATA_DIR = Path(os.environ.get(
    "CC_DATA_DIR",
    user_data_dir(APP_NAME, APP_AUTHOR),
))

# Config file paths
CONFIG_FILE = CONFIG_DIR / "config.json"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"

# Well-known environments with their default OAuth client IDs.
# Each CommCare HQ instance needs its own registered OAuth application.
# Client IDs are public values (not secrets) for the PKCE public client flow.
DEFAULT_ENVIRONMENTS = {
    "production": {
        "url": "https://www.commcarehq.org",
        "client_id": "A8fzmYyvXFjBlrOq6luNnqShA12l6KPpCeRqeuMV",
        "formplayer_url": None,
    },
    "india": {
        "url": "https://india.commcarehq.org",
        "client_id": "",
        "formplayer_url": None,
    },
    "staging": {
        "url": "https://staging.commcarehq.org",
        "client_id": "",
        "formplayer_url": None,
    },
}

DEFAULT_ACTIVE_ENVIRONMENT = "production"

# OAuth2 settings
OAUTH_SCOPES = "access_apis"
OAUTH_AUTHORIZE_PATH = "/oauth/authorize/"
OAUTH_TOKEN_PATH = "/oauth/token/"
OAUTH_REVOKE_PATH = "/oauth/revoke_token/"

# Localhost callback settings for OAuth flow
OAUTH_CALLBACK_HOST = "localhost"
OAUTH_CALLBACK_PORT_RANGE = (8400, 8500)  # Try ports in this range
OAUTH_CALLBACK_PATH = "/callback"

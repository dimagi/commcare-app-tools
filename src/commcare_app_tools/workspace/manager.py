"""Workspace manager for organizing downloaded CommCare artifacts.

Directory structure:
    .cc/
    ├── commcare-cli.jar
    └── workspaces/
        └── {domain}/
            └── {app_id}/
                ├── app.ccz
                ├── app-info.json
                └── users/
                    └── {user_id}/
                        ├── restore.xml
                        ├── user-info.json
                        └── sessions/
"""

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

def _get_cc_dir() -> Path:
    """Get the .cc directory path (calculated at runtime, not import time)."""
    return Path.cwd() / ".cc"


def _get_workspaces_dir() -> Path:
    """Get the workspaces directory path."""
    return _get_cc_dir() / "workspaces"


@dataclass
class AppInfo:
    """Metadata about a downloaded app."""

    app_id: str
    name: str
    version: Optional[int] = None
    downloaded_at: Optional[str] = None
    domain: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AppInfo":
        return cls(**data)


@dataclass
class UserInfo:
    """Metadata about a downloaded user restore."""

    user_id: str
    username: str
    downloaded_at: Optional[str] = None
    domain: Optional[str] = None
    app_id: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "UserInfo":
        return cls(**data)


class WorkspaceManager:
    """Manages local workspace directories for CommCare artifacts."""

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize workspace manager.

        Args:
            base_dir: Base directory for workspaces. Defaults to .cc/workspaces/
        """
        self.base_dir = base_dir or _get_workspaces_dir()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def create_minimal_restore(username: str) -> str:
        """Create a minimal restore XML that allows the CLI to run without cases.

        This generates a basic OpenRosa restore response with user registration
        but no case data. Useful for testing form logic without real user data.

        Note: The XML declaration is intentionally omitted because the CommCare
        XML parser (kxml2) doesn't handle it well.

        Args:
            username: Username to include in the restore

        Returns:
            XML string for the minimal restore
        """
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        return f"""<OpenRosaResponse xmlns="http://openrosa.org/http/response">
    <message nature="ota_restore_success">Successfully restored account {username}!</message>
    <Sync xmlns="http://commcarehq.org/sync">
        <restore_id>minimal-restore-{now}</restore_id>
    </Sync>
    <registration xmlns="http://openrosa.org/user/registration">
        <username>{username}</username>
        <password>not-used</password>
        <uuid>minimal-user-{username}</uuid>
        <date>{now}</date>
        <user_data>
            <data key="commcare_first_name">{username}</data>
            <data key="commcare_last_name">User</data>
        </user_data>
    </registration>
</OpenRosaResponse>"""

    # --- Path helpers ---

    def get_domain_path(self, domain: str) -> Path:
        """Get path to a domain's workspace directory."""
        return self.base_dir / domain

    def get_app_path(self, domain: str, app_id: str) -> Path:
        """Get path to an app's workspace directory."""
        return self.get_domain_path(domain) / app_id

    def get_app_ccz_path(self, domain: str, app_id: str) -> Path:
        """Get path to an app's CCZ file."""
        return self.get_app_path(domain, app_id) / "app.ccz"

    def get_app_info_path(self, domain: str, app_id: str) -> Path:
        """Get path to an app's info JSON file."""
        return self.get_app_path(domain, app_id) / "app-info.json"

    def get_user_path(self, domain: str, app_id: str, user_id: str) -> Path:
        """Get path to a user's workspace directory."""
        return self.get_app_path(domain, app_id) / "users" / user_id

    def get_restore_path(self, domain: str, app_id: str, user_id: str) -> Path:
        """Get path to a user's restore XML file."""
        return self.get_user_path(domain, app_id, user_id) / "restore.xml"

    def get_user_info_path(self, domain: str, app_id: str, user_id: str) -> Path:
        """Get path to a user's info JSON file."""
        return self.get_user_path(domain, app_id, user_id) / "user-info.json"

    def get_sessions_path(self, domain: str, app_id: str, user_id: str) -> Path:
        """Get path to a user's sessions directory."""
        return self.get_user_path(domain, app_id, user_id) / "sessions"

    # --- Directory management ---

    def ensure_app_dir(self, domain: str, app_id: str) -> Path:
        """Ensure app directory exists and return its path."""
        path = self.get_app_path(domain, app_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def ensure_user_dir(self, domain: str, app_id: str, user_id: str) -> Path:
        """Ensure user directory exists and return its path."""
        path = self.get_user_path(domain, app_id, user_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    # --- App operations ---

    def save_app_ccz(
        self,
        domain: str,
        app_id: str,
        ccz_content: bytes,
        app_name: str,
        version: Optional[int] = None,
    ) -> Path:
        """
        Save an app CCZ file to the workspace.

        Args:
            domain: Domain name
            app_id: Application ID
            ccz_content: Raw CCZ file content
            app_name: Human-readable app name
            version: App version number

        Returns:
            Path to the saved CCZ file
        """
        self.ensure_app_dir(domain, app_id)

        # Save CCZ
        ccz_path = self.get_app_ccz_path(domain, app_id)
        ccz_path.write_bytes(ccz_content)

        # Save metadata
        info = AppInfo(
            app_id=app_id,
            name=app_name,
            version=version,
            downloaded_at=datetime.utcnow().isoformat(),
            domain=domain,
        )
        self.save_app_info(domain, app_id, info)

        return ccz_path

    def save_app_info(self, domain: str, app_id: str, info: AppInfo) -> Path:
        """Save app metadata to JSON file."""
        path = self.get_app_info_path(domain, app_id)
        path.write_text(json.dumps(info.to_dict(), indent=2))
        return path

    def get_app_info(self, domain: str, app_id: str) -> Optional[AppInfo]:
        """Load app metadata from JSON file."""
        path = self.get_app_info_path(domain, app_id)
        if not path.exists():
            return None
        return AppInfo.from_dict(json.loads(path.read_text()))

    def has_app_ccz(self, domain: str, app_id: str) -> bool:
        """Check if app CCZ is already downloaded."""
        return self.get_app_ccz_path(domain, app_id).exists()

    # --- User/restore operations ---

    def save_restore(
        self,
        domain: str,
        app_id: str,
        user_id: str,
        restore_content: bytes | str,
        username: str,
    ) -> Path:
        """
        Save a user restore XML file to the workspace.

        Args:
            domain: Domain name
            app_id: Application ID
            user_id: User ID
            restore_content: Restore XML content (bytes or string)
            username: Human-readable username

        Returns:
            Path to the saved restore file
        """
        self.ensure_user_dir(domain, app_id, user_id)

        # Save restore XML
        restore_path = self.get_restore_path(domain, app_id, user_id)
        if isinstance(restore_content, bytes):
            restore_path.write_bytes(restore_content)
        else:
            restore_path.write_text(restore_content)

        # Save metadata
        info = UserInfo(
            user_id=user_id,
            username=username,
            downloaded_at=datetime.utcnow().isoformat(),
            domain=domain,
            app_id=app_id,
        )
        self.save_user_info(domain, app_id, user_id, info)

        return restore_path

    def save_user_info(
        self, domain: str, app_id: str, user_id: str, info: UserInfo
    ) -> Path:
        """Save user metadata to JSON file."""
        path = self.get_user_info_path(domain, app_id, user_id)
        path.write_text(json.dumps(info.to_dict(), indent=2))
        return path

    def get_user_info(
        self, domain: str, app_id: str, user_id: str
    ) -> Optional[UserInfo]:
        """Load user metadata from JSON file."""
        path = self.get_user_info_path(domain, app_id, user_id)
        if not path.exists():
            return None
        return UserInfo.from_dict(json.loads(path.read_text()))

    def has_restore(self, domain: str, app_id: str, user_id: str) -> bool:
        """Check if user restore is already downloaded."""
        return self.get_restore_path(domain, app_id, user_id).exists()

    # --- Listing operations ---

    def list_domains(self) -> list[str]:
        """List all domains with workspaces."""
        if not self.base_dir.exists():
            return []
        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]

    def list_apps(self, domain: str) -> list[AppInfo]:
        """List all apps in a domain's workspace."""
        domain_path = self.get_domain_path(domain)
        if not domain_path.exists():
            return []

        apps = []
        for app_dir in domain_path.iterdir():
            if app_dir.is_dir():
                info = self.get_app_info(domain, app_dir.name)
                if info:
                    apps.append(info)
                else:
                    # Directory exists but no info file - create minimal info
                    apps.append(AppInfo(app_id=app_dir.name, name=app_dir.name))
        return apps

    def list_users(self, domain: str, app_id: str) -> list[UserInfo]:
        """List all users in an app's workspace."""
        users_path = self.get_app_path(domain, app_id) / "users"
        if not users_path.exists():
            return []

        users = []
        for user_dir in users_path.iterdir():
            if user_dir.is_dir():
                info = self.get_user_info(domain, app_id, user_dir.name)
                if info:
                    users.append(info)
                else:
                    users.append(UserInfo(user_id=user_dir.name, username=user_dir.name))
        return users

    # --- Cleanup operations ---

    def clean_all(self) -> int:
        """
        Remove all workspaces.

        Returns:
            Number of domains removed
        """
        domains = self.list_domains()
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)
            self.base_dir.mkdir(parents=True, exist_ok=True)
        return len(domains)

    def clean_domain(self, domain: str) -> bool:
        """
        Remove a domain's workspace.

        Returns:
            True if domain was removed, False if it didn't exist
        """
        domain_path = self.get_domain_path(domain)
        if domain_path.exists():
            shutil.rmtree(domain_path)
            return True
        return False

    def clean_app(self, domain: str, app_id: str) -> bool:
        """
        Remove an app's workspace.

        Returns:
            True if app was removed, False if it didn't exist
        """
        app_path = self.get_app_path(domain, app_id)
        if app_path.exists():
            shutil.rmtree(app_path)
            return True
        return False

    def clean_user(self, domain: str, app_id: str, user_id: str) -> bool:
        """
        Remove a user's workspace.

        Returns:
            True if user was removed, False if it didn't exist
        """
        user_path = self.get_user_path(domain, app_id, user_id)
        if user_path.exists():
            shutil.rmtree(user_path)
            return True
        return False

    # --- Size/stats ---

    def get_workspace_size(self) -> int:
        """Get total size of all workspaces in bytes."""
        if not self.base_dir.exists():
            return 0
        total = 0
        for path in self.base_dir.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
        return total

    def get_workspace_stats(self) -> dict:
        """Get statistics about workspaces."""
        domains = self.list_domains()
        total_apps = 0
        total_users = 0

        for domain in domains:
            apps = self.list_apps(domain)
            total_apps += len(apps)
            for app in apps:
                total_users += len(self.list_users(domain, app.app_id))

        return {
            "domains": len(domains),
            "apps": total_apps,
            "users": total_users,
            "size_bytes": self.get_workspace_size(),
            "path": str(self.base_dir),
        }

"""REST API endpoints for test configuration and CommCare data."""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...api.client import CommCareAPI
from ...config.environments import ConfigManager
from ...config.settings import DATA_DIR
from ...workspace import WorkspaceManager

router = APIRouter(tags=["config"])

# Test configs storage
TEST_CONFIGS_FILE = DATA_DIR / "test-configs.json"


# --- Pydantic models ---


class TestConfig(BaseModel):
    """A saved test configuration."""

    id: str
    name: str
    domain: str
    app_id: str
    app_name: str
    user_id: str
    username: str
    case_type: Optional[str] = None
    case_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TestConfigCreate(BaseModel):
    """Request body for creating a test config."""

    name: str
    domain: str
    app_id: str
    app_name: str
    user_id: str
    username: str
    case_type: Optional[str] = None
    case_id: Optional[str] = None


class DomainInfo(BaseModel):
    """Domain information."""

    domain: str
    name: str


class AppInfo(BaseModel):
    """Application information."""

    id: str
    name: str
    version: Optional[int] = None


class UserInfo(BaseModel):
    """Mobile worker information."""

    id: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class CaseInfo(BaseModel):
    """Case information."""

    case_id: str
    case_type: str
    name: Optional[str] = None
    owner_id: Optional[str] = None


class WorkspaceStats(BaseModel):
    """Workspace statistics."""

    domains: int
    apps: int
    users: int
    size_bytes: int
    size_human: str
    path: str


# --- Helper functions ---


def _get_api_client(env_name: Optional[str] = None) -> CommCareAPI:
    """Get an authenticated API client."""
    config = ConfigManager()
    return CommCareAPI(config, env_name=env_name)


def _load_test_configs() -> dict[str, TestConfig]:
    """Load test configs from file."""
    if not TEST_CONFIGS_FILE.exists():
        return {}
    data = json.loads(TEST_CONFIGS_FILE.read_text())
    return {k: TestConfig(**v) for k, v in data.items()}


def _save_test_configs(configs: dict[str, TestConfig]) -> None:
    """Save test configs to file."""
    TEST_CONFIGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {k: v.model_dump() for k, v in configs.items()}
    TEST_CONFIGS_FILE.write_text(json.dumps(data, indent=2))


def _format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _flatten_pages(pages) -> list:
    """Flatten paginated results (list of lists) into a single list."""
    result = []
    for page in pages:
        result.extend(page)
    return result


# --- CommCare HQ data endpoints ---


@router.get("/domains", response_model=list[DomainInfo])
async def list_domains(env: Optional[str] = None):
    """List all domains the user has access to."""
    try:
        with _get_api_client(env) as client:
            domains = client.list_domains()
            return [
                DomainInfo(
                    domain=d.get("domain_name", d.get("domain", "")),
                    name=d.get("project_name", d.get("domain_name", d.get("domain", ""))),
                )
                for d in domains
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domains/{domain}/apps", response_model=list[AppInfo])
async def list_apps(domain: str, env: Optional[str] = None):
    """List all applications in a domain."""
    try:
        with _get_api_client(env) as client:
            pages = client.paginate(f"/a/{domain}/api/application/v1/", max_results=100)
            apps = _flatten_pages(pages)
            return [
                AppInfo(
                    id=app.get("id", ""),
                    name=app.get("name", "Unknown"),
                    version=app.get("version"),
                )
                for app in apps
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domains/{domain}/users", response_model=list[UserInfo])
async def list_users(domain: str, env: Optional[str] = None):
    """List all mobile workers in a domain."""
    try:
        with _get_api_client(env) as client:
            pages = client.paginate(f"/a/{domain}/api/user/v1/", max_results=100)
            users = _flatten_pages(pages)
            return [
                UserInfo(
                    id=user.get("id", ""),
                    username=user.get("username", ""),
                    first_name=user.get("first_name"),
                    last_name=user.get("last_name"),
                )
                for user in users
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domains/{domain}/cases", response_model=list[CaseInfo])
async def list_cases(
    domain: str,
    case_type: Optional[str] = Query(None, description="Filter by case type"),
    owner_id: Optional[str] = Query(None, description="Filter by owner ID"),
    limit: int = Query(50, le=100, description="Maximum number of cases to return"),
    env: Optional[str] = None,
):
    """List cases in a domain."""
    try:
        with _get_api_client(env) as client:
            params = {}
            if case_type:
                params["type"] = case_type
            if owner_id:
                params["owner_id"] = owner_id

            pages = client.paginate(
                f"/a/{domain}/api/case/v2/",
                params=params,
                max_results=limit,
            )
            cases = _flatten_pages(pages)
            return [
                CaseInfo(
                    case_id=case.get("case_id", ""),
                    case_type=case.get("properties", {}).get("case_type", ""),
                    name=case.get("properties", {}).get("case_name"),
                    owner_id=case.get("properties", {}).get("owner_id"),
                )
                for case in cases
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domains/{domain}/case-types", response_model=list[str])
async def list_case_types(domain: str, env: Optional[str] = None):
    """List unique case types in a domain (samples from recent cases)."""
    try:
        with _get_api_client(env) as client:
            # Get a sample of cases to find case types
            pages = client.paginate(
                f"/a/{domain}/api/case/v2/",
                max_results=200,
            )
            cases = _flatten_pages(pages)
            case_types = set()
            for case in cases:
                ct = case.get("properties", {}).get("case_type")
                if ct:
                    case_types.add(ct)
            return sorted(case_types)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Download endpoints ---


@router.post("/domains/{domain}/apps/{app_id}/download")
async def download_app(domain: str, app_id: str, env: Optional[str] = None):
    """
    Download an app's CCZ file to the local workspace.

    Returns info about the downloaded app.
    """
    try:
        with _get_api_client(env) as client:
            # Get app info first
            response = client.get(f"/a/{domain}/api/application/v1/{app_id}/")
            response.raise_for_status()
            app_data = response.json()
            app_name = app_data.get("name", "Unknown")
            app_version = app_data.get("version")

            # Download CCZ using the direct_ccz endpoint
            # latest options: 'release' (starred), 'build' (any build), 'save' (current)
            ccz_url = f"/a/{domain}/apps/api/download_ccz/"
            ccz_response = client.get(
                ccz_url,
                params={"app_id": app_id, "latest": "release"},
            )
            # If no released version, try latest build
            if ccz_response.status_code == 404:
                ccz_response = client.get(
                    ccz_url,
                    params={"app_id": app_id, "latest": "build"},
                )
            # If still no build, try current save
            if ccz_response.status_code == 404:
                ccz_response = client.get(
                    ccz_url,
                    params={"app_id": app_id, "latest": "save"},
                )
            ccz_response.raise_for_status()
            ccz_content = ccz_response.content

            # Save to workspace
            workspace = WorkspaceManager()
            ccz_path = workspace.save_app_ccz(
                domain=domain,
                app_id=app_id,
                ccz_content=ccz_content,
                app_name=app_name,
                version=app_version,
            )

            return {
                "success": True,
                "app_id": app_id,
                "app_name": app_name,
                "version": app_version,
                "path": str(ccz_path),
                "size_bytes": len(ccz_content),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/domains/{domain}/apps/{app_id}/users/{user_id}/download-restore")
async def download_restore(
    domain: str, app_id: str, user_id: str, env: Optional[str] = None
):
    """
    Download a user's restore XML to the local workspace.

    Returns info about the downloaded restore.
    """
    try:
        with _get_api_client(env) as client:
            # Get user info first
            response = client.get(f"/a/{domain}/api/user/v1/{user_id}/")
            response.raise_for_status()
            user_data = response.json()
            username = user_data.get("username", "unknown")

            # Download restore XML
            # The restore endpoint varies - try the OTA restore endpoint
            restore_url = f"/a/{domain}/phone/restore/{user_id}/"
            restore_response = client.get(
                restore_url,
                params={"version": "2.0", "as": user_id},
            )
            restore_response.raise_for_status()
            restore_content = restore_response.content

            # Save to workspace
            workspace = WorkspaceManager()
            restore_path = workspace.save_restore(
                domain=domain,
                app_id=app_id,
                user_id=user_id,
                restore_content=restore_content,
                username=username,
            )

            return {
                "success": True,
                "user_id": user_id,
                "username": username,
                "path": str(restore_path),
                "size_bytes": len(restore_content),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domains/{domain}/apps/{app_id}/status")
async def get_app_download_status(domain: str, app_id: str):
    """Check if app CCZ is downloaded and get its info."""
    workspace = WorkspaceManager()
    has_ccz = workspace.has_app_ccz(domain, app_id)
    app_info = workspace.get_app_info(domain, app_id)

    return {
        "downloaded": has_ccz,
        "app_info": app_info.to_dict() if app_info else None,
        "ccz_path": str(workspace.get_app_ccz_path(domain, app_id)) if has_ccz else None,
    }


@router.get("/domains/{domain}/apps/{app_id}/users/{user_id}/status")
async def get_restore_status(domain: str, app_id: str, user_id: str):
    """Check if user restore is downloaded and get its info."""
    workspace = WorkspaceManager()
    has_restore = workspace.has_restore(domain, app_id, user_id)
    user_info = workspace.get_user_info(domain, app_id, user_id)

    return {
        "downloaded": has_restore,
        "user_info": user_info.to_dict() if user_info else None,
        "restore_path": (
            str(workspace.get_restore_path(domain, app_id, user_id))
            if has_restore
            else None
        ),
    }


# --- Test config CRUD endpoints ---


@router.get("/test-configs", response_model=list[TestConfig])
async def list_test_configs():
    """List all saved test configurations."""
    configs = _load_test_configs()
    return list(configs.values())


@router.get("/test-configs/{config_id}", response_model=TestConfig)
async def get_test_config(config_id: str):
    """Get a specific test configuration."""
    configs = _load_test_configs()
    if config_id not in configs:
        raise HTTPException(status_code=404, detail="Test config not found")
    return configs[config_id]


@router.post("/test-configs", response_model=TestConfig)
async def create_test_config(config: TestConfigCreate):
    """Create a new test configuration."""
    configs = _load_test_configs()

    # Generate ID from name
    config_id = config.name.lower().replace(" ", "-")
    base_id = config_id
    counter = 1
    while config_id in configs:
        config_id = f"{base_id}-{counter}"
        counter += 1

    now = datetime.utcnow().isoformat()
    new_config = TestConfig(
        id=config_id,
        created_at=now,
        updated_at=now,
        **config.model_dump(),
    )

    configs[config_id] = new_config
    _save_test_configs(configs)

    return new_config


@router.put("/test-configs/{config_id}", response_model=TestConfig)
async def update_test_config(config_id: str, config: TestConfigCreate):
    """Update an existing test configuration."""
    configs = _load_test_configs()
    if config_id not in configs:
        raise HTTPException(status_code=404, detail="Test config not found")

    existing = configs[config_id]
    updated = TestConfig(
        id=config_id,
        created_at=existing.created_at,
        updated_at=datetime.utcnow().isoformat(),
        **config.model_dump(),
    )

    configs[config_id] = updated
    _save_test_configs(configs)

    return updated


@router.delete("/test-configs/{config_id}")
async def delete_test_config(config_id: str):
    """Delete a test configuration."""
    configs = _load_test_configs()
    if config_id not in configs:
        raise HTTPException(status_code=404, detail="Test config not found")

    del configs[config_id]
    _save_test_configs(configs)

    return {"status": "deleted", "id": config_id}


# --- Workspace endpoints ---


@router.get("/workspace/stats", response_model=WorkspaceStats)
async def get_workspace_stats():
    """Get workspace statistics."""
    manager = WorkspaceManager()
    stats = manager.get_workspace_stats()
    return WorkspaceStats(
        domains=stats["domains"],
        apps=stats["apps"],
        users=stats["users"],
        size_bytes=stats["size_bytes"],
        size_human=_format_size(stats["size_bytes"]),
        path=stats["path"],
    )


@router.delete("/workspace")
async def clean_workspace():
    """Clean all workspace data."""
    manager = WorkspaceManager()
    count = manager.clean_all()
    return {"status": "cleaned", "domains_removed": count}


@router.delete("/workspace/{domain}")
async def clean_domain_workspace(domain: str):
    """Clean a domain's workspace data."""
    manager = WorkspaceManager()
    if manager.clean_domain(domain):
        return {"status": "cleaned", "domain": domain}
    raise HTTPException(status_code=404, detail="Domain workspace not found")

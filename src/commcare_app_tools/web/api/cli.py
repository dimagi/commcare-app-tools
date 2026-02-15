"""CLI-related API endpoints for the web UI."""

from typing import Optional

from fastapi import APIRouter

from ...commcare_cli.builder import CommCareCLIBuilder
from ...workspace import WorkspaceManager

router = APIRouter(tags=["cli"])


@router.get("/terminal/status")
async def terminal_status():
    """Check if the CLI backend is ready (Java + JAR available)."""
    builder = CommCareCLIBuilder()

    try:
        java_path = builder.find_java()
        java_ok = True
        java_error = None
    except Exception as e:
        java_path = None
        java_ok = False
        java_error = str(e)

    jar_built = builder.is_built()

    return {
        "ready": java_ok and jar_built,
        "java": {
            "found": java_ok,
            "path": java_path,
            "error": java_error,
        },
        "cli_jar": {
            "built": jar_built,
            "path": str(builder.jar_path) if jar_built else None,
        },
    }


@router.get("/run-command")
async def get_run_command(
    domain: str,
    app_id: str,
    user_id: Optional[str] = None,
):
    """
    Generate the command to run the CommCare CLI for a given config.

    Returns the full command string that can be copied to a terminal.
    """
    builder = CommCareCLIBuilder()
    workspace = WorkspaceManager()

    # Check Java
    try:
        java_path = builder.find_java()
    except Exception as e:
        return {"error": f"Java not found: {e}"}

    # Check JAR
    if not builder.is_built():
        return {"error": "CLI JAR not built. Run 'cc cli build' first."}

    jar_path = builder.jar_path

    # Check CCZ
    ccz_path = workspace.get_app_ccz_path(domain, app_id)
    if not ccz_path.exists():
        return {"error": f"App CCZ not found at {ccz_path}"}

    # Check/create restore
    restore_path = None
    if user_id:
        restore_path = workspace.get_restore_path(domain, app_id, user_id)
        if not restore_path.exists():
            # Create minimal restore
            minimal_restore = workspace.create_minimal_restore(user_id)
            restore_path.parent.mkdir(parents=True, exist_ok=True)
            restore_path.write_text(minimal_restore)
    else:
        # Create minimal restore for anonymous user
        restore_path = workspace.get_restore_path(domain, app_id, "minimal")
        if not restore_path.exists():
            minimal_restore = workspace.create_minimal_restore("test-user")
            restore_path.parent.mkdir(parents=True, exist_ok=True)
            restore_path.write_text(minimal_restore)

    # Build command - quote paths that might have spaces
    def quote(path: str) -> str:
        if " " in path:
            return f'"{path}"'
        return path

    cmd_parts = [
        "&",  # PowerShell call operator (needed when exe path is quoted)
        quote(java_path),
        "-jar",
        quote(str(jar_path)),
        "play",
        quote(str(ccz_path)),
        "-r",
        quote(str(restore_path)),
    ]

    return {
        "command": " ".join(cmd_parts),
        "java_path": java_path,
        "jar_path": str(jar_path),
        "ccz_path": str(ccz_path),
        "restore_path": str(restore_path),
    }

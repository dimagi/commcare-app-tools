"""Workspace management commands."""

import click

from ..utils.output import format_output, print_error, print_info, print_success
from ..workspace import WorkspaceManager


@click.group()
def workspace():
    """Manage local workspace data (downloaded apps, restores, etc.)."""
    pass


@workspace.command("list")
@click.option(
    "--domain", "-d",
    help="List apps/users for a specific domain",
)
@click.pass_context
def list_workspace(ctx, domain: str):
    """List workspace contents.

    Shows downloaded domains, apps, and user restores.

    Example:
        cc workspace list
        cc workspace list --domain my-domain
    """
    output_format = ctx.obj.get("output_format", "table") if ctx.obj else "table"
    manager = WorkspaceManager()

    if domain:
        # List apps and users for a specific domain
        apps = manager.list_apps(domain)
        if not apps:
            print_info(f"No apps downloaded for domain '{domain}'")
            return

        rows = []
        for app in apps:
            users = manager.list_users(domain, app.app_id)
            rows.append({
                "app_id": app.app_id,
                "app_name": app.name,
                "version": app.version or "-",
                "users": len(users),
                "downloaded": app.downloaded_at or "-",
            })

        format_output(
            rows,
            fmt=output_format,
            columns=["app_id", "app_name", "version", "users", "downloaded"],
            title=f"Apps in {domain}",
        )
    else:
        # List all domains
        domains = manager.list_domains()
        if not domains:
            print_info("No workspaces found. Download an app to create one.")
            return

        rows = []
        for d in domains:
            apps = manager.list_apps(d)
            total_users = sum(len(manager.list_users(d, a.app_id)) for a in apps)
            rows.append({
                "domain": d,
                "apps": len(apps),
                "users": total_users,
            })

        format_output(
            rows,
            fmt=output_format,
            columns=["domain", "apps", "users"],
            title="Workspaces",
        )


@workspace.command()
def stats():
    """Show workspace statistics.

    Displays total size, number of domains, apps, and users.

    Example:
        cc workspace stats
    """
    manager = WorkspaceManager()
    stats = manager.get_workspace_stats()

    # Format size
    size_bytes = stats["size_bytes"]
    if size_bytes < 1024:
        size_str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        size_str = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    print_info(f"Workspace path: {stats['path']}")
    print_info(f"Total size: {size_str}")
    print_info(f"Domains: {stats['domains']}")
    print_info(f"Apps: {stats['apps']}")
    print_info(f"Users: {stats['users']}")


@workspace.command()
@click.option(
    "--domain", "-d",
    help="Clean only a specific domain",
)
@click.option(
    "--app", "-a",
    help="Clean only a specific app (requires --domain)",
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Skip confirmation prompt",
)
def clean(domain: str, app: str, force: bool):
    """Clean workspace data.

    Removes downloaded apps, restores, and other cached data.

    Example:
        cc workspace clean              # Clean all
        cc workspace clean -d my-domain # Clean one domain
        cc workspace clean -d my-domain -a app123  # Clean one app
    """
    manager = WorkspaceManager()

    if app and not domain:
        print_error("--app requires --domain")
        raise SystemExit(1)

    if app:
        # Clean specific app
        target = f"app '{app}' in domain '{domain}'"
        if not force:
            click.confirm(f"Delete {target}?", abort=True)

        if manager.clean_app(domain, app):
            print_success(f"Cleaned {target}")
        else:
            print_error(f"App not found: {app}")

    elif domain:
        # Clean specific domain
        target = f"domain '{domain}'"
        if not force:
            click.confirm(f"Delete all data for {target}?", abort=True)

        if manager.clean_domain(domain):
            print_success(f"Cleaned {target}")
        else:
            print_error(f"Domain not found: {domain}")

    else:
        # Clean all
        stats = manager.get_workspace_stats()
        if stats["domains"] == 0:
            print_info("No workspaces to clean")
            return

        if not force:
            click.confirm(
                f"Delete ALL workspace data ({stats['domains']} domains, "
                f"{stats['apps']} apps, {stats['users']} users)?",
                abort=True,
            )

        count = manager.clean_all()
        print_success(f"Cleaned {count} domain(s)")


@workspace.command()
@click.argument("domain")
@click.argument("app_id")
def path(domain: str, app_id: str):
    """Show the path to a workspace directory.

    Useful for terminal debugging - copy the path to navigate there.

    Example:
        cc workspace path my-domain abc123
    """
    manager = WorkspaceManager()
    app_path = manager.get_app_path(domain, app_id)

    if app_path.exists():
        print_success(f"Path: {app_path}")
        print_info("Contents:")
        for item in app_path.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(app_path)
                size = item.stat().st_size
                print_info(f"  {rel_path} ({size} bytes)")
    else:
        print_info(f"Path (not yet created): {app_path}")

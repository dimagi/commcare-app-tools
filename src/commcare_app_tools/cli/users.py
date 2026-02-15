"""cc user -- user management commands."""

import click

from ..api.client import CommCareAPI
from ..api.endpoints import USER_LIST
from ..config.environments import ConfigManager
from ..utils.output import format_output, print_error
from ..workspace.manager import WorkspaceManager


@click.group()
def user():
    """Manage CommCare mobile workers and web users."""


@user.command("list")
@click.option("--limit", default=20, type=int, help="Number of results to return.")
@click.option("--offset", default=0, type=int, help="Pagination offset.")
@click.pass_context
def list_users(ctx, limit, offset):
    """List mobile workers in a domain.

    Requires --domain to be set.
    """
    config = ConfigManager()
    domain = ctx.obj.get("domain")
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    if not domain:
        print_error("--domain is required. Example: cc --domain my-project user list")
        raise SystemExit(1)

    try:
        with CommCareAPI(config, domain=domain, env_name=env_name) as api_client:
            data = api_client.list(USER_LIST, limit=limit, offset=offset)
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(data, fmt=output_format, output_file=output_file)


@user.command("get")
@click.argument("user_id")
@click.pass_context
def get_user(ctx, user_id):
    """Get details for a specific mobile worker."""
    config = ConfigManager()
    domain = ctx.obj.get("domain")
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    if not domain:
        print_error("--domain is required. Example: cc --domain my-project user get USER_ID")
        raise SystemExit(1)

    try:
        with CommCareAPI(config, domain=domain, env_name=env_name) as api_client:
            response = api_client.get(f"api/user/v1/{user_id}/")
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(data, fmt=output_format, output_file=output_file)


@user.command("restore")
@click.argument("username")
@click.option("--app-id", help="App ID (required for workspace storage).")
@click.option(
    "--save/--no-save",
    default=False,
    help="Save restore to workspace (requires --app-id).",
)
@click.option(
    "--output-xml",
    type=click.Path(),
    help="Write restore XML directly to this file path.",
)
@click.pass_context
def restore_user(ctx, username, app_id, save, output_xml):
    """Download a user's restore XML using the 'login as' mechanism.

    This uses the ?as= parameter to get the restore for a specific mobile
    worker. Your authenticated user must have 'login_as_all_users' or
    'limited_login_as' permission on the domain.

    USERNAME should be the mobile worker's username (without @domain).

    Examples:

        cc --domain my-project user restore worker1

        cc --domain my-project user restore worker1 --output-xml restore.xml

        cc --domain my-project user restore worker1 --app-id abc123 --save
    """
    config = ConfigManager()
    domain = ctx.obj.get("domain")
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    if not domain:
        print_error(
            "--domain is required. Example: cc --domain my-project user restore worker1"
        )
        raise SystemExit(1)

    if save and not app_id:
        print_error("--app-id is required when using --save")
        raise SystemExit(1)

    try:
        with CommCareAPI(config, domain=domain, env_name=env_name) as api_client:
            # First, look up the user to get their user_id
            click.echo(f"Looking up user '{username}'...", err=True)
            user_response = api_client.list(
                USER_LIST, params={"username": username}, limit=1
            )

            users = user_response.get("objects", [])
            if not users:
                print_error(f"User '{username}' not found in domain '{domain}'")
                raise SystemExit(1)

            user_data = users[0]
            user_id = user_data.get("id")
            full_username = user_data.get("username", username)

            # Download restore using ?as= parameter
            click.echo(f"Downloading restore for user '{full_username}'...", err=True)
            restore_response = api_client.get(
                "phone/restore/",
                params={"version": "2.0", "as": full_username},
            )
            restore_response.raise_for_status()
            restore_content = restore_response.content

            # Handle output
            if output_xml:
                # Write directly to specified file
                with open(output_xml, "wb") as f:
                    f.write(restore_content)
                result = {
                    "success": True,
                    "user_id": user_id,
                    "username": full_username,
                    "path": output_xml,
                    "size_bytes": len(restore_content),
                }
            elif save:
                # Save to workspace
                workspace = WorkspaceManager()
                restore_path = workspace.save_restore(
                    domain=domain,
                    app_id=app_id,
                    user_id=user_id,
                    restore_content=restore_content,
                    username=full_username,
                )
                result = {
                    "success": True,
                    "user_id": user_id,
                    "username": full_username,
                    "path": str(restore_path),
                    "size_bytes": len(restore_content),
                }
            else:
                # Output restore info (not the XML itself, that would be huge)
                result = {
                    "success": True,
                    "user_id": user_id,
                    "username": full_username,
                    "size_bytes": len(restore_content),
                    "hint": "Use --output-xml <file> to save the XML, or --save --app-id <id> to save to workspace",
                }

    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(result, fmt=output_format, output_file=output_file)

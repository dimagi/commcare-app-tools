"""cc user -- user management commands."""

import click

from ..api.client import CommCareAPI
from ..api.endpoints import USER_LIST
from ..config.environments import ConfigManager
from ..utils.output import format_output, print_error


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

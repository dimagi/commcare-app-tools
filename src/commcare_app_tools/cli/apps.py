"""cc app -- application management commands."""

import click

from ..api.client import CommCareAPI
from ..api.endpoints import APP_LIST
from ..config.environments import ConfigManager
from ..utils.output import format_output, print_error


@click.group()
def app():
    """Manage CommCare applications."""


@app.command("list")
@click.option("--limit", default=None, type=int, help="Maximum number of results (default: all).")
@click.option("--offset", default=0, type=int, help="Pagination offset.")
@click.pass_context
def list_apps(ctx, limit, offset):
    """List applications in a domain.

    Requires --domain to be set.
    """
    config = ConfigManager()
    domain = ctx.obj.get("domain")
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    if not domain:
        print_error("--domain is required. Example: cc --domain my-project app list")
        raise SystemExit(1)

    try:
        with CommCareAPI(config, domain=domain, env_name=env_name) as api_client:
            data = api_client.list(APP_LIST, limit=limit, offset=offset)
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(data, fmt=output_format, output_file=output_file)


@app.command("get")
@click.argument("app_id")
@click.pass_context
def get_app(ctx, app_id):
    """Get details for a specific application."""
    config = ConfigManager()
    domain = ctx.obj.get("domain")
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    if not domain:
        print_error("--domain is required. Example: cc --domain my-project app get APP_ID")
        raise SystemExit(1)

    try:
        with CommCareAPI(config, domain=domain, env_name=env_name) as api_client:
            response = api_client.get(f"api/application/v1/{app_id}/")
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(data, fmt=output_format, output_file=output_file)

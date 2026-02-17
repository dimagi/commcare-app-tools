"""cc lookup-table -- lookup table management commands."""

import click

from ..api.client import CommCareAPI
from ..config.environments import ConfigManager
from ..utils.output import format_output, print_error


@click.group("lookup-table")
def lookup_table():
    """Manage CommCare lookup tables (fixtures)."""


@lookup_table.command("list")
@click.option("--limit", default=None, type=int, help="Maximum number of results (default: all).")
@click.option("--offset", default=0, type=int, help="Pagination offset.")
@click.pass_context
def list_tables(ctx, limit, offset):
    """List lookup tables in a domain.

    Requires --domain to be set.
    """
    config = ConfigManager()
    domain = ctx.obj.get("domain")
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    if not domain:
        print_error(
            "--domain is required. Example: cc --domain my-project lookup-table list"
        )
        raise SystemExit(1)

    try:
        with CommCareAPI(config, domain=domain, env_name=env_name) as api_client:
            data = api_client.list(
                "api/lookup_table/v1/", limit=limit, offset=offset
            )
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(data, fmt=output_format, output_file=output_file)


@lookup_table.command("get")
@click.argument("table_id")
@click.pass_context
def get_table(ctx, table_id):
    """Get details for a specific lookup table."""
    config = ConfigManager()
    domain = ctx.obj.get("domain")
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    if not domain:
        print_error(
            "--domain is required. "
            "Example: cc --domain my-project lookup-table get TABLE_ID"
        )
        raise SystemExit(1)

    try:
        with CommCareAPI(config, domain=domain, env_name=env_name) as api_client:
            response = api_client.get(f"api/lookup_table/v1/{table_id}/")
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(data, fmt=output_format, output_file=output_file)


@lookup_table.command("items")
@click.argument("table_id")
@click.option("--limit", default=None, type=int, help="Maximum number of results (default: all).")
@click.option("--offset", default=0, type=int, help="Pagination offset.")
@click.pass_context
def list_items(ctx, table_id, limit, offset):
    """List items in a lookup table."""
    config = ConfigManager()
    domain = ctx.obj.get("domain")
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    if not domain:
        print_error(
            "--domain is required. "
            "Example: cc --domain my-project lookup-table items TABLE_ID"
        )
        raise SystemExit(1)

    try:
        with CommCareAPI(config, domain=domain, env_name=env_name) as api_client:
            data = api_client.list(
                "api/lookup_table_item/v2/",
                params={"data_type_id": table_id},
                limit=limit,
                offset=offset,
            )
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(data, fmt=output_format, output_file=output_file)

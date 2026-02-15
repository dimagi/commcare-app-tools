"""cc case -- case management commands."""

import click

from ..api.client import CommCareAPI
from ..api.endpoints import CASE_LIST_V2
from ..config.environments import ConfigManager
from ..utils.output import format_output, print_error


@click.group()
def case():
    """Manage CommCare cases."""


@case.command("list")
@click.option("--case-type", default=None, help="Filter by case type.")
@click.option("--owner-id", default=None, help="Filter by owner ID.")
@click.option("--closed", default=None, type=bool, help="Filter by closed status.")
@click.option("--limit", default=20, type=int, help="Number of results to return.")
@click.option("--offset", default=0, type=int, help="Pagination offset.")
@click.pass_context
def list_cases(ctx, case_type, owner_id, closed, limit, offset):
    """List cases in a domain.

    Requires --domain to be set.
    """
    config = ConfigManager()
    domain = ctx.obj.get("domain")
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    if not domain:
        print_error("--domain is required. Example: cc --domain my-project case list")
        raise SystemExit(1)

    params = {}
    if case_type:
        params["case_type"] = case_type
    if owner_id:
        params["owner_id"] = owner_id
    if closed is not None:
        params["closed"] = str(closed).lower()

    try:
        with CommCareAPI(config, domain=domain, env_name=env_name) as api_client:
            data = api_client.list(CASE_LIST_V2, params=params, limit=limit, offset=offset)
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(data, fmt=output_format, output_file=output_file)


@case.command("get")
@click.argument("case_id")
@click.pass_context
def get_case(ctx, case_id):
    """Get details for a specific case."""
    config = ConfigManager()
    domain = ctx.obj.get("domain")
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    if not domain:
        print_error("--domain is required. Example: cc --domain my-project case get CASE_ID")
        raise SystemExit(1)

    try:
        with CommCareAPI(config, domain=domain, env_name=env_name) as api_client:
            response = api_client.get(f"api/case/v2/{case_id}/")
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(data, fmt=output_format, output_file=output_file)

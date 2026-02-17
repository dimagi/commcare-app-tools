"""cc form -- form submission commands."""

import click

from ..api.client import CommCareAPI
from ..api.endpoints import FORM_LIST
from ..config.environments import ConfigManager
from ..utils.output import format_output, print_error


@click.group()
def form():
    """Manage CommCare form submissions."""


@form.command("list")
@click.option("--xmlns", default=None, help="Filter by form XMLNS.")
@click.option("--limit", default=None, type=int, help="Maximum number of results (default: all).")
@click.option("--offset", default=0, type=int, help="Pagination offset.")
@click.pass_context
def list_forms(ctx, xmlns, limit, offset):
    """List form submissions in a domain.

    Requires --domain to be set.
    """
    config = ConfigManager()
    domain = ctx.obj.get("domain")
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    if not domain:
        print_error("--domain is required. Example: cc --domain my-project form list")
        raise SystemExit(1)

    params = {}
    if xmlns:
        params["xmlns"] = xmlns

    try:
        with CommCareAPI(config, domain=domain, env_name=env_name) as api_client:
            data = api_client.list(FORM_LIST, params=params, limit=limit, offset=offset)
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(data, fmt=output_format, output_file=output_file)


@form.command("get")
@click.argument("form_id")
@click.pass_context
def get_form(ctx, form_id):
    """Get details for a specific form submission."""
    config = ConfigManager()
    domain = ctx.obj.get("domain")
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    if not domain:
        print_error("--domain is required. Example: cc --domain my-project form get FORM_ID")
        raise SystemExit(1)

    try:
        with CommCareAPI(config, domain=domain, env_name=env_name) as api_client:
            response = api_client.get(f"api/form/v1/{form_id}/")
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(data, fmt=output_format, output_file=output_file)

"""cc report -- report commands."""

import click

from ..api.client import CommCareAPI
from ..config.environments import ConfigManager
from ..utils.output import format_output, print_error


@click.group()
def report():
    """Manage CommCare reports and data sources."""


@report.command("list")
@click.option("--limit", default=20, type=int, help="Number of results to return.")
@click.option("--offset", default=0, type=int, help="Pagination offset.")
@click.pass_context
def list_reports(ctx, limit, offset):
    """List report configurations in a domain.

    Requires --domain to be set.
    """
    config = ConfigManager()
    domain = ctx.obj.get("domain")
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    if not domain:
        print_error(
            "--domain is required. Example: cc --domain my-project report list"
        )
        raise SystemExit(1)

    try:
        with CommCareAPI(config, domain=domain, env_name=env_name) as api_client:
            data = api_client.list(
                "api/simple_report_configuration/v1/",
                limit=limit,
                offset=offset,
            )
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(data, fmt=output_format, output_file=output_file)


@report.command("data")
@click.argument("report_id")
@click.option("--limit", default=20, type=int, help="Number of results to return.")
@click.option("--offset", default=0, type=int, help="Pagination offset.")
@click.option(
    "--filters", default=None,
    help="Report filters as JSON string (e.g. '{\"state\": \"active\"}').",
)
@click.pass_context
def report_data(ctx, report_id, limit, offset, filters):
    """Fetch data from a configurable report.

    REPORT_ID is the UUID of the report configuration.
    """
    import json

    config = ConfigManager()
    domain = ctx.obj.get("domain")
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    if not domain:
        print_error(
            "--domain is required. "
            "Example: cc --domain my-project report data REPORT_ID"
        )
        raise SystemExit(1)

    params = {}
    if filters:
        try:
            params.update(json.loads(filters))
        except json.JSONDecodeError as e:
            print_error(f"Invalid JSON for --filters: {e}")
            raise SystemExit(1)

    try:
        with CommCareAPI(config, domain=domain, env_name=env_name) as api_client:
            data = api_client.list(
                f"api/configurable_report_data/v1/{report_id}/",
                params=params,
                limit=limit,
                offset=offset,
            )
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(data, fmt=output_format, output_file=output_file)

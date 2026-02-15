"""cc domain -- domain listing commands."""

import click

from ..api.client import CommCareAPI
from ..config.environments import ConfigManager
from ..utils.output import format_output, print_error


@click.group("domain")
def domains():
    """Manage CommCare domains (project spaces)."""


@domains.command("list")
@click.pass_context
def list_domains(ctx):
    """List all domains you have access to.

    Shows all CommCare project spaces that your account can access
    on the current environment.
    """
    config = ConfigManager()
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    try:
        with CommCareAPI(config, env_name=env_name) as api_client:
            domain_list = api_client.list_domains()
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(domain_list, fmt=output_format, output_file=output_file)

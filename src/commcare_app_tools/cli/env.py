"""cc env -- environment management commands."""

import click

from ..config.environments import ConfigManager
from ..utils.output import format_output, print_error, print_success


@click.group()
def env():
    """Manage CommCare HQ environments."""


@env.command("list")
@click.pass_context
def list_envs(ctx):
    """List all configured environments."""
    config = ConfigManager()
    active = config.get_active_environment_name()
    environments = config.list_environments()
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    if output_format == "json":
        data = [
            {
                "name": e.name,
                "url": e.url,
                "active": e.name == active,
                "client_id_set": bool(e.client_id),
                "formplayer_url": e.formplayer_url,
            }
            for e in environments
        ]
        format_output(data, fmt="json", output_file=output_file)
    elif output_format == "table":
        data = [
            {
                "": "*" if e.name == active else "",
                "Name": e.name,
                "URL": e.url,
                "OAuth": "configured" if e.client_id else "not set",
                "FormPlayer": e.formplayer_url or "-",
            }
            for e in environments
        ]
        format_output(data, fmt="table", title="Environments", output_file=output_file)
    else:
        data = [
            {
                "name": e.name,
                "url": e.url,
                "active": e.name == active,
                "client_id_set": bool(e.client_id),
                "formplayer_url": e.formplayer_url or "",
            }
            for e in environments
        ]
        format_output(data, fmt="csv", output_file=output_file)


@env.command("add")
@click.argument("name")
@click.argument("url")
@click.option("--client-id", default="", help="OAuth2 client ID for this environment.")
@click.option("--formplayer-url", default=None, help="FormPlayer URL for this environment.")
def add_env(name, url, client_id, formplayer_url):
    """Add a new environment.

    NAME is a short identifier (e.g. 'local', 'staging').
    URL is the CommCare HQ base URL (e.g. 'http://localhost:8000').
    """
    config = ConfigManager()
    try:
        env = config.add_environment(name, url, client_id, formplayer_url)
        print_success(f"Added environment '{name}' -> {env.url}")
        if not client_id:
            click.echo(
                f"  Note: No client_id set. Register an OAuth app on {env.url} "
                f"and update with:\n"
                f"    cc env add {name} {url} --client-id YOUR_CLIENT_ID"
            )
    except ValueError as e:
        print_error(str(e))
        raise SystemExit(1)


@env.command("use")
@click.argument("name")
def use_env(name):
    """Switch the active environment.

    NAME is the environment to activate (e.g. 'production', 'india', 'local').
    """
    config = ConfigManager()
    try:
        env = config.set_active_environment(name)
        print_success(f"Active environment: {name} ({env.url})")
    except ValueError as e:
        print_error(str(e))
        raise SystemExit(1)


@env.command("remove")
@click.argument("name")
@click.confirmation_option(prompt="Are you sure you want to remove this environment?")
def remove_env(name):
    """Remove a custom environment and its stored credentials."""
    config = ConfigManager()
    try:
        config.remove_environment(name)
        print_success(f"Removed environment '{name}'")
    except ValueError as e:
        print_error(str(e))
        raise SystemExit(1)

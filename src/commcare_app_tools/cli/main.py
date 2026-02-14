"""Root CLI group for the cc command."""

import click

from .. import __version__
from ..config.environments import ConfigManager


@click.group()
@click.version_option(version=__version__, prog_name="cc")
@click.option(
    "--env", "env_name",
    default=None,
    envvar="CC_ENV",
    help="Environment to use (overrides active environment).",
)
@click.option(
    "--domain",
    default=None,
    envvar="CC_DOMAIN",
    help="CommCare domain (project space) to operate on.",
)
@click.option(
    "--format", "output_format",
    type=click.Choice(["json", "table", "csv"]),
    default="json",
    envvar="CC_FORMAT",
    help="Output format.",
)
@click.option(
    "--output", "output_file",
    default=None,
    type=click.Path(),
    help="Write output to a file instead of stdout.",
)
@click.pass_context
def cli(ctx, env_name, domain, output_format, output_file):
    """cc - CommCare CLI tools for app builders.

    Interact with CommCare HQ APIs, manage environments, and run
    local FormPlayer instances.
    """
    ctx.ensure_object(dict)
    ctx.obj["env_name"] = env_name

    # Load defaults from config file if not provided on command line
    try:
        config = ConfigManager()
        cfg = config._read_config()
        if domain is None:
            domain = cfg.get("default_domain")
        if output_format == "json":
            # Only override if user didn't explicitly pass --format
            config_format = cfg.get("default_format")
            if config_format and config_format in ("json", "table", "csv"):
                output_format = config_format
    except Exception:
        pass

    ctx.obj["domain"] = domain
    ctx.obj["output_format"] = output_format
    ctx.obj["output_file"] = output_file


# Import and register subcommands
from .api import api  # noqa: E402
from .apps import app  # noqa: E402
from .auth import auth  # noqa: E402
from .cases import case  # noqa: E402
from .config_cmd import config_cmd  # noqa: E402
from .domains import domains  # noqa: E402
from .env import env  # noqa: E402
from .forms import form  # noqa: E402
from .lookup_tables import lookup_table  # noqa: E402
from .reports import report  # noqa: E402
from .users import user  # noqa: E402

cli.add_command(auth)
cli.add_command(env)
cli.add_command(config_cmd)
cli.add_command(api)
cli.add_command(domains)
cli.add_command(app)
cli.add_command(case)
cli.add_command(form)
cli.add_command(user)
cli.add_command(lookup_table)
cli.add_command(report)

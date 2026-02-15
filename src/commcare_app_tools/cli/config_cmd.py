"""cc config -- manage CLI configuration defaults."""

import click

from ..config.environments import ConfigManager
from ..utils.output import format_output, print_error, print_success


@click.group("config")
def config_cmd():
    """Manage CLI configuration defaults."""


@config_cmd.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Set a configuration default.

    Supported keys:

        default_domain  - Domain to use when --domain is not specified

        default_format  - Output format (json, table, csv)

    Examples:

        cc config set default_domain my-project

        cc config set default_format table
    """
    valid_keys = {"default_domain", "default_format"}
    if key not in valid_keys:
        print_error(f"Unknown config key '{key}'. Valid keys: {', '.join(sorted(valid_keys))}")
        raise SystemExit(1)

    if key == "default_format" and value not in ("json", "table", "csv"):
        print_error("default_format must be one of: json, table, csv")
        raise SystemExit(1)

    config = ConfigManager()
    cfg = config._read_config()
    cfg[key] = value
    config._write_config(cfg)
    print_success(f"Set {key} = {value}")


@config_cmd.command("get")
@click.argument("key")
def config_get(key):
    """Get a configuration value."""
    config = ConfigManager()
    cfg = config._read_config()
    value = cfg.get(key)
    if value is None:
        click.echo(f"{key}: (not set)")
    else:
        click.echo(f"{key}: {value}")


@config_cmd.command("show")
@click.pass_context
def config_show(ctx):
    """Show all configuration values."""
    config = ConfigManager()
    cfg = config._read_config()
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    # Show user-facing config (not the full environments dict)
    display = {
        "active_environment": cfg.get("active_environment", ""),
        "default_domain": cfg.get("default_domain", "(not set)"),
        "default_format": cfg.get("default_format", "(not set)"),
        "config_file": str(config.config_path),
        "credentials_file": str(config.credentials_path),
    }
    format_output(display, fmt=output_format, output_file=output_file)

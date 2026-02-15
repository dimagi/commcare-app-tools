"""FormPlayer Docker management commands."""

import click

from ..config.environments import ConfigManager
from ..formplayer.docker import (
    DockerNotFoundError,
    FormPlayerDocker,
)
from ..formplayer.settings import DEFAULT_FORMPLAYER_PORT
from ..utils.output import format_output, print_error, print_info, print_success


@click.group()
def formplayer():
    """Manage local FormPlayer Docker environment."""
    pass


@formplayer.command()
@click.option(
    "--port", "-p",
    default=DEFAULT_FORMPLAYER_PORT,
    help=f"Port to expose FormPlayer on (default: {DEFAULT_FORMPLAYER_PORT})",
)
@click.option(
    "--hq-host",
    default="http://host.docker.internal:8000",
    help="Local CommCare HQ URL (default: http://host.docker.internal:8000)",
)
@click.option(
    "--auth-key",
    default=None,
    help="Auth key for FormPlayer (default: localdevkey)",
)
@click.option(
    "--no-pull",
    is_flag=True,
    help="Skip pulling latest images before starting",
)
@click.pass_context
def start(ctx, port, hq_host, auth_key, no_pull):
    """Start local FormPlayer Docker environment.

    This starts FormPlayer along with its dependencies (Postgres, Redis)
    and connects it to a LOCAL CommCare HQ instance running on your machine.

    IMPORTANT: FormPlayer should only connect to local HQ, not production!
    The default connects to HQ at host.docker.internal:8000 (Docker's way
    of reaching localhost from inside a container).

    Example:
        cc formplayer start
        cc formplayer start --hq-host http://host.docker.internal:8000
        cc formplayer start --port 8090
        cc formplayer start --no-pull
    """
    config = ConfigManager()
    env_name = ctx.obj.get("env_name") if ctx.obj else None

    if not env_name:
        env_name = config.get_active_environment_name()

    print_info(f"Starting FormPlayer connected to local HQ at {hq_host}...")

    docker = FormPlayerDocker()

    try:
        success, message = docker.start(
            commcare_host=hq_host,
            port=port,
            auth_key=auth_key,
            pull=not no_pull,
        )
        if success:
            print_success(message)
            print_info(f"FormPlayer is now available at http://localhost:{port}")
            print_info("Use 'cc formplayer logs' to view logs")
            print_info("Use 'cc formplayer status' to check status")

            # Update environment config with formplayer URL
            config.update_environment(env_name, formplayer_url=f"http://localhost:{port}")
        else:
            print_error(message)
            raise SystemExit(1)
    except DockerNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)


@formplayer.command()
def stop():
    """Stop local FormPlayer Docker environment.

    Stops all FormPlayer containers but preserves data volumes.

    Example:
        cc formplayer stop
    """
    docker = FormPlayerDocker()
    print_info("Stopping FormPlayer...")

    success, message = docker.stop()
    if success:
        print_success(message)
    else:
        print_error(message)
        raise SystemExit(1)


@formplayer.command()
def restart():
    """Restart local FormPlayer Docker environment.

    Example:
        cc formplayer restart
    """
    docker = FormPlayerDocker()
    print_info("Restarting FormPlayer...")

    success, message = docker.restart()
    if success:
        print_success(message)
    else:
        print_error(message)
        raise SystemExit(1)


@formplayer.command()
@click.pass_context
def status(ctx):
    """Show status of local FormPlayer Docker environment.

    Example:
        cc formplayer status
    """
    output_format = ctx.obj.get("output_format", "table") if ctx.obj else "table"

    docker = FormPlayerDocker()
    service_status = docker.get_status()

    if service_status.error_message:
        print_error(service_status.error_message)
        raise SystemExit(1)

    status_data = {
        "formplayer": {
            "status": service_status.formplayer.value,
            "url": service_status.formplayer_url or "N/A",
        },
        "postgres": {
            "status": service_status.postgres.value,
        },
        "redis": {
            "status": service_status.redis.value,
        },
    }

    if output_format == "json":
        format_output(status_data, fmt="json")
    else:
        # Table format
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="FormPlayer Status")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("URL", style="dim")

        status_colors = {
            "running": "green",
            "stopped": "yellow",
            "not_found": "dim",
            "error": "red",
        }

        for service, info in status_data.items():
            status_val = info["status"]
            color = status_colors.get(status_val, "white")
            url = info.get("url", "")
            table.add_row(service, f"[{color}]{status_val}[/{color}]", url)

        console.print(table)


@formplayer.command()
@click.option(
    "--service", "-s",
    type=click.Choice(["formplayer", "postgres", "redis"]),
    default=None,
    help="Specific service to get logs from",
)
@click.option(
    "--follow", "-f",
    is_flag=True,
    help="Follow log output (stream)",
)
@click.option(
    "--tail", "-n",
    default=100,
    help="Number of lines to show from end of logs (default: 100)",
)
def logs(service, follow, tail):
    """View logs from FormPlayer Docker containers.

    Example:
        cc formplayer logs
        cc formplayer logs -f
        cc formplayer logs --service formplayer
        cc formplayer logs -n 50
    """
    docker = FormPlayerDocker()

    try:
        if follow:
            print_info("Streaming logs (Ctrl+C to stop)...")
            # For follow mode, we need to stream to stdout
            import subprocess

            from ..formplayer.settings import COMPOSE_FILE

            if not COMPOSE_FILE.exists():
                print_error("FormPlayer is not configured. Run 'cc formplayer start' first.")
                raise SystemExit(1)

            cmd = ["docker", "compose", "-f", str(COMPOSE_FILE), "logs", "-f", f"--tail={tail}"]
            if service:
                cmd.append(service)

            try:
                subprocess.run(cmd, cwd=COMPOSE_FILE.parent)
            except KeyboardInterrupt:
                print_info("\nStopped following logs")
        else:
            result = docker.logs(service=service, follow=False, tail=tail)
            if result.returncode != 0:
                print_error(f"Failed to get logs: {result.stderr}")
                raise SystemExit(1)
            print(result.stdout)
    except FileNotFoundError:
        print_error("FormPlayer is not configured. Run 'cc formplayer start' first.")
        raise SystemExit(1)


@formplayer.command()
def destroy():
    """Stop and remove all FormPlayer containers and data.

    WARNING: This will delete all FormPlayer data including Postgres database
    and Redis cache. This action cannot be undone.

    Example:
        cc formplayer destroy
    """
    if not click.confirm(
        "This will delete all FormPlayer data including the database. Continue?"
    ):
        print_info("Cancelled")
        return

    docker = FormPlayerDocker()
    print_info("Destroying FormPlayer environment...")

    success, message = docker.destroy()
    if success:
        print_success(message)
    else:
        print_error(message)
        raise SystemExit(1)


@formplayer.command()
def pull():
    """Pull latest FormPlayer Docker images.

    Example:
        cc formplayer pull
    """
    docker = FormPlayerDocker()
    print_info("Pulling latest FormPlayer images...")

    success, message = docker.pull()
    if success:
        print_success(message)
    else:
        print_error(message)
        raise SystemExit(1)


@formplayer.command()
@click.argument("url")
@click.pass_context
def connect(ctx, url):
    """Set a custom FormPlayer URL for the current environment.

    Use this to point at an external FormPlayer instance instead of
    running one locally.

    Example:
        cc formplayer connect http://formplayer.example.com:8080
        cc formplayer connect http://localhost:8080
    """
    config = ConfigManager()
    env_name = ctx.obj.get("env_name") if ctx.obj else None

    if not env_name:
        env_name = config.get_active_environment_name()

    # Validate URL format
    if not url.startswith(("http://", "https://")):
        print_error("URL must start with http:// or https://")
        raise SystemExit(1)

    config.update_environment(env_name, formplayer_url=url)
    print_success(f"FormPlayer URL set to {url} for environment '{env_name}'")


@formplayer.command()
@click.pass_context
def disconnect(ctx):
    """Clear the FormPlayer URL for the current environment.

    Example:
        cc formplayer disconnect
    """
    config = ConfigManager()
    env_name = ctx.obj.get("env_name") if ctx.obj else None

    if not env_name:
        env_name = config.get_active_environment_name()

    config.update_environment(env_name, formplayer_url=None)
    print_success(f"FormPlayer URL cleared for environment '{env_name}'")

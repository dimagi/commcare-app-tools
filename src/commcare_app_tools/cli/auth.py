"""cc auth -- authentication commands."""

import click

from ..auth.oauth import OAuthError, perform_oauth_login, revoke_token
from ..auth.token_store import token_status
from ..config.environments import ConfigManager
from ..utils.output import format_output, print_error, print_info, print_success


@click.group()
def auth():
    """Manage authentication with CommCare HQ."""


@auth.command()
@click.option(
    "--scopes", default=None,
    help="OAuth scopes to request (space-separated). Default: access_apis",
)
@click.pass_context
def login(ctx, scopes):
    """Authenticate with CommCare HQ via browser-based OAuth2 login.

    Opens your browser to log in to CommCare HQ. After approving access,
    you'll be redirected back and your credentials will be stored locally.
    """
    config = ConfigManager()
    env_name = ctx.obj.get("env_name")

    try:
        env = config.get_environment(env_name) if env_name else config.get_active_environment()
        env_name = env.name
    except ValueError as e:
        print_error(str(e))
        raise SystemExit(1)

    print_info(f"Logging in to {env.url} (environment: {env_name})...")

    try:
        credentials = perform_oauth_login(env, scopes=scopes)
    except OAuthError as e:
        print_error(str(e))
        raise SystemExit(1)

    # Try to get user info
    try:
        from ..auth.session import AuthenticatedClient
        temp_config = ConfigManager()
        temp_config.save_credentials(env_name, credentials)
        with AuthenticatedClient(temp_config, env_name) as client:
            response = client.get("/api/identity/v1/")
            if response.status_code == 200:
                user_info = response.json()
                credentials.user = user_info.get("username", "")
    except Exception:
        pass  # Non-critical -- we still have valid tokens

    config.save_credentials(env_name, credentials)

    user_display = credentials.user or "(unknown user)"
    print_success(f"Logged in as {user_display} on {env_name} ({env.url})")


@auth.command()
@click.pass_context
def logout(ctx):
    """Log out and clear stored credentials for the current environment."""
    config = ConfigManager()
    env_name = ctx.obj.get("env_name") or config.get_active_environment_name()

    try:
        env = config.get_environment(env_name)
        creds = config.get_credentials(env_name)

        # Revoke token on server (best-effort)
        if creds.is_authenticated:
            revoke_token(env, creds)

        config.clear_credentials(env_name)
        print_success(f"Logged out from {env_name} ({env.url})")

    except ValueError as e:
        print_error(str(e))
        raise SystemExit(1)


@auth.command()
@click.pass_context
def status(ctx):
    """Show authentication status for the current environment."""
    config = ConfigManager()
    env_name = ctx.obj.get("env_name") or config.get_active_environment_name()
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    try:
        info = token_status(config, env_name)
    except ValueError as e:
        print_error(str(e))
        raise SystemExit(1)

    if output_format == "json":
        format_output(info, fmt="json", output_file=output_file)
    else:
        if info["authenticated"]:
            minutes = info["expires_in"] // 60
            seconds = info["expires_in"] % 60
            print_success(f"Authenticated on {info['environment']} ({info['url']})")
            click.echo(f"  User:       {info['user']}")
            click.echo(f"  Expires in: {minutes}m {seconds}s")
            click.echo(f"  Scopes:     {', '.join(info['scopes'])}")
        else:
            print_info(f"Not authenticated on {info['environment']} ({info['url']})")
            click.echo("  Run 'cc auth login' to authenticate.")


@auth.command()
@click.pass_context
def whoami(ctx):
    """Show details about the currently authenticated user."""
    config = ConfigManager()
    env_name = ctx.obj.get("env_name") or config.get_active_environment_name()
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    try:
        from ..api.client import CommCareAPI
        with CommCareAPI(config, env_name=env_name) as api_client:
            user_info = api_client.get_user_info()
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(user_info, fmt=output_format, output_file=output_file)

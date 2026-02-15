"""CommCare CLI JAR management commands."""

import click

from ..commcare_cli.builder import (
    BuildError,
    CommCareCLIBuilder,
    GradleNotFoundError,
    JavaNotFoundError,
    JavaVersionError,
)
from ..commcare_cli.runner import CommCareCLIRunner
from ..utils.output import print_error, print_info, print_success


@click.group("cli")
def commcare_cli():
    """Manage and run the CommCare CLI (commcare-cli.jar).

    The CommCare CLI allows you to validate and run CommCare apps locally
    without needing a full CommCare HQ setup.
    """
    pass


@commcare_cli.command()
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force rebuild even if JAR already exists",
)
def build(force):
    """Build commcare-cli.jar from source.

    Requires Java 17+ and Gradle to be installed.

    Example:
        cc cli build
        cc cli build --force
    """
    builder = CommCareCLIBuilder()

    if builder.is_built() and not force:
        print_info(f"commcare-cli.jar already exists at {builder.jar_path}")
        print_info("Use --force to rebuild")
        return

    try:
        jar_path = builder.build(force=force)
        print_success(f"Built: {jar_path}")
    except JavaNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)
    except JavaVersionError as e:
        print_error(str(e))
        raise SystemExit(1)
    except GradleNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)
    except BuildError as e:
        print_error(f"Build failed: {e}")
        raise SystemExit(1)


@commcare_cli.command()
def clean():
    """Remove cached commcare-cli.jar.

    Example:
        cc cli clean
    """
    builder = CommCareCLIBuilder()
    if builder.is_built():
        builder.clean()
        print_success("Cached JAR removed")
    else:
        print_info("No cached JAR to remove")


@commcare_cli.command()
def status():
    """Show status of commcare-cli.jar.

    Example:
        cc cli status
    """
    builder = CommCareCLIBuilder()

    print_info(f"Submodule path: {builder.commcare_core_path}")
    print_info(f"Submodule exists: {builder.commcare_core_path.exists()}")
    print_info(f"Cache directory: {builder.cache_dir}")
    print_info(f"JAR path: {builder.jar_path}")
    print_info(f"JAR built: {builder.is_built()}")

    # Check Java
    try:
        java_path = builder.find_java()
        version = builder.check_java_version(java_path)
        print_success(f"Java {version} found at: {java_path}")
    except (JavaNotFoundError, JavaVersionError) as e:
        print_error(str(e))

    # Check Gradle
    try:
        gradle_cmd = builder.find_gradle()
        print_success(f"Gradle found: {' '.join(gradle_cmd)}")
    except GradleNotFoundError as e:
        print_error(str(e))


@commcare_cli.command()
@click.argument("app_path", type=click.Path(exists=True))
def validate(app_path):
    """Validate a CommCare app.

    APP_PATH is the path to an app CCZ file or extracted app directory.

    Example:
        cc cli validate ./my-app.ccz
        cc cli validate ./extracted-app/
    """
    try:
        runner = CommCareCLIRunner()
        result = runner.validate(app_path)

        if result.returncode == 0:
            print_success("App is valid")
            if result.stdout:
                print(result.stdout)
        else:
            print_error("Validation failed")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
            raise SystemExit(1)

    except (JavaNotFoundError, JavaVersionError, BuildError) as e:
        print_error(str(e))
        raise SystemExit(1)


@commcare_cli.command()
@click.argument("app_path", type=click.Path(exists=True))
@click.option(
    "--restore", "-r",
    type=click.Path(exists=True),
    help="Path to restore XML file for offline mode",
)
@click.option(
    "--demo", "-d",
    is_flag=True,
    help="Use the demo user restore bundled in the app",
)
def play(app_path, restore, demo):
    """Run a CommCare app interactively.

    APP_PATH is the path to an app CCZ file or extracted app directory.

    This launches an interactive terminal session where you can navigate
    menus, fill out forms, and test app logic.

    Example:
        cc cli play ./my-app.ccz --demo
        cc cli play ./my-app.ccz --restore ./user-restore.xml
    """
    if restore and demo:
        print_error("Cannot use both --restore and --demo")
        raise SystemExit(1)

    try:
        runner = CommCareCLIRunner()
        print_info("Starting CommCare CLI (Ctrl+C to exit)...")
        exit_code = runner.play_interactive(
            app_path,
            restore_file=restore,
            use_demo_user=demo,
        )
        raise SystemExit(exit_code)

    except (JavaNotFoundError, JavaVersionError, BuildError) as e:
        print_error(str(e))
        raise SystemExit(1)

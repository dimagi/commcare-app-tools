"""cc test -- run end-to-end CommCare form tests."""

import click

from ..config.environments import ConfigManager
from ..test.definition import TestDefinition, generate_skeleton
from ..test.runner import TestRunner
from ..utils.output import format_output, print_error


@click.group()
def test():
    """Run CommCare form tests.

    Define tests in YAML files that specify an app, user, navigation
    steps, and form answers. The test runner downloads the app and
    restore if needed, then executes the form via commcare-cli.jar.
    """


@test.command("run")
@click.argument("test_file", type=click.Path(exists=True))
@click.option("--timeout", type=int, help="Override timeout from test file (seconds).")
@click.option(
    "--output-xml",
    type=click.Path(),
    help="Save completed form XML to this file.",
)
@click.option(
    "--show-output",
    is_flag=True,
    default=False,
    help="Print raw CLI stdout/stderr after the test.",
)
@click.pass_context
def run_test(ctx, test_file, timeout, output_xml, show_output):
    """Run a CommCare form test from a YAML definition file.

    The test file specifies the domain, app, user, navigation steps,
    and form answers. The runner will:

    1. Download the app CCZ if not already cached.

    2. Download the user's restore (via login-as) if not already cached.

    3. Execute the form by piping navigation + :replay input to commcare-cli.jar.

    4. Report pass/fail and optionally save the completed form XML.

    Examples:

        cc test run tests/register-patient.yaml

        cc test run tests/register-patient.yaml --output-xml result.xml

        cc --domain other-domain test run tests/my-test.yaml
    """
    config = ConfigManager()
    domain = ctx.obj.get("domain")
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    # Load test definition
    try:
        definition = TestDefinition.from_file(test_file)
    except (FileNotFoundError, ValueError) as e:
        print_error(str(e))
        raise SystemExit(1)

    # Apply CLI overrides
    if domain:
        definition = definition.with_overrides(domain=domain)
    if timeout:
        definition.timeout = timeout

    # Run the test
    runner = TestRunner(config, env_name=env_name)
    result = runner.run_test(definition)

    # Save form XML if requested
    if output_xml and result.form_xml:
        try:
            with open(output_xml, "w", encoding="utf-8") as f:
                f.write(result.form_xml)
            click.echo(f"  Form XML saved to: {output_xml}", err=True)
        except OSError as e:
            print_error(f"Failed to save XML: {e}")

    # Show raw output if requested
    if show_output:
        click.echo("", err=True)
        click.echo("--- stdout ---", err=True)
        click.echo(result.stdout or "(empty)", err=True)
        if result.stderr:
            click.echo("--- stderr ---", err=True)
            click.echo(result.stderr, err=True)

    # Output structured result
    click.echo("", err=True)
    format_output(result.to_dict(), fmt=output_format, output_file=output_file)

    # Exit with appropriate code
    if not result.passed:
        raise SystemExit(1)


@test.command("init")
@click.option(
    "--output",
    "output_path",
    type=click.Path(),
    default=None,
    help="Write skeleton to a file instead of stdout.",
)
def init_test(output_path):
    """Generate a skeleton test YAML file.

    Creates a commented template with all available fields that you
    can fill in for your specific app and form.

    Examples:

        cc test init

        cc test init --output tests/my-test.yaml
    """
    skeleton = generate_skeleton()

    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(skeleton)
            click.echo(f"Test skeleton written to: {output_path}", err=True)
        except OSError as e:
            print_error(f"Failed to write file: {e}")
            raise SystemExit(1)
    else:
        click.echo(skeleton)

"""cc api -- raw API access commands."""

import json

import click

from ..api.client import CommCareAPI
from ..config.environments import ConfigManager
from ..utils.output import format_output, print_error


@click.group()
def api():
    """Make raw API requests to CommCare HQ."""


@api.command("get")
@click.argument("path")
@click.option("--params", default=None, help="Query parameters as JSON string.")
@click.option("--limit", default=None, type=int, help="Limit number of results.")
@click.option("--offset", default=0, type=int, help="Pagination offset.")
@click.pass_context
def api_get(ctx, path, params, limit, offset):
    """Make a GET request to a CommCare HQ API endpoint.

    PATH is the API path, e.g. 'api/case/v2/' or '/a/my-domain/api/case/v2/'.
    If PATH doesn't start with /a/, the --domain flag is used to build the full path.

    Examples:

        cc --domain my-project api get api/case/v2/

        cc api get /a/my-project/api/case/v2/ --limit 10

        cc api get api/user/v1/ --params '{"username": "worker1"}'
    """
    config = ConfigManager()
    domain = ctx.obj.get("domain")
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    query_params = {}
    if params:
        try:
            query_params = json.loads(params)
        except json.JSONDecodeError as e:
            print_error(f"Invalid JSON for --params: {e}")
            raise SystemExit(1)

    if limit is not None:
        query_params["limit"] = limit
    if offset:
        query_params["offset"] = offset

    try:
        with CommCareAPI(config, domain=domain, env_name=env_name) as api_client:
            response = api_client.get(path, params=query_params)
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(data, fmt=output_format, output_file=output_file)


@api.command("post")
@click.argument("path")
@click.option("--data", "body", default=None, help="Request body as JSON string.")
@click.option("--file", "body_file", default=None, type=click.Path(exists=True),
              help="Read request body from a JSON file.")
@click.pass_context
def api_post(ctx, path, body, body_file):
    """Make a POST request to a CommCare HQ API endpoint.

    PATH is the API path. Provide the request body via --data or --file.

    Examples:

        cc --domain my-project api post api/case/v2/ --data '{"case_type": "patient"}'

        cc api post /a/my-project/api/case/v2/ --file payload.json
    """
    config = ConfigManager()
    domain = ctx.obj.get("domain")
    env_name = ctx.obj.get("env_name")
    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")

    json_body = None
    if body:
        try:
            json_body = json.loads(body)
        except json.JSONDecodeError as e:
            print_error(f"Invalid JSON for --data: {e}")
            raise SystemExit(1)
    elif body_file:
        try:
            with open(body_file, "r", encoding="utf-8") as f:
                json_body = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print_error(f"Error reading file: {e}")
            raise SystemExit(1)

    try:
        with CommCareAPI(config, domain=domain, env_name=env_name) as api_client:
            response = api_client.post(path, json=json_body)
            response.raise_for_status()
            try:
                data = response.json()
            except json.JSONDecodeError:
                click.echo(response.text)
                return
    except Exception as e:
        print_error(str(e))
        raise SystemExit(1)

    format_output(data, fmt=output_format, output_file=output_file)

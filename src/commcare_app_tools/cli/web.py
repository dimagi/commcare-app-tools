"""Web UI commands."""

import socket
import webbrowser

import click

from ..utils.output import print_error, print_info, print_success


def find_available_port(host: str, start_port: int, max_attempts: int = 20) -> int:
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, port))
                return port
        except OSError:
            continue
    raise RuntimeError(
        f"No available port found in range {start_port}-{start_port + max_attempts - 1}"
    )


@click.group()
def web():
    """Start and manage the local web UI."""
    pass


@web.command()
@click.option(
    "--port", "-p",
    default=8080,
    help="Preferred port (will auto-increment if in use)",
)
@click.option(
    "--host",
    default="127.0.0.1",
    help="Host to bind to (default: 127.0.0.1)",
)
@click.option(
    "--no-browser",
    is_flag=True,
    help="Don't open browser automatically",
)
@click.option(
    "--reload",
    is_flag=True,
    help="Enable auto-reload for development",
)
def start(port: int, host: str, no_browser: bool, reload: bool):
    """Start the local web UI server.

    This launches a local web server that provides:
    - A wizard to create test configurations
    - An interactive terminal for running CommCare forms
    - Workspace management for downloaded artifacts

    Example:
        cc web start
        cc web start --port 3000
        cc web start --reload  # For development
    """
    import uvicorn

    # Find an available port
    try:
        actual_port = find_available_port(host, port)
    except RuntimeError as e:
        print_error(str(e))
        raise SystemExit(1)

    if actual_port != port:
        print_info(f"Port {port} in use, using {actual_port}")

    url = f"http://{host}:{actual_port}"
    print_info(f"Starting web UI at {url}")

    if not no_browser:
        # Open browser after a short delay (server needs to start)
        import threading

        def open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open(url)

        threading.Thread(target=open_browser, daemon=True).start()

    try:
        uvicorn.run(
            "commcare_app_tools.web.app:app",
            host=host,
            port=actual_port,
            reload=reload,
            log_level="info",
        )
    except KeyboardInterrupt:
        print_info("\nServer stopped")
    except Exception as e:
        print_error(f"Failed to start server: {e}")
        raise SystemExit(1)


@web.command()
def status():
    """Check if the web UI dependencies are ready.

    This verifies that:
    - The CommCare CLI JAR is built
    - Java is available
    - All required Python packages are installed
    """
    from ..commcare_cli.builder import CommCareCLIBuilder

    builder = CommCareCLIBuilder()

    # Check Java
    try:
        java_path = builder.find_java()
        version = builder.check_java_version(java_path)
        print_success(f"Java {version} found at: {java_path}")
    except Exception as e:
        print_error(f"Java: {e}")

    # Check CLI JAR
    if builder.is_built():
        print_success(f"CommCare CLI JAR: {builder.jar_path}")
    else:
        print_error("CommCare CLI JAR not built. Run 'cc cli build' first.")

    # Check Python packages
    packages = ["fastapi", "uvicorn", "websockets"]
    if __import__("sys").platform == "win32":
        packages.append("winpty")
    else:
        packages.append("ptyprocess")

    for pkg in packages:
        try:
            __import__(pkg)
            print_success(f"Python package '{pkg}' installed")
        except ImportError:
            print_error(f"Python package '{pkg}' not installed")

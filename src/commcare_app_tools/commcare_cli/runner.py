"""Run commcare-cli.jar commands."""

import subprocess
from typing import Optional

from .builder import CommCareCLIBuilder


class CommCareCLIRunner:
    """Run commcare-cli.jar commands."""

    def __init__(self, builder: Optional[CommCareCLIBuilder] = None):
        """
        Initialize the runner.

        Args:
            builder: CommCareCLIBuilder instance. Creates one if not provided.
        """
        self.builder = builder or CommCareCLIBuilder()

    def run(
        self,
        command: str,
        args: list[str],
        timeout: Optional[int] = None,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Run a commcare-cli command.

        Args:
            command: CLI command (e.g., "validate", "play")
            args: Arguments for the command
            timeout: Timeout in seconds (None for no timeout)
            capture_output: Whether to capture stdout/stderr

        Returns:
            CompletedProcess with results
        """
        jar_path = self.builder.get_jar_path()
        java_path = self.builder.find_java()

        cmd = [java_path, "-jar", str(jar_path), command] + args

        return subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
        )

    def validate(self, app_path: str, timeout: int = 60) -> subprocess.CompletedProcess:
        """
        Validate a CommCare app.

        Args:
            app_path: Path to app CCZ or directory
            timeout: Timeout in seconds

        Returns:
            CompletedProcess with validation results
        """
        return self.run("validate", [app_path], timeout=timeout)

    def play(
        self,
        app_path: str,
        restore_file: Optional[str] = None,
        use_demo_user: bool = False,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> subprocess.CompletedProcess:
        """
        Play/run a CommCare app interactively.

        Args:
            app_path: Path to app CCZ or directory
            restore_file: Path to restore XML file (for offline mode)
            use_demo_user: Use the demo user restore bundled in the app
            username: Username for remote restore
            password: Password for remote restore
            timeout: Timeout in seconds (None for interactive)

        Returns:
            CompletedProcess with results
        """
        args = [app_path]

        if restore_file:
            args.extend(["-r", restore_file])
        elif use_demo_user:
            args.append("-d")

        if username and password:
            args.extend([username, password])

        return self.run("play", args, timeout=timeout, capture_output=False)

    def play_interactive(
        self,
        app_path: str,
        restore_file: Optional[str] = None,
        use_demo_user: bool = False,
    ) -> int:
        """
        Play a CommCare app interactively (no capture, direct terminal I/O).

        Args:
            app_path: Path to app CCZ or directory
            restore_file: Path to restore XML file (for offline mode)
            use_demo_user: Use the demo user restore bundled in the app

        Returns:
            Exit code from the CLI
        """
        jar_path = self.builder.get_jar_path()
        java_path = self.builder.find_java()

        args = [java_path, "-jar", str(jar_path), "play", app_path]

        if restore_file:
            args.extend(["-r", restore_file])
        elif use_demo_user:
            args.append("-d")

        # Run without capturing - direct terminal interaction
        result = subprocess.run(args)
        return result.returncode

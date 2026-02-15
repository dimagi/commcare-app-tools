"""Docker container lifecycle management for FormPlayer."""

import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from .compose import FormPlayerComposeGenerator
from .settings import (
    COMPOSE_FILE,
    DEFAULT_FORMPLAYER_PORT,
    FORMPLAYER_CONTAINER,
    POSTGRES_CONTAINER,
    REDIS_CONTAINER,
)


class ContainerStatus(Enum):
    """Status of a Docker container."""
    RUNNING = "running"
    STOPPED = "stopped"
    NOT_FOUND = "not_found"
    ERROR = "error"


@dataclass
class ServiceStatus:
    """Status of a FormPlayer service."""
    formplayer: ContainerStatus
    postgres: ContainerStatus
    redis: ContainerStatus
    formplayer_url: Optional[str] = None
    error_message: Optional[str] = None


class DockerNotFoundError(Exception):
    """Raised when Docker is not installed or not running."""
    pass


class FormPlayerDocker:
    """Manage FormPlayer Docker containers."""

    def __init__(self, compose_file: Optional[Path] = None):
        """
        Initialize FormPlayer Docker manager.

        Args:
            compose_file: Path to docker-compose.yml. Defaults to standard location.
        """
        self.compose_file = compose_file or COMPOSE_FILE

    @staticmethod
    def check_docker_available() -> bool:
        """Check if Docker is installed and running."""
        docker_path = shutil.which("docker")
        if not docker_path:
            return False

        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    @staticmethod
    def check_docker_compose_available() -> bool:
        """Check if Docker Compose is available (either plugin or standalone)."""
        # Try docker compose (plugin)
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Try docker-compose (standalone)
        docker_compose_path = shutil.which("docker-compose")
        if docker_compose_path:
            try:
                result = subprocess.run(
                    ["docker-compose", "version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                return result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        return False

    def _get_compose_command(self) -> list[str]:
        """Get the appropriate docker compose command."""
        # Prefer docker compose plugin
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return ["docker", "compose"]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Fall back to docker-compose standalone
        return ["docker-compose"]

    def _run_compose(
        self,
        *args: str,
        capture_output: bool = True,
        timeout: Optional[int] = 60,
    ) -> subprocess.CompletedProcess:
        """Run a docker compose command."""
        if not self.compose_file.exists():
            raise FileNotFoundError(
                f"Docker Compose file not found: {self.compose_file}. "
                "Run 'cc formplayer start' to generate it."
            )

        cmd = self._get_compose_command() + ["-f", str(self.compose_file)] + list(args)

        return subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            cwd=self.compose_file.parent,
        )

    def _get_container_status(self, container_name: str) -> ContainerStatus:
        """Get the status of a specific container."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Status}}", container_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return ContainerStatus.NOT_FOUND

            status = result.stdout.strip().lower()
            if status == "running":
                return ContainerStatus.RUNNING
            else:
                return ContainerStatus.STOPPED
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ContainerStatus.ERROR

    def get_status(self) -> ServiceStatus:
        """Get the status of all FormPlayer services."""
        if not self.check_docker_available():
            return ServiceStatus(
                formplayer=ContainerStatus.ERROR,
                postgres=ContainerStatus.ERROR,
                redis=ContainerStatus.ERROR,
                error_message="Docker is not installed or not running",
            )

        fp_status = self._get_container_status(FORMPLAYER_CONTAINER)
        pg_status = self._get_container_status(POSTGRES_CONTAINER)
        redis_status = self._get_container_status(REDIS_CONTAINER)

        # Determine FormPlayer URL if running
        formplayer_url = None
        if fp_status == ContainerStatus.RUNNING:
            formplayer_url = f"http://localhost:{DEFAULT_FORMPLAYER_PORT}"

        return ServiceStatus(
            formplayer=fp_status,
            postgres=pg_status,
            redis=redis_status,
            formplayer_url=formplayer_url,
        )

    def start(
        self,
        commcare_host: str,
        port: int = DEFAULT_FORMPLAYER_PORT,
        auth_key: Optional[str] = None,
        pull: bool = True,
    ) -> tuple[bool, str]:
        """
        Start FormPlayer and its dependencies.

        Args:
            commcare_host: CommCare HQ URL to connect to
            port: Port to expose FormPlayer on
            auth_key: Optional auth key (defaults to localdevkey)
            pull: Whether to pull latest images before starting

        Returns:
            Tuple of (success, message)
        """
        if not self.check_docker_available():
            raise DockerNotFoundError(
                "Docker is not installed or not running. "
                "Please install Docker Desktop and ensure it's running."
            )

        if not self.check_docker_compose_available():
            raise DockerNotFoundError(
                "Docker Compose is not available. "
                "Please install Docker Compose or use Docker Desktop which includes it."
            )

        # Generate compose file
        generator = FormPlayerComposeGenerator(
            commcare_host=commcare_host,
            formplayer_port=port,
            auth_key=auth_key or "localdevkey",
        )
        generator.ensure_data_dirs()
        generator.write_compose_file(self.compose_file)

        # Pull images if requested
        if pull:
            pull_result = self._run_compose("pull", timeout=300)
            if pull_result.returncode != 0:
                return False, f"Failed to pull images: {pull_result.stderr}"

        # Start services
        result = self._run_compose("up", "-d", timeout=120)
        if result.returncode != 0:
            return False, f"Failed to start services: {result.stderr}"

        return True, f"FormPlayer started at http://localhost:{port}"

    def stop(self) -> tuple[bool, str]:
        """
        Stop FormPlayer and its dependencies.

        Returns:
            Tuple of (success, message)
        """
        if not self.compose_file.exists():
            return True, "FormPlayer is not configured"

        result = self._run_compose("down", timeout=60)
        if result.returncode != 0:
            return False, f"Failed to stop services: {result.stderr}"

        return True, "FormPlayer stopped"

    def restart(self) -> tuple[bool, str]:
        """
        Restart FormPlayer services.

        Returns:
            Tuple of (success, message)
        """
        result = self._run_compose("restart", timeout=120)
        if result.returncode != 0:
            return False, f"Failed to restart services: {result.stderr}"

        return True, "FormPlayer restarted"

    def logs(
        self,
        service: Optional[str] = None,
        follow: bool = False,
        tail: int = 100,
    ) -> subprocess.CompletedProcess:
        """
        Get logs from FormPlayer services.

        Args:
            service: Specific service to get logs from (formplayer, postgres, redis)
            follow: Whether to follow log output (streaming)
            tail: Number of lines to show from end of logs

        Returns:
            CompletedProcess with logs in stdout
        """
        args = ["logs", f"--tail={tail}"]
        if follow:
            args.append("-f")
        if service:
            args.append(service)

        return self._run_compose(
            *args,
            capture_output=not follow,
            timeout=None if follow else 30,
        )

    def destroy(self) -> tuple[bool, str]:
        """
        Stop and remove all containers, networks, and volumes.

        Returns:
            Tuple of (success, message)
        """
        if not self.compose_file.exists():
            return True, "FormPlayer is not configured"

        result = self._run_compose("down", "-v", "--remove-orphans", timeout=60)
        if result.returncode != 0:
            return False, f"Failed to destroy services: {result.stderr}"

        return True, "FormPlayer destroyed (containers and volumes removed)"

    def pull(self) -> tuple[bool, str]:
        """
        Pull latest FormPlayer images.

        Returns:
            Tuple of (success, message)
        """
        if not self.compose_file.exists():
            return False, "FormPlayer is not configured. Run 'cc formplayer start' first."

        result = self._run_compose("pull", timeout=300)
        if result.returncode != 0:
            return False, f"Failed to pull images: {result.stderr}"

        return True, "Images updated. Run 'cc formplayer restart' to use new images."

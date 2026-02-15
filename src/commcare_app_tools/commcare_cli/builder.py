"""Build commcare-cli.jar from the commcare-core submodule."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

# Path to commcare-core submodule (relative to project root)
# builder.py -> commcare_cli -> commcare_app_tools -> src -> commcare-app-tools (project root)
_project_root = Path(__file__).parent.parent.parent.parent
COMMCARE_CORE_SUBMODULE = _project_root / "libs" / "commcare-core"

# Gradle wrapper in our project root
GRADLEW_BAT = _project_root / "gradlew.bat"
GRADLEW_SH = _project_root / "gradlew"

# JAR is stored in .cc/ subdirectory of current working directory
CLI_JAR_NAME = "commcare-cli.jar"
CLI_JAR_SUBDIR = ".cc"

# Minimum Java version required
MIN_JAVA_VERSION = 17


class JavaNotFoundError(Exception):
    """Raised when Java is not installed or not in PATH."""
    pass


class JavaVersionError(Exception):
    """Raised when Java version is too old."""
    pass


class GradleNotFoundError(Exception):
    """Raised when Gradle is not available."""
    pass


class BuildError(Exception):
    """Raised when the build fails."""
    pass


class CommCareCLIBuilder:
    """Builds and manages the commcare-cli.jar."""

    def __init__(self, commcare_core_path: Optional[Path] = None):
        """
        Initialize the builder.

        Args:
            commcare_core_path: Path to commcare-core source. Defaults to submodule.
        """
        self.commcare_core_path = commcare_core_path or COMMCARE_CORE_SUBMODULE
        # JAR lives in .cc/ subdirectory of current working directory
        self.cache_dir = Path.cwd() / CLI_JAR_SUBDIR
        self.jar_path = self.cache_dir / CLI_JAR_NAME

    def get_jar_path(self) -> Path:
        """
        Get path to commcare-cli.jar, building if necessary.

        Returns:
            Path to the JAR file.

        Raises:
            JavaNotFoundError: If Java is not installed.
            JavaVersionError: If Java version is too old.
            BuildError: If the build fails.
        """
        # Check if we have a cached JAR
        if self.jar_path.exists():
            return self.jar_path

        # Need to build
        self.build()
        return self.jar_path

    def find_java(self) -> str:
        """
        Find Java executable.

        Returns:
            Path to java executable.

        Raises:
            JavaNotFoundError: If Java is not found.
        """
        # Check JAVA_HOME first
        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            java_path = Path(java_home) / "bin" / "java"
            if os.name == "nt":
                java_path = java_path.with_suffix(".exe")
            if java_path.exists():
                return str(java_path)

        # Check PATH
        java_cmd = shutil.which("java")
        if java_cmd:
            return java_cmd

        raise JavaNotFoundError(
            "Java not found. Please install Java 17+ and ensure it's in your PATH "
            "or set JAVA_HOME environment variable."
        )

    def check_java_version(self, java_path: str) -> int:
        """
        Check Java version.

        Args:
            java_path: Path to java executable.

        Returns:
            Major version number.

        Raises:
            JavaVersionError: If version is too old or can't be determined.
        """
        try:
            result = subprocess.run(
                [java_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # Java version is printed to stderr
            output = result.stderr or result.stdout

            # Parse version from output like:
            # openjdk version "17.0.1" 2021-10-19
            # java version "21.0.1" 2023-10-17
            for line in output.split("\n"):
                if "version" in line.lower():
                    # Extract version string
                    import re
                    match = re.search(r'"(\d+)', line)
                    if match:
                        version = int(match.group(1))
                        if version < MIN_JAVA_VERSION:
                            raise JavaVersionError(
                                f"Java {version} found, but Java {MIN_JAVA_VERSION}+ is required. "
                                "Please upgrade your Java installation."
                            )
                        return version

            raise JavaVersionError(
                f"Could not determine Java version from output: {output}"
            )
        except subprocess.TimeoutExpired:
            raise JavaVersionError("Timed out checking Java version")
        except FileNotFoundError:
            raise JavaNotFoundError(f"Java not found at {java_path}")

    def find_gradle(self) -> list[str]:
        """
        Find Gradle command (wrapper or system).

        Returns:
            Command list to run Gradle.

        Raises:
            GradleNotFoundError: If Gradle is not found.
        """
        # Check for Gradle wrapper in commcare-core first
        if os.name == "nt":
            submodule_wrapper = self.commcare_core_path / "gradlew.bat"
        else:
            submodule_wrapper = self.commcare_core_path / "gradlew"

        if submodule_wrapper.exists():
            return [str(submodule_wrapper)]

        # Check for our project's Gradle wrapper
        if os.name == "nt":
            our_wrapper = GRADLEW_BAT
        else:
            our_wrapper = GRADLEW_SH

        if our_wrapper.exists():
            return [str(our_wrapper)]

        # Check for system Gradle
        gradle_cmd = shutil.which("gradle")
        if gradle_cmd:
            return [gradle_cmd]

        raise GradleNotFoundError(
            "Gradle not found. Please install Gradle and ensure it's in your PATH."
        )

    def build(self, force: bool = False) -> Path:
        """
        Build commcare-cli.jar from source.

        Args:
            force: If True, rebuild even if JAR exists.

        Returns:
            Path to the built JAR.

        Raises:
            JavaNotFoundError: If Java is not found.
            JavaVersionError: If Java version is too old.
            GradleNotFoundError: If Gradle is not found.
            BuildError: If the build fails.
        """
        if self.jar_path.exists() and not force:
            return self.jar_path

        # Verify commcare-core submodule exists
        if not self.commcare_core_path.exists():
            raise BuildError(
                f"commcare-core not found at {self.commcare_core_path}. "
                "Run 'git submodule update --init' to initialize it."
            )

        build_gradle = self.commcare_core_path / "build.gradle"
        if not build_gradle.exists():
            raise BuildError(
                f"build.gradle not found in {self.commcare_core_path}. "
                "The commcare-core submodule may be empty. "
                "Run 'git submodule update --init' to initialize it."
            )

        # Check Java
        java_path = self.find_java()
        java_version = self.check_java_version(java_path)

        # Find Gradle
        gradle_cmd = self.find_gradle()

        # Build the CLI JAR
        print(f"Building commcare-cli.jar (Java {java_version} detected)...")

        try:
            result = subprocess.run(
                gradle_cmd + ["cliJar", "--no-daemon"],
                cwd=self.commcare_core_path,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                raise BuildError(
                    f"Gradle build failed:\n{result.stdout}\n{result.stderr}"
                )

        except subprocess.TimeoutExpired:
            raise BuildError("Build timed out after 5 minutes")

        # Find the built JAR
        build_dir = self.commcare_core_path / "build" / "libs"
        built_jars = list(build_dir.glob("commcare-cli*.jar"))

        if not built_jars:
            raise BuildError(
                f"Build completed but commcare-cli.jar not found in {build_dir}"
            )

        # Copy to cache
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(built_jars[0], self.jar_path)

        print(f"Built and cached: {self.jar_path}")
        return self.jar_path

    def clean(self) -> None:
        """Remove cached JAR, forcing rebuild on next use."""
        if self.jar_path.exists():
            self.jar_path.unlink()
            print(f"Removed cached JAR: {self.jar_path}")

    def is_built(self) -> bool:
        """Check if JAR is already built and cached."""
        return self.jar_path.exists()

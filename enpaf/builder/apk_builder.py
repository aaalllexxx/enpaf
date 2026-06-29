"""
ENPAF Builder — APK Builder
Generates a Gradle-based Android project and builds APK using Chaquopy.
Works natively on Windows.
"""

import os
import platform
import shutil
import subprocess
from typing import Optional

from enpaf.cli import ui
from enpaf.builder.project_generator import ProjectGenerator


class APKBuilder:
    """
    Generates and builds an Android project from an ENPAF project.
    Uses Gradle + Chaquopy to embed Python into an Android WebView app.
    """

    GRADLE_WRAPPER_VERSION = "8.4"

    def __init__(self, project_dir: str, config: dict, build_dir: str):
        self.project_dir = project_dir
        self.config = config
        self.build_dir = build_dir
        self.android_project_dir = os.path.join(build_dir, "android")
        self.generator = ProjectGenerator(
            project_dir, config, self.android_project_dir
        )

    def generate_project(self, release: bool = False, keystore_path: Optional[str] = None):
        """Generate the complete Android/Gradle project.

        `release` enables a signing config so the release APK can be installed.
        """
        self.generator.release = release
        self.generator.keystore_path = keystore_path
        self.generator.generate()

    def build_apk(self, release: bool = False, keystore_path: Optional[str] = None) -> Optional[str]:
        """Build the APK using Gradle. Returns path to APK or None."""
        gradle_cmd = self._get_gradle_command()
        if not gradle_cmd:
            ui.error("Gradle not found. Install JDK + Gradle or Android Studio.")
            return None

        task = "assembleRelease" if release else "assembleDebug"
        ui.info(f"Running: gradle {task}")
        ui.newline()

        try:
            env = os.environ.copy()
            android_home = env.get("ANDROID_HOME", "")
            if android_home:
                env["ANDROID_SDK_ROOT"] = android_home

            process = subprocess.Popen(
                gradle_cmd + [task, "--stacktrace"],
                cwd=self.android_project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                shell=(platform.system() == "Windows"),
            )

            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                if "BUILD SUCCESSFUL" in line:
                    ui.success(line)
                elif "BUILD FAILED" in line or "FAILURE" in line:
                    ui.error(line)
                elif "ERROR" in line.upper():
                    ui.error(line)
                elif line.startswith(">"):
                    ui.info(line)
                else:
                    ui.dim(f"  {line}")

            process.wait()
            if process.returncode != 0:
                ui.error(f"Gradle exited with code {process.returncode}")
                return None

        except FileNotFoundError:
            ui.error("Could not run Gradle. Make sure Java JDK is installed.")
            return None
        except Exception as e:
            ui.error(f"Build error: {e}")
            return None

        # Find the APK
        build_type = "release" if release else "debug"
        apk_dir = os.path.join(
            self.android_project_dir, "app", "build", "outputs", "apk", build_type
        )
        if os.path.isdir(apk_dir):
            for f in os.listdir(apk_dir):
                if f.endswith(".apk"):
                    return os.path.join(apk_dir, f)
        return None

    def _get_gradle_command(self) -> Optional[list]:
        """Get the Gradle command for the current platform.

        Prefer the project's wrapper, but only when its bootstrap jar is present
        (a wrapper script without the jar cannot start). Otherwise fall back to a
        system-wide Gradle on PATH.
        """
        wrapper_jar = os.path.join(
            self.android_project_dir, "gradle", "wrapper", "gradle-wrapper.jar"
        )
        if os.path.isfile(wrapper_jar):
            name = "gradlew.bat" if platform.system() == "Windows" else "gradlew"
            wrapper = os.path.join(self.android_project_dir, name)
            if os.path.isfile(wrapper):
                return [wrapper]
        gradle = shutil.which("gradle")
        if gradle:
            return [gradle]
        return None

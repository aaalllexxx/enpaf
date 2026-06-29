"""
ENPAF CLI — Doctor Command
Checks the development environment for required tools.
"""

import os
import sys
import shutil
import subprocess
import platform

from enpaf.cli import ui


def cmd_doctor(args):
    """Check the environment for required tools and dependencies."""
    ui.logo_small()
    ui.header("Environment Check")
    ui.newline()

    all_ok = True

    # ─── Python ───────────────────────────────────────────
    py_version = sys.version.split()[0]
    py_major, py_minor = sys.version_info[:2]
    if py_major >= 3 and py_minor >= 9:
        ui.success(f"Python {py_version}")
    else:
        ui.error(f"Python {py_version} — requires 3.9+")
        all_ok = False

    # ─── pip ──────────────────────────────────────────────
    pip_path = shutil.which("pip") or shutil.which("pip3")
    if pip_path:
        ui.success(f"pip found: {pip_path}")
    else:
        ui.warning("pip not found")

    # ─── ENPAF Framework ─────────────────────────────────
    try:
        import enpaf
        ui.success(f"ENPAF Framework v{enpaf.__version__}")
    except ImportError:
        ui.error("ENPAF not installed")
        all_ok = False

    # ─── Flask ────────────────────────────────────────────
    try:
        import flask
        ui.success(f"Flask {flask.__version__}")
    except ImportError:
        ui.error("Flask not installed — run: pip install flask")
        all_ok = False

    # ─── Flask-SocketIO ───────────────────────────────────
    try:
        import flask_socketio
        try:
            version = flask_socketio.__version__
        except AttributeError:
            try:
                import importlib.metadata
                version = importlib.metadata.version('flask-socketio')
            except Exception:
                version = "installed"
        ui.success(f"Flask-SocketIO {version}")
    except ImportError:
        ui.warning("Flask-SocketIO not installed — run: pip install flask-socketio")

    # ─── Watchdog ─────────────────────────────────────────
    try:
        import watchdog
        ui.success(f"Watchdog (hot-reload support)")
    except ImportError:
        ui.warning("Watchdog not installed — hot-reload disabled. Install: pip install watchdog")

    # ─── Colorama ─────────────────────────────────────────
    try:
        import colorama
        ui.success("Colorama (terminal colors)")
    except ImportError:
        ui.warning("Colorama not installed — colors may not work on Windows")

    ui.newline()
    ui.header("Build Tools (for APK)")
    ui.newline()

    # ─── Java JDK ─────────────────────────────────────────
    from enpaf.cli.commands.build import (
        _java_major_version, _resolve_active_java, _find_compatible_jdk,
    )
    java_path = _resolve_active_java()
    if java_path:
        jmaj = _java_major_version(java_path)
        try:
            result = subprocess.run(
                [java_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            version_line = result.stderr.split("\n")[0] if result.stderr else "unknown"
        except Exception:
            version_line = java_path
        if jmaj is not None and 17 <= jmaj <= 21:
            ui.success(f"Java: {version_line}")
        else:
            ui.warning(f"Java (active): {version_line}")
            ui.dim(f"  JDK {jmaj} is incompatible with the APK build — JDK 17 needed (17–21 supported)")
            alt = _find_compatible_jdk()
            if alt:
                ui.success(f"Compatible JDK found: {alt}")
                ui.dim("  'paf build' will use it automatically")
            else:
                ui.dim("  Install JDK 17: https://adoptium.net/temurin/releases/?version=17")
                all_ok = False
    else:
        ui.warning("Java not found — required for APK build")
        ui.dim("  Install JDK 17: https://adoptium.net/")
        all_ok = False

    # ─── Gradle ───────────────────────────────────────────
    gradle_path = shutil.which("gradle")
    if gradle_path:
        ui.success(f"Gradle found: {gradle_path}")
    else:
        ui.info("Gradle not found — will be auto-downloaded during build")

    # ─── Android SDK ──────────────────────────────────────
    android_home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if android_home and os.path.isdir(android_home):
        ui.success(f"Android SDK: {android_home}")
    else:
        # Check common locations
        common_paths = []
        if platform.system() == "Windows":
            common_paths = [
                os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk"),
                os.path.expanduser(r"~\AppData\Local\Android\Sdk"),
                r"C:\Android\Sdk",
            ]
        else:
            common_paths = [
                os.path.expanduser("~/Android/Sdk"),
                os.path.expanduser("~/Library/Android/sdk"),
                "/usr/local/android-sdk",
            ]

        found = False
        for p in common_paths:
            if os.path.isdir(p):
                ui.success(f"Android SDK: {p}")
                ui.dim("  Tip: set ANDROID_HOME environment variable")
                found = True
                break

        if not found:
            ui.warning("Android SDK not found — required for APK build")
            ui.dim("  Install Android Studio or SDK Command-line Tools")
            ui.dim("  https://developer.android.com/studio")

    # ─── OS Info ──────────────────────────────────────────
    ui.newline()
    ui.header("System")
    ui.newline()
    ui.info(f"OS: {platform.system()} {platform.release()} ({platform.machine()})")
    ui.info(f"Python: {sys.executable}")
    ui.info(f"Working Dir: {os.getcwd()}")

    # ─── Summary ──────────────────────────────────────────
    ui.newline()
    if all_ok:
        ui.success("All checks passed! Your environment is ready. ✨")
    else:
        ui.warning("Some issues found. Fix them to use all features.")
    ui.newline()

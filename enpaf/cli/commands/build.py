"""
ENPAF CLI — Build Command
Builds the project into an Android APK.
Uses Gradle + Chaquopy for Windows-native builds.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import platform
import urllib.request
import zipfile
from typing import Optional

from enpaf.cli import ui


def _under_onedrive(path: str) -> bool:
    """Whether *path* lives inside a OneDrive-synced folder."""
    p = os.path.abspath(path).lower()
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        root = os.environ.get(var)
        if root and p.startswith(os.path.abspath(root).lower()):
            return True
    return (os.sep + "onedrive") in p


def _resolve_build_dir(project_dir: str) -> str:
    """Pick a build directory.

    Android/Gradle builds break inside cloud-synced folders: OneDrive keeps
    file handles / read-only placeholders, so Gradle's own delete steps fail
    ('Unable to delete directory ... a process has files open'). When the
    project is under OneDrive we relocate the build outside it (overridable
    with ENPAF_BUILD_DIR).
    """
    override = os.environ.get("ENPAF_BUILD_DIR")
    if override:
        digest = hashlib.sha1(os.path.abspath(project_dir).encode("utf-8")).hexdigest()[:8]
        name = os.path.basename(os.path.normpath(project_dir)) or "app"
        return os.path.join(override, f"{name}-{digest}")
    if _under_onedrive(project_dir):
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        digest = hashlib.sha1(os.path.abspath(project_dir).encode("utf-8")).hexdigest()[:8]
        name = os.path.basename(os.path.normpath(project_dir)) or "app"
        return os.path.join(base, "enpaf", "builds", f"{name}-{digest}")
    return os.path.join(project_dir, ".enpaf_build")


def cmd_build(args):
    """Build the project into an APK."""
    ui.logo_small()
    ui.header(f"Building {args.target.upper()}")
    ui.newline()

    # Check if we're in an ENPAF project
    config_path = os.path.join(os.getcwd(), "enpaf.json")
    if not os.path.isfile(config_path):
        ui.error("Not an ENPAF project (enpaf.json not found)")
        return

    # Load config
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    ui.info(f"Project: {config.get('name', 'Unknown')}")
    ui.info(f"Package: {config.get('package', 'Unknown')}")
    ui.info(f"Version: {config.get('version', '1.0.0')}")
    ui.newline()

    # Validate project
    if not _validate_project(config):
        return

    # Check build environment
    if not _check_build_env():
        return

    # Generate Android project
    ui.header("Generating Android Project")
    ui.newline()

    build_dir = _resolve_build_dir(os.getcwd())
    if not os.path.abspath(build_dir).startswith(os.path.abspath(os.getcwd())):
        ui.info("Building outside OneDrive to avoid file-lock errors:")
        ui.dim(f"  {build_dir}")
        ui.newline()

    if args.clean and os.path.exists(build_dir):
        spinner = ui.Spinner("Cleaning previous build...")
        spinner.start()
        from enpaf.builder.project_generator import safe_rmtree
        try:
            safe_rmtree(build_dir)
            spinner.stop("Clean complete", is_success=True)
        except OSError as e:
            spinner.stop(f"Clean incomplete: {e}", is_success=False)
            ui.dim("  Continuing — the generator will overwrite existing files")

    is_release = args.release or args.target == "aab"
    keystore_path = args.keystore if hasattr(args, "keystore") else None

    spinner = ui.Spinner("Generating Android project...")
    spinner.start()

    try:
        from enpaf.builder.apk_builder import APKBuilder
        builder = APKBuilder(os.getcwd(), config, build_dir)
        builder.generate_project(release=is_release, keystore_path=keystore_path)
        spinner.stop("Android project generated", is_success=True)
    except Exception as e:
        spinner.stop(f"Failed: {e}", is_success=False)
        return

    # Build APK with Gradle
    ui.newline()
    ui.header("Building APK")
    ui.newline()

    try:
        apk_path = builder.build_apk(
            release=is_release,
            keystore_path=keystore_path,
        )

        if apk_path and os.path.isfile(apk_path):
            # Copy to dist/
            dist_dir = os.path.join(os.getcwd(), "dist")
            os.makedirs(dist_dir, exist_ok=True)
            
            apk_name = f"{config.get('name', 'app').replace(' ', '_').lower()}-{config.get('version', '1.0.0')}.apk"
            final_path = os.path.join(dist_dir, apk_name)
            shutil.copy2(apk_path, final_path)
            
            size_mb = os.path.getsize(final_path) / (1024 * 1024)

            ui.newline()
            ui.success(f"APK built successfully! 🎉")
            ui.newline()
            ui.info(f"Output: {final_path}")
            ui.info(f"Size: {size_mb:.1f} MB")
            ui.newline()
            ui.header("Install on Device")
            ui.newline()
            ui.command_hint(f"adb install {final_path}", "Via USB")
            ui.dim("  Or transfer the APK file to your phone and install it")
            ui.newline()
        else:
            ui.error("Build completed but APK not found")
            ui.dim("Check the build output above for errors")

    except Exception as e:
        ui.error(f"Build failed: {e}")
        ui.newline()
        ui.info("Troubleshooting:")
        ui.command_hint("paf doctor", "Check your environment")
        ui.dim("  Make sure Java JDK and Android SDK are installed")


def _validate_project(config: dict) -> bool:
    """Validate the project structure before building."""
    errors = []

    # Check required config fields
    if not config.get("package"):
        errors.append("'package' is required in enpaf.json (e.g., 'com.example.myapp')")

    if not config.get("name"):
        errors.append("'name' is required in enpaf.json")

    # Check main.py
    if not os.path.isfile(os.path.join(os.getcwd(), "main.py")):
        errors.append("main.py not found")

    # Check app directory
    app_dir = os.path.join(os.getcwd(), "app")
    if not os.path.isdir(app_dir):
        errors.append("app/ directory not found")

    # Check index.html
    if not os.path.isfile(os.path.join(app_dir, "index.html")):
        errors.append("app/index.html not found")

    if errors:
        ui.error("Project validation failed:")
        for err in errors:
            ui.dim(f"  • {err}")
        ui.newline()
        return False

    ui.success("Project validation passed")
    return True


def _check_build_env() -> bool:
    """Check that build tools are available."""
    errors = []

    # Check Java. Gradle/AGP 8.2 require JDK 17 (17–21 works); newer JDKs (22+)
    # cannot even run Gradle 8.4. Resolve Java the way Gradle does (JAVA_HOME
    # first, then PATH) and, if it is incompatible, auto-pick a usable JDK from
    # common install locations and pin JAVA_HOME for the build.
    active_java = _resolve_active_java()
    if not active_java:
        errors.append("Java JDK not found. Install JDK 17: https://adoptium.net/")
    else:
        jmaj = _java_major_version(active_java)
        if jmaj is None or not (17 <= jmaj <= 21):
            jdk_home = _find_compatible_jdk()
            if jdk_home:
                os.environ["JAVA_HOME"] = jdk_home
                ui.info(f"Using compatible JDK for the build: {jdk_home}")
            else:
                shown = jmaj if jmaj is not None else "unknown"
                errors.append(
                    f"No compatible Java found (active JDK: {shown}).\n"
                    "         The Android build (Gradle 8.4 + AGP 8.2) needs JDK 17 — versions 17 to 21 work.\n"
                    "         1) Install JDK 17:  https://adoptium.net/temurin/releases/?version=17\n"
                    "         2) Point JAVA_HOME at it, e.g.:\n"
                    '            setx JAVA_HOME "C:\\Program Files\\Eclipse Adoptium\\jdk-17.0.x-hotspot"\n'
                    "         then open a NEW terminal and re-run 'paf build'."
                )

    # Android SDK is optional — we'll try to work without it
    android_home = (
        os.environ.get("ANDROID_HOME")
        or os.environ.get("ANDROID_SDK_ROOT")
    )
    
    if not android_home:
        # Check common locations
        common = _find_android_sdk()
        if common:
            os.environ["ANDROID_HOME"] = common
            ui.info(f"Android SDK found: {common}")
        else:
            errors.append(
                "Android SDK not found. Install Android Studio or set ANDROID_HOME.\n"
                "         Download: https://developer.android.com/studio"
            )

    if errors:
        ui.newline()
        ui.error("Build environment issues:")
        for err in errors:
            ui.dim(f"  • {err}")
        ui.newline()
        ui.info("Run 'paf doctor' for detailed diagnostics")
        ui.newline()
        return False

    return True


def _java_major_version(java_path: str) -> Optional[int]:
    """Return the major Java version (e.g. 17, 21, 25) or None if undetectable."""
    import re
    try:
        out = subprocess.run(
            [java_path, "-version"], capture_output=True, text=True, timeout=15
        )
    except Exception:
        return None
    text = (out.stderr or "") + (out.stdout or "")
    m = re.search(r'version "(\d+)(?:\.(\d+))?', text)
    if not m:
        return None
    major = int(m.group(1))
    if major == 1 and m.group(2):  # legacy "1.8.0" version scheme
        major = int(m.group(2))
    return major


def _java_exe(home: str) -> str:
    """Path to the java executable inside a JDK home for this platform."""
    exe = "java.exe" if platform.system() == "Windows" else "java"
    return os.path.join(home, "bin", exe)


def _resolve_active_java() -> Optional[str]:
    """Return the java executable Gradle would use: JAVA_HOME first, then PATH."""
    home = os.environ.get("JAVA_HOME")
    if home:
        exe = _java_exe(home)
        if os.path.isfile(exe):
            return exe
    return shutil.which("java")


def _find_compatible_jdk() -> Optional[str]:
    """Find a JDK 17–21 home among common install locations (incl. Android
    Studio's bundled JBR). Prefers JDK 17 (AGP 8.2's target)."""
    import glob

    roots, extra = [], []
    if platform.system() == "Windows":
        roots = [
            r"C:\Program Files\Java",
            r"C:\Program Files\Eclipse Adoptium",
            r"C:\Program Files\Microsoft",
            r"C:\Program Files\Zulu",
            r"C:\Program Files\Amazon Corretto",
        ]
        extra = [
            r"C:\Program Files\Android\Android Studio\jbr",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Android Studio\jbr"),
        ]
    elif platform.system() == "Darwin":
        roots = ["/Library/Java/JavaVirtualMachines"]
        extra = ["/Applications/Android Studio.app/Contents/jbr/Contents/Home"]
    else:
        roots = ["/usr/lib/jvm", "/usr/java"]
        extra = [os.path.expanduser("~/android-studio/jbr")]

    candidates = list(extra)
    for root in roots:
        for entry in glob.glob(os.path.join(root, "*")):
            candidates.append(entry)
            candidates.append(os.path.join(entry, "Contents", "Home"))  # macOS layout

    found = []
    for home in candidates:
        if os.path.isfile(_java_exe(home)):
            major = _java_major_version(_java_exe(home))
            if major is not None and 17 <= major <= 21:
                found.append((major, home))
    if not found:
        return None
    found.sort(key=lambda t: (t[0] != 17, t[0]))  # JDK 17 first, then lowest
    return found[0][1]


def _find_android_sdk() -> Optional[str]:
    """Try to find Android SDK in common locations."""
    candidates = []
    
    if platform.system() == "Windows":
        candidates = [
            os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk"),
            os.path.expanduser(r"~\AppData\Local\Android\Sdk"),
            r"C:\Android\Sdk",
        ]
    elif platform.system() == "Darwin":
        candidates = [
            os.path.expanduser("~/Library/Android/sdk"),
        ]
    else:
        candidates = [
            os.path.expanduser("~/Android/Sdk"),
            "/usr/local/android-sdk",
        ]
    
    for path in candidates:
        if os.path.isdir(path):
            return path
    
    return None

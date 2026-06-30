"""
ENPAF CLI — Main Entry Point
The 'paf' command-line tool for managing ENPAF projects.
"""

import argparse
import os
import sys

from enpaf.cli import ui


def main():
    """Main CLI entry point — called as the 'paf' command."""
    parser = argparse.ArgumentParser(
        prog="paf",
        description="PAF — ENPAF Framework CLI. Build Android apps with Python + Web.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  paf create myapp          Create a new ENPAF project
  paf run                   Start development server
  paf run --port 3000       Start on custom port
  paf serve                 Serve built APK over Wi-Fi
  paf build apk             Build Android APK
  paf doctor                Check your environment
  paf info                  Show project info
  paf update                Update PAF to the latest version
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ─── create ───────────────────────────────────────────
    create_parser = subparsers.add_parser("create", help="Create a new ENPAF project")
    create_parser.add_argument("name", help="Project name")
    create_parser.add_argument("--package", "-p", help="Android package name (e.g., com.example.myapp)")
    create_parser.add_argument("--template", "-t", default="default", help="Project template")

    # ─── run ──────────────────────────────────────────────
    run_parser = subparsers.add_parser("run", help="Start development server")
    run_parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    run_parser.add_argument("--port", type=int, default=8080, help="Server port (default: 8080)")
    run_parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    run_parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    # ─── serve ────────────────────────────────────────────
    serve_parser = subparsers.add_parser("serve", help="Serve built APK over Wi-Fi for debugging")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to serve on (default: 8000)")

    # ─── build ────────────────────────────────────────────
    build_parser = subparsers.add_parser("build", help="Build the project")
    build_parser.add_argument("target", choices=["apk", "debug-apk", "aab"], help="Build target")
    build_parser.add_argument("--release", action="store_true", help="Build release version")
    build_parser.add_argument("--keystore", help="Path to keystore for signing")
    build_parser.add_argument("--clean", action="store_true", help="Clean build")

    # ─── doctor ───────────────────────────────────────────
    subparsers.add_parser("doctor", help="Check environment and dependencies")

    # ─── info ─────────────────────────────────────────────
    subparsers.add_parser("info", help="Show current project info")

    # ─── update ───────────────────────────────────────────
    update_parser = subparsers.add_parser("update", help="Update PAF to the latest version")
    update_parser.add_argument("--pre", action="store_true", help="Include pre-release versions")

    # Parse arguments
    args = parser.parse_args()

    if args.command is None:
        ui.logo()
        ui.header("Available Commands")
        ui.newline()
        ui.table(
            ["Command", "Description"],
            [
                ["create <name>", "Create a new ENPAF project"],
                ["run", "Start development server"],
                ["serve", "Serve built APK over Wi-Fi"],
                ["build apk", "Build Android APK"],
                ["doctor", "Check your environment"],
                ["info", "Show project info"],
                ["update", "Update PAF to the latest version"],
            ],
        )
        ui.newline()
        ui.header("Quick Start")
        ui.newline()
        ui.command_hint("paf create myapp", "Create a new project")
        ui.command_hint("cd myapp", "Enter project directory")
        ui.command_hint("paf run", "Start dev server")
        ui.command_hint("paf build apk", "Build APK")
        ui.newline()
        return

    # Dispatch to command handlers
    if args.command == "create":
        from enpaf.cli.commands.create import cmd_create
        cmd_create(args)
    elif args.command == "run":
        from enpaf.cli.commands.run import cmd_run
        cmd_run(args)
    elif args.command == "serve":
        from enpaf.cli.commands.serve import cmd_serve
        cmd_serve(args)
    elif args.command == "build":
        from enpaf.cli.commands.build import cmd_build
        cmd_build(args)
    elif args.command == "doctor":
        from enpaf.cli.commands.doctor import cmd_doctor
        cmd_doctor(args)
    elif args.command == "info":
        cmd_info(args)
    elif args.command == "update":
        cmd_update(args)


def cmd_info(args):
    """Show project info."""
    import json

    ui.logo_small()

    config_path = os.path.join(os.getcwd(), "enpaf.json")
    if not os.path.isfile(config_path):
        ui.error("Not an ENPAF project (enpaf.json not found)")
        ui.dim(f"Current directory: {os.getcwd()}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    ui.header("Project Info")
    ui.newline()
    ui.table(
        ["Property", "Value"],
        [
            ["Name", config.get("name", "N/A")],
            ["Package", config.get("package", "N/A")],
            ["Version", config.get("version", "N/A")],
            ["Description", config.get("description", "N/A")],
            ["Author", config.get("author", "N/A")],
            ["Min SDK", str(config.get("min_sdk", "N/A"))],
            ["Target SDK", str(config.get("target_sdk", "N/A"))],
            ["Orientation", config.get("orientation", "N/A")],
        ],
    )

    perms = config.get("permissions", [])
    if perms:
        ui.newline()
        ui.info(f"Permissions: {', '.join(perms)}")

    py_reqs = config.get("python_requirements", [])
    if py_reqs:
        ui.info(f"Python deps: {', '.join(py_reqs)}")

    ui.newline()


def cmd_update(args):
    """Update the installed PAF (enpaf) package to the latest release from PyPI."""
    import json
    import subprocess
    import urllib.request

    from enpaf import __version__

    ui.logo_small()
    ui.header("Update PAF")
    ui.newline()
    ui.info(f"Installed version: {__version__}")

    latest = None
    try:
        with urllib.request.urlopen("https://pypi.org/pypi/enpaf/json", timeout=10) as r:
            latest = json.load(r)["info"]["version"]
        ui.info(f"Latest on PyPI:    {latest}")
    except Exception:
        ui.dim("  (could not reach PyPI to check the latest version)")

    if latest and latest == __version__ and not args.pre:
        ui.newline()
        ui.success("Already up to date 🎉")
        return

    ui.newline()
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "enpaf"]
    if args.pre:
        cmd.append("--pre")
    ui.info("Running: " + " ".join(cmd))
    ui.newline()
    try:
        rc = subprocess.call(cmd)
    except Exception as e:
        ui.error(f"Update failed: {e}")
        ui.dim("  Try manually: python -m pip install --upgrade enpaf")
        return

    ui.newline()
    if rc == 0:
        ui.success("PAF updated! Run 'paf' to see the new version.")
    else:
        ui.error("Update failed — see the pip output above.")
        ui.dim("  Try manually: python -m pip install --upgrade enpaf")


if __name__ == "__main__":
    main()

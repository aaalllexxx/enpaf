"""
ENPAF CLI — Run Command
Starts the development server.
"""

import os
import sys
import json

from enpaf.cli import ui


def cmd_run(args):
    """Start the development server."""
    ui.logo_small()

    # Check if we're in an ENPAF project
    config_path = os.path.join(os.getcwd(), "enpaf.json")
    if not os.path.isfile(config_path):
        ui.error("Not an ENPAF project!")
        ui.dim("Run this command from an ENPAF project directory (containing enpaf.json)")
        ui.newline()
        ui.info("To create a new project:")
        ui.command_hint("paf create myapp")
        return

    # Check for main.py
    main_py = os.path.join(os.getcwd(), "main.py")
    if not os.path.isfile(main_py):
        ui.error("main.py not found!")
        ui.dim("Every ENPAF project needs a main.py file")
        return

    # Load config
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    app_name = config.get("name", "ENPAF App")
    host = args.host
    port = args.port
    open_browser = not args.no_browser
    debug = args.debug

    # Add project dir to Python path so main.py can be imported
    project_dir = os.getcwd()
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

    # Run the app
    try:
        # Import and execute main.py
        # We need to exec it so that the app.run() call at the bottom works
        # But we want to intercept the run() call to use our CLI args
        
        import importlib.util
        spec = importlib.util.spec_from_file_location("__main__", main_py)
        module = importlib.util.module_from_spec(spec)
        
        # Patch sys.argv so the module thinks it's the main script
        old_argv = sys.argv
        sys.argv = [main_py]

        # Monkey-patch EnpafApp.run to use our args
        from enpaf.core.app import EnpafApp
        original_run = EnpafApp.run

        def patched_run(self, **kwargs):
            original_run(
                self,
                host=host,
                port=port,
                debug=debug,
                open_browser=open_browser,
            )

        EnpafApp.run = patched_run

        try:
            spec.loader.exec_module(module)
        finally:
            EnpafApp.run = original_run
            sys.argv = old_argv

    except KeyboardInterrupt:
        ui.newline()
        ui.info("Server stopped.")
    except Exception as e:
        ui.error(f"Failed to start server: {e}")
        if debug:
            import traceback
            traceback.print_exc()

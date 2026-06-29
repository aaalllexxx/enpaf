"""
ENPAF CLI — Create Command
Creates a new ENPAF project from template.
"""

import json
import os
import shutil
import re

from enpaf.cli import ui


def cmd_create(args):
    """Create a new ENPAF project."""
    ui.logo_small()
    ui.header("Creating New Project")
    ui.newline()

    project_name = args.name

    # Validate project name
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', project_name):
        ui.error("Invalid project name. Use letters, numbers, hyphens, and underscores.")
        ui.dim("Example: my-app, myApp, my_cool_app")
        return

    # Project directory
    project_dir = os.path.join(os.getcwd(), project_name)

    if os.path.exists(project_dir):
        ui.error(f"Directory '{project_name}' already exists!")
        return

    # Determine package name
    package = args.package
    if not package:
        safe_name = re.sub(r'[^a-zA-Z0-9]', '', project_name).lower()
        package = f"com.enpaf.{safe_name}"

    ui.info(f"Project: {ui.C.BOLD}{project_name}{ui.C.RESET}")
    ui.info(f"Package: {package}")
    ui.info(f"Directory: {project_dir}")
    ui.newline()

    # Create project from template
    spinner = ui.Spinner("Creating project structure...")
    spinner.start()

    try:
        _create_project(project_dir, project_name, package)
        spinner.stop(f"Project '{project_name}' created!", is_success=True)
    except Exception as e:
        spinner.stop(f"Failed to create project: {e}", is_success=False)
        return

    ui.newline()
    ui.header("Next Steps")
    ui.newline()
    ui.step(1, "Enter the project directory:")
    ui.command_hint(f"cd {project_name}")
    ui.newline()
    ui.step(2, "Start the development server:")
    ui.command_hint("paf run")
    ui.newline()
    ui.step(3, "Open in your browser:")
    ui.dim("http://127.0.0.1:8080")
    ui.newline()
    ui.step(4, "When ready, build APK:")
    ui.command_hint("paf build apk")
    ui.newline()
    ui.success("Happy coding! 🎉")
    ui.newline()


def _create_project(project_dir: str, name: str, package: str):
    """Create the project directory structure from template."""

    # Find template directory (from enpaf/cli/commands/create.py -> enpaf/template/)
    enpaf_pkg_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    template_dir = os.path.join(enpaf_pkg_dir, "template")

    if os.path.isdir(template_dir):
        # Copy template
        shutil.copytree(template_dir, project_dir)
    else:
        # Create from scratch if template not found
        _create_project_manual(project_dir)

    # Update enpaf.json with project-specific values
    config_path = os.path.join(project_dir, "enpaf.json")
    if os.path.isfile(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        config["name"] = name
        config["package"] = package

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

    # Update main.py
    main_path = os.path.join(project_dir, "main.py")
    if os.path.isfile(main_path):
        with open(main_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("{{PROJECT_NAME}}", name)
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(content)


def _create_project_manual(project_dir: str):
    """Create project structure manually (fallback if template is missing)."""
    os.makedirs(project_dir, exist_ok=True)
    os.makedirs(os.path.join(project_dir, "app", "css"), exist_ok=True)
    os.makedirs(os.path.join(project_dir, "app", "js"), exist_ok=True)
    os.makedirs(os.path.join(project_dir, "app", "pages"), exist_ok=True)
    os.makedirs(os.path.join(project_dir, "app", "img"), exist_ok=True)
    os.makedirs(os.path.join(project_dir, "data"), exist_ok=True)

    # Create minimal files
    _write(os.path.join(project_dir, "enpaf.json"), json.dumps({
        "name": "My App",
        "package": "com.enpaf.myapp",
        "version": "1.0.0",
        "description": "My ENPAF Application",
        "author": "Developer",
        "orientation": "portrait",
        "permissions": ["INTERNET"],
        "python_requirements": [],
        "min_sdk": 24,
        "target_sdk": 34,
        "theme": {
            "primary_color": "#6C5CE7",
            "status_bar_color": "#5A4BD1"
        }
    }, indent=4, ensure_ascii=False))

    _write(os.path.join(project_dir, "main.py"), '''"""My ENPAF App — main entry point."""
from enpaf import EnpafApp

app = EnpafApp(__name__)

@app.route("/")
def index():
    return app.render("index.html", title="My App")

@app.bridge_handler("hello")
def hello(params):
    name = params.get("name", "World")
    return {"message": f"Hello, {name}!"}

@app.on("app_start")
def on_start():
    print("App started!")

if __name__ == "__main__":
    app.run()
''')

    _write(os.path.join(project_dir, "app", "index.html"), '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My App</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div id="app">
        <h1>Welcome to ENPAF!</h1>
        <p>Edit app/index.html to get started.</p>
    </div>
    <script src="js/app.js"></script>
</body>
</html>
''')

    _write(os.path.join(project_dir, "app", "css", "style.css"), "/* Add your styles */\n")
    _write(os.path.join(project_dir, "app", "js", "app.js"), "// Add your code\n")


def _write(path: str, content: str):
    """Write content to a file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

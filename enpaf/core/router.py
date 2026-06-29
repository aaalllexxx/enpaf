"""
ENPAF Core — Router
Page routing system with template rendering support.
"""

from __future__ import annotations  # keep type hints lazy (jinja2 is optional)

import os
from typing import Any, Callable, Dict, List, Optional, Tuple

# NOTE: jinja2 is imported lazily inside _get_jinja_env(). On Android (Chaquopy)
# it is not bundled unless the app needs it, and templates are not rendered there
# (the WebView loads static assets directly). A top-level import would crash the
# app on launch with ModuleNotFoundError.


class Route:
    """A single route definition."""

    def __init__(self, path: str, handler: Callable, methods: List[str] = None):
        self.path = path
        self.handler = handler
        self.methods = methods or ["GET"]

    def matches(self, request_path: str) -> bool:
        """Check if the request path matches this route."""
        # Simple path matching (no regex for now)
        return self.path == request_path


class Router:
    """
    Page router with template rendering.
    
    Usage:
        router = Router("app/")
        
        @router.route("/")
        def index():
            return router.render("index.html", title="Home")
            
        @router.route("/about")
        def about():
            return router.render("pages/about.html")
    """

    def __init__(self, template_dir: str = "app"):
        self._routes: List[Route] = []
        self._middleware: List[Callable] = []
        self._template_dir = template_dir
        self._jinja_env: Optional[Environment] = None
        self._error_handlers: Dict[int, Callable] = {}

    def _get_jinja_env(self) -> "Environment":
        """Lazy-initialize Jinja2 environment (imports jinja2 on first use)."""
        if self._jinja_env is None:
            from jinja2 import Environment, FileSystemLoader, select_autoescape
            self._jinja_env = Environment(
                loader=FileSystemLoader(self._template_dir),
                autoescape=select_autoescape(["html", "xml"]),
                auto_reload=True,
            )
        return self._jinja_env

    def route(self, path: str, methods: List[str] = None) -> Callable:
        """
        Decorator to register a route handler.
        
            @router.route("/")
            def index():
                return router.render("index.html")
        """
        def decorator(handler: Callable) -> Callable:
            self._routes.append(Route(path, handler, methods))
            return handler
        return decorator

    def middleware(self, func: Callable) -> Callable:
        """Register a middleware function."""
        self._middleware.append(func)
        return func

    def error_handler(self, status_code: int) -> Callable:
        """Register an error handler for a specific status code."""
        def decorator(handler: Callable) -> Callable:
            self._error_handlers[status_code] = handler
            return handler
        return decorator

    def render(self, template_name: str, **context) -> str:
        """
        Render an HTML template with context data.
        Automatically injects the ENPAF bridge script.
        """
        env = self._get_jinja_env()
        template = env.get_template(template_name)
        
        # Add framework context
        context.setdefault("enpaf_version", "1.0.0")
        
        rendered = template.render(**context)
        
        # Inject bridge script if not already present
        if "enpaf.js" not in rendered and "</head>" in rendered:
            bridge_inject = '<script src="/enpaf-bridge/enpaf.js"></script>\n</head>'
            rendered = rendered.replace("</head>", bridge_inject)
        
        return rendered

    def render_string(self, template_string: str, **context) -> str:
        """Render a template from a string."""
        env = self._get_jinja_env()
        template = env.from_string(template_string)
        return template.render(**context)

    def resolve(self, path: str, method: str = "GET") -> Optional[Tuple[Route, Callable]]:
        """Find the route handler for a given path."""
        for route in self._routes:
            if route.matches(path) and method.upper() in route.methods:
                return route, route.handler
        return None

    def get_routes(self) -> List[Dict[str, Any]]:
        """Get all registered routes as dictionaries."""
        return [
            {"path": r.path, "methods": r.methods, "handler": r.handler.__name__}
            for r in self._routes
        ]

    def set_template_dir(self, template_dir: str):
        """Change the template directory."""
        self._template_dir = template_dir
        self._jinja_env = None  # Reset to force reload

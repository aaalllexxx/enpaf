"""Tests for enpaf.core.router — routing + Jinja2 template rendering."""


from enpaf.core.router import Route, Router


def _write_template(tmp_path, name, content):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_route_matches_exact_path():
    r = Route("/about", lambda: None)
    assert r.matches("/about") is True
    assert r.matches("/other") is False


def test_route_default_method_is_get():
    r = Route("/", lambda: None)
    assert r.methods == ["GET"]


def test_register_and_resolve_route():
    router = Router("app")

    @router.route("/")
    def index():
        return "home"

    resolved = router.resolve("/")
    assert resolved is not None
    _, handler = resolved
    assert handler() == "home"


def test_resolve_respects_method():
    router = Router("app")
    router.route("/submit", methods=["POST"])(lambda: "ok")
    assert router.resolve("/submit", "GET") is None
    assert router.resolve("/submit", "POST") is not None


def test_get_routes_lists_metadata():
    router = Router("app")

    @router.route("/x", methods=["GET", "POST"])
    def handler():
        return None

    routes = router.get_routes()
    assert routes == [{"path": "/x", "methods": ["GET", "POST"], "handler": "handler"}]


def test_render_interpolates_context(tmp_path):
    _write_template(tmp_path, "page.html", "<h1>{{ title }}</h1>")
    router = Router(str(tmp_path))
    out = router.render("page.html", title="Welcome")
    assert "<h1>Welcome</h1>" in out


def test_render_injects_bridge_script_into_head(tmp_path):
    _write_template(
        tmp_path, "page.html", "<html><head><title>x</title></head><body></body></html>"
    )
    router = Router(str(tmp_path))
    out = router.render("page.html")
    assert "/enpaf-bridge/enpaf.js" in out
    assert out.count("enpaf.js") == 1


def test_render_does_not_double_inject_bridge(tmp_path):
    _write_template(
        tmp_path,
        "page.html",
        '<html><head><script src="enpaf.js"></script></head><body></body></html>',
    )
    router = Router(str(tmp_path))
    out = router.render("page.html")
    # Already references enpaf.js -> must not inject a second tag.
    assert out.count("enpaf.js") == 1


def test_render_string(tmp_path):
    router = Router(str(tmp_path))
    assert router.render_string("Hello {{ name }}", name="Sam") == "Hello Sam"


def test_render_autoescapes_html(tmp_path):
    _write_template(tmp_path, "p.html", "<div>{{ value }}</div>")
    router = Router(str(tmp_path))
    out = router.render("p.html", value="<script>alert(1)</script>")
    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;" in out


def test_set_template_dir_resets_env(tmp_path):
    d1 = tmp_path / "a"
    d2 = tmp_path / "b"
    _write_template(d1, "t.html", "A:{{ v }}")
    _write_template(d2, "t.html", "B:{{ v }}")
    router = Router(str(d1))
    assert router.render("t.html", v=1) == "A:1"
    router.set_template_dir(str(d2))
    assert router.render("t.html", v=2) == "B:2"


def test_error_handler_registration():
    router = Router("app")

    @router.error_handler(404)
    def not_found():
        return "missing"

    assert router._error_handlers[404]() == "missing"

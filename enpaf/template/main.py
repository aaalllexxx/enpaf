"""
{{PROJECT_NAME}} — ENPAF Application
"""

from enpaf import EnpafApp

app = EnpafApp(__name__)


# ─── Routes ───────────────────────────────────────────────────

@app.route("/")
def index():
    """Main page."""
    return app.render("index.html", title=app.name)


# ─── Bridge Handlers (callable from JavaScript) ──────────────

@app.bridge_handler("hello")
def hello(params):
    """
    Greet a user.
    JS: const result = await enpaf.call("hello", { name: "Alex" });
    """
    name = params.get("name", "World")
    return {"message": f"Привет, {name}! 👋", "from": "Python"}


@app.bridge_handler("get_time")
def get_time(params):
    """Get the current server/device time."""
    from datetime import datetime
    now = datetime.now()
    return {
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%d.%m.%Y"),
        "timestamp": now.timestamp(),
    }


@app.bridge_handler("save_note")
def save_note(params):
    """Save a note to storage."""
    text = params.get("text", "")
    if not text:
        return {"success": False, "error": "Empty note"}
    
    notes = app.storage.collection("notes")
    note_id = notes.add({"text": text})
    return {"success": True, "id": note_id}


@app.bridge_handler("get_notes")
def get_notes(params):
    """Get all saved notes."""
    notes = app.storage.collection("notes")
    return {"notes": notes.all()}


@app.bridge_handler("delete_note")
def delete_note(params):
    """Delete a note by ID."""
    note_id = params.get("id")
    if note_id:
        app.storage.collection("notes").delete(int(note_id))
    return {"success": True}


@app.bridge_handler("calculate")
def calculate(params):
    """Example: server-side calculation."""
    a = params.get("a", 0)
    b = params.get("b", 0)
    op = params.get("op", "+")
    
    operations = {
        "+": lambda x, y: x + y,
        "-": lambda x, y: x - y,
        "*": lambda x, y: x * y,
        "/": lambda x, y: x / y if y != 0 else "∞",
    }
    
    func = operations.get(op, operations["+"])
    result = func(float(a), float(b))
    return {"result": result, "expression": f"{a} {op} {b} = {result}"}


# ─── Lifecycle Events ────────────────────────────────────────

@app.on("app_start")
def on_start():
    print("🚀 App started!")


@app.on("app_stop")
def on_stop():
    print("🛑 App stopped")


# ─── Run ──────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run()

"""
testapp — ENPAF Application
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
    app.api.vibrate(200)
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


# ─── Sensors & NFC (read straight from Python via app.api) ───

@app.bridge_handler("device_report")
def device_report(params):
    """Read a batch of sensors from Python and return them to the UI.

    JS: const r = await enpaf.call("device_report", {});
    (The UI also calls enpaf.sensors.* / enpaf.nfc.* directly — both work.)
    """
    return {
        "accelerometer": app.api.read_sensor("accelerometer"),
        "gyroscope": app.api.read_sensor("gyroscope"),
        "light": app.api.read_sensor("light"),
        "location": app.api.get_location(),
        "battery": app.api.get_battery(),
        "nfc": app.api.get_nfc(),
    }


# ─── Driving the modules from Python (Wi-Fi / Bluetooth / …) ──
# Every capability is a Python object on `app` (app.wifi, app.bluetooth,
# app.location, app.sensors, app.nfc, app.battery, …) — so you can start them
# straight from Python, not only from JS.

@app.bridge_handler("py_scan_wifi")
def py_scan_wifi(params):
    """Scan Wi-Fi from Python and return the networks (blocks until done)."""
    return app.wifi.scan_sync(timeout=10)          # -> {"networks": [...]}


@app.bridge_handler("py_scan_bluetooth")
def py_scan_bluetooth(params):
    """Discover Bluetooth devices from Python and return them."""
    return app.bluetooth.discover_sync(timeout=12)  # -> {"devices": [...]}


@app.bridge_handler("py_wifi_connect")
def py_wifi_connect(params):
    """Connect to Wi-Fi straight from Python."""
    return app.wifi.connect(ssid=params.get("ssid", ""), password=params.get("password", ""))


@app.bridge_handler("py_bt_send")
def py_bt_send(params):
    """Send a Bluetooth message from Python."""
    return app.bluetooth.send(text=params.get("text", ""))


# Python can also react to module events (same events JS receives):
@app.on("wifi_scan_result")
def _on_wifi(net):
    print(f"📡 Wi-Fi: {net.get('ssid')} ({net.get('rssi')} dBm)")

@app.on("bluetooth_device_found")
def _on_bt(dev):
    print(f"📶 BT: {dev.get('name')} {dev.get('address')}")


@app.on("nfc_tag")
def on_nfc_tag(data):
    """Fired when an NFC tag is tapped (Android)."""
    print(f"🏷️ NFC tag: {data.get('id')}")


@app.on("permission_result")
def on_permission_result(data):
    print(f"🔐 granted={data.get('granted')} denied={data.get('denied')}")


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

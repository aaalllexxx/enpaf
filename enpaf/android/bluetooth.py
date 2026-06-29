"""
ENPAF Android — Bluetooth (Classic / SPP)
A small, friendly Bluetooth module: discover nearby devices, connect, and
exchange text messages between two phones (line-based over RFCOMM/SPP).

Design notes:
  * No third-party / android imports at module top level — everything Android is
    imported lazily inside the methods (this module is bundled into the APK).
  * On desktop (dev) every method returns a stub and the discovery/chat is
    simulated, so the UI can be built and tested without a phone.
  * Events are pushed to JS via the app bridge:
      bluetooth_device_found      {name, address, rssi}
      bluetooth_discovery_finished{}
      bluetooth_connected         {name, address, role}
      bluetooth_data              {text}
      bluetooth_disconnected      {}
      bluetooth_error             {error, where}
"""

import logging
import threading
import time

logger = logging.getLogger("enpaf.bluetooth")

# Standard Serial Port Profile UUID — both ends must use the same one.
SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"


class BluetoothManager:
    """Simple Bluetooth Classic helper (one connection at a time)."""

    _ALLOWED = {
        "status", "enable", "paired", "discover", "stop_discovery",
        "connect", "listen", "send", "disconnect",
    }

    def __init__(self, app=None):
        self._app = app
        self._is_android = bool(getattr(app, "_is_android", False))
        self._socket = None     # connected BluetoothSocket
        self._server = None     # BluetoothServerSocket while listening
        self._receiver = None   # discovery BroadcastReceiver
        self._reader = None     # reader thread

    # ── dispatch (called by the __enpaf_bt bridge handler) ──
    def invoke(self, method, args=None):
        if method not in self._ALLOWED:
            raise ValueError(f"unknown bluetooth method: {method!r}")
        return getattr(self, method)(**(args or {}))

    # ── helpers ──
    def _fire(self, event, data=None):
        """Push an event to JS (and Python handlers)."""
        if self._app is None:
            return
        try:
            self._app.events.emit(event, data)
            self._app.bridge.emit_to_js(event, data)
        except Exception as e:
            logger.error(f"bluetooth emit error ({event}): {e}")

    def _ctx(self):
        from com.chaquo.python import Python
        return Python.getPlatform().getApplication()

    def _adapter(self):
        from android.bluetooth import BluetoothAdapter
        return BluetoothAdapter.getDefaultAdapter()

    # ── state ──
    def status(self, **_):
        if not self._is_android:
            return {"available": True, "dev": True, "enabled": True,
                    "name": "Dev-Bluetooth", "address": "00:11:22:33:44:55",
                    "note": "bluetooth runs on-device; desktop stub"}
        try:
            a = self._adapter()
            if a is None:
                return {"available": False, "note": "no bluetooth adapter"}
            info = {"available": True, "enabled": bool(a.isEnabled())}
            try:
                info["name"] = str(a.getName())
            except Exception:
                pass
            info["connected"] = self._socket is not None
            return info
        except Exception as e:
            return {"available": False, "error": str(e)}

    def enable(self, **_):
        """Ask the user to turn Bluetooth on (system dialog)."""
        if not self._is_android:
            return {"ok": True, "dev": True}
        try:
            from android.bluetooth import BluetoothAdapter
            from android.content import Intent
            activity = getattr(self._app.api, "_activity", None)
            intent = Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE)
            if activity is not None:
                activity.startActivity(intent)
            else:
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                self._ctx().startActivity(intent)
            return {"ok": True, "requested": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def paired(self, **_):
        """List bonded (already-paired) devices."""
        if not self._is_android:
            return {"dev": True, "devices": [
                {"name": "Dev Phone", "address": "AA:BB:CC:DD:EE:01"},
                {"name": "Dev Speaker", "address": "AA:BB:CC:DD:EE:02"},
            ]}
        try:
            a = self._adapter()
            out = [{"name": str(d.getName()), "address": str(d.getAddress())}
                   for d in a.getBondedDevices()]
            return {"devices": out}
        except Exception as e:
            return {"devices": [], "error": str(e)}

    # ── discovery ──
    def discover(self, **_):
        """Start scanning for nearby devices. Results arrive as
        `bluetooth_device_found` events, then `bluetooth_discovery_finished`."""
        if not self._is_android:
            def sim():
                time.sleep(0.6)
                self._fire("bluetooth_device_found",
                           {"name": "Dev Phone", "address": "AA:BB:CC:DD:EE:01", "rssi": -44})
                time.sleep(0.7)
                self._fire("bluetooth_device_found",
                           {"name": "Dev Watch", "address": "AA:BB:CC:DD:EE:03", "rssi": -69})
                time.sleep(0.5)
                self._fire("bluetooth_discovery_finished", {})
            threading.Thread(target=sim, daemon=True).start()
            return {"ok": True, "dev": True}
        try:
            from android.bluetooth import BluetoothAdapter, BluetoothDevice
            from java import jarray
            from java.lang import String

            a = self._adapter()
            if a is None:
                return {"ok": False, "note": "no bluetooth adapter"}
            if a.isDiscovering():
                a.cancelDiscovery()
            self._unregister_receiver()
            mgr = self

            activity = getattr(self._app.api, "_activity", None)
            if activity is None:
                return {"ok": False, "error": "no Activity"}

            actions = jarray(String)([
                str(BluetoothDevice.ACTION_FOUND),
                str(BluetoothAdapter.ACTION_DISCOVERY_FINISHED),
            ])
            self._receiver = activity.registerEnpafReceiver("bt", actions)

            action_found = str(BluetoothDevice.ACTION_FOUND)
            action_finished = str(BluetoothAdapter.ACTION_DISCOVERY_FINISHED)

            def on_broadcast(payload):
                intent = payload.get("intent")
                if not intent:
                    return
                try:
                    action = str(intent.getAction())
                except Exception:
                    return
                logger.debug(f"bt broadcast: {action}")
                if action == action_found:
                    try:
                        dev = intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE)
                        rssi = intent.getShortExtra(BluetoothDevice.EXTRA_RSSI, -32768)
                        name = dev.getName()
                        mgr._fire("bluetooth_device_found", {
                            "name": str(name) if name else "",
                            "address": str(dev.getAddress()),
                            "rssi": int(rssi),
                        })
                    except Exception as e:
                        logger.error(f"bt device parse error: {e}")
                elif action == action_finished:
                    mgr._fire("bluetooth_discovery_finished", {})

            self._on_broadcast = on_broadcast
            self._app.events.on("broadcast:bt", on_broadcast)

            a.startDiscovery()
            return {"ok": True}
        except Exception as e:
            logger.error(f"discover error: {e}")
            return {"ok": False, "error": str(e)}

    def discover_sync(self, timeout=12.0, include_paired=True):
        """Python helper: discover and RETURN the devices (blocks up to timeout).

        Example (main.py):
            devices = app.bluetooth.discover_sync()["devices"]
        """
        import threading
        found, done = {}, threading.Event()
        if include_paired:
            for d in self.paired().get("devices", []):
                found[d.get("address")] = d

        def on_found(d):
            if d and d.get("address"):
                found[d["address"]] = d

        def on_done(_d=None):
            done.set()

        ev = self._app.events
        ev.on("bluetooth_device_found", on_found)
        ev.on("bluetooth_discovery_finished", on_done)
        try:
            self.discover()
            done.wait(max(0.5, float(timeout)))
        finally:
            ev.off("bluetooth_device_found", on_found)
            ev.off("bluetooth_discovery_finished", on_done)
        return {"devices": list(found.values())}

    def stop_discovery(self, **_):
        if not self._is_android:
            return {"ok": True, "dev": True}
        try:
            a = self._adapter()
            if a and a.isDiscovering():
                a.cancelDiscovery()
            self._unregister_receiver()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _unregister_receiver(self):
        if self._receiver is not None:
            try:
                activity = getattr(self._app.api, "_activity", None)
                if activity is not None:
                    activity.unregisterEnpafReceiver(self._receiver)
                else:
                    self._ctx().unregisterReceiver(self._receiver)
            except Exception:
                pass
            self._receiver = None
        if hasattr(self, "_on_broadcast"):
            try:
                self._app.events.off("broadcast:bt", self._on_broadcast)
            except Exception:
                pass

    # ── connect (client) ──
    def connect(self, address=None, **_):
        """Connect to a device by MAC address (as the client end)."""
        if not self._is_android:
            self._fire("bluetooth_connected",
                       {"address": address, "name": "Dev Device", "role": "client", "dev": True})
            return {"ok": True, "dev": True}
        try:
            from java.util import UUID
            a = self._adapter()
            if a.isDiscovering():
                a.cancelDiscovery()
            device = a.getRemoteDevice(address)

            def run():
                try:
                    sock = device.createRfcommSocketToServiceRecord(UUID.fromString(SPP_UUID))
                    sock.connect()
                    self._socket = sock
                    self._fire("bluetooth_connected", {
                        "address": str(address), "name": str(device.getName()), "role": "client"})
                    self._start_reader(sock)
                except Exception as e:
                    self._fire("bluetooth_error", {"error": str(e), "where": "connect"})

            threading.Thread(target=run, daemon=True).start()
            return {"ok": True, "connecting": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── listen (server) ──
    def listen(self, name="ENPAF", **_):
        """Wait for an incoming connection (the other phone calls connect())."""
        if not self._is_android:
            return {"ok": True, "dev": True, "listening": True}
        try:
            from java.util import UUID
            a = self._adapter()

            def run():
                try:
                    server = a.listenUsingRfcommWithServiceRecord(name, UUID.fromString(SPP_UUID))
                    self._server = server
                    sock = server.accept()          # blocks until a client connects
                    self._socket = sock
                    try:
                        server.close()
                    except Exception:
                        pass
                    self._server = None
                    remote = sock.getRemoteDevice()
                    self._fire("bluetooth_connected", {
                        "address": str(remote.getAddress()),
                        "name": str(remote.getName()), "role": "server"})
                    self._start_reader(sock)
                except Exception as e:
                    self._fire("bluetooth_error", {"error": str(e), "where": "listen"})

            threading.Thread(target=run, daemon=True).start()
            return {"ok": True, "listening": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── messaging ──
    def send(self, text="", **_):
        """Send a line of text to the connected device."""
        if not self._is_android:
            def echo():
                time.sleep(0.4)
                self._fire("bluetooth_data", {"text": "Эхо: " + str(text)})
            threading.Thread(target=echo, daemon=True).start()
            return {"ok": True, "dev": True, "sent": len(text or "")}
        try:
            if self._socket is None:
                return {"ok": False, "note": "not connected"}
            data = ((text or "") + "\n").encode("utf-8")
            out = self._socket.getOutputStream()
            out.write(data)
            out.flush()
            return {"ok": True, "sent": len(data)}
        except Exception as e:
            self._fire("bluetooth_error", {"error": str(e), "where": "send"})
            return {"ok": False, "error": str(e)}

    def _start_reader(self, sock):
        """Background thread: read incoming lines and emit bluetooth_data."""
        def run():
            try:
                from java.io import BufferedReader, InputStreamReader
                reader = BufferedReader(InputStreamReader(sock.getInputStream(), "UTF-8"))
                while True:
                    line = reader.readLine()
                    if line is None:
                        break
                    self._fire("bluetooth_data", {"text": str(line)})
            except Exception as e:
                self._fire("bluetooth_error", {"error": str(e), "where": "read"})
            finally:
                self._fire("bluetooth_disconnected", {})

        self._reader = threading.Thread(target=run, daemon=True)
        self._reader.start()

    def disconnect(self, **_):
        if not self._is_android:
            self._fire("bluetooth_disconnected", {"dev": True})
            return {"ok": True, "dev": True}
        for obj in (self._socket, self._server):
            try:
                if obj is not None:
                    obj.close()
            except Exception:
                pass
        self._socket = None
        self._server = None
        self._unregister_receiver()
        return {"ok": True}

"""
ENPAF Android — Wi-Fi module
Simple Wi-Fi: current connection info, scan for networks, connect.

Events:
  wifi_scan_result   {ssid, bssid, rssi, frequency, secure}
  wifi_scan_finished {count}
  wifi_connected     {ssid}
  wifi_error         {error, ssid}

Notes: modern Android (10+) restricts programmatic Wi-Fi control. `enable()`
opens the system Wi-Fi panel, and `connect()` uses a network *suggestion*
(the system joins when possible). No third-party imports at module top level.
"""

import struct
import threading
import time

from enpaf.android.manager import Manager


def _int_to_ip(value: int) -> str:
    try:
        return ".".join(str(b) for b in struct.pack("<I", value & 0xFFFFFFFF))
    except Exception:
        return ""


class WifiManager(Manager):
    NAME = "wifi"
    _ALLOWED = {"status", "info", "scan", "networks", "enable", "connect", "disconnect"}

    def _wifi(self):
        from android.content import Context
        return self._ctx().getSystemService(Context.WIFI_SERVICE)

    # ── state ──
    def status(self, **_):
        if not self._is_android:
            return {"available": True, "dev": True, "enabled": True, "ssid": "Dev-WiFi",
                    "rssi": -48, "ip": "192.168.0.42", "link_speed": 300,
                    "note": "wifi runs on-device; desktop stub"}
        try:
            w = self._wifi()
            info = {"available": True, "enabled": bool(w.isWifiEnabled())}
            ci = w.getConnectionInfo()
            if ci is not None:
                ssid = str(ci.getSSID()).strip('"')
                if ssid and ssid != "<unknown ssid>":
                    info["ssid"] = ssid
                    info["rssi"] = int(ci.getRssi())
                    info["link_speed"] = int(ci.getLinkSpeed())
                    info["bssid"] = str(ci.getBSSID())
                    ip = ci.getIpAddress()
                    if ip:
                        info["ip"] = _int_to_ip(ip)
            return info
        except Exception as e:
            return {"available": False, "error": str(e)}

    def info(self, **_):
        return self.status()

    # ── scan ──
    def _scan_to_dict(self, r):
        caps = str(r.capabilities)
        secure = any(k in caps for k in ("WPA", "WEP", "PSK", "EAP"))
        return {"ssid": str(r.SSID), "bssid": str(r.BSSID), "rssi": int(r.level),
                "frequency": int(r.frequency), "secure": secure}

    def scan(self, **_):
        """Trigger a scan; results arrive as `wifi_scan_result` events."""
        if not self._is_android:
            def sim():
                time.sleep(0.5)
                for n in ({"ssid": "HomeNet", "rssi": -42, "secure": True},
                          {"ssid": "Office", "rssi": -61, "secure": True},
                          {"ssid": "FreeCafe", "rssi": -73, "secure": False}):
                    self._fire("wifi_scan_result", n)
                self._fire("wifi_scan_finished", {"count": 3})
            threading.Thread(target=sim, daemon=True).start()
            return {"ok": True, "dev": True}
        try:
            from android.net.wifi import WifiManager as AWifi
            from java import jarray
            from java.lang import String
            w = self._wifi()
            mgr = self

            activity = getattr(self._app.api, "_activity", None)
            if activity is None:
                return {"ok": False, "error": "no Activity"}

            scan_action = str(AWifi.SCAN_RESULTS_AVAILABLE_ACTION)
            actions = jarray(String)([scan_action])
            self._scan_receiver = activity.registerEnpafReceiver("wifi", actions)

            def on_broadcast(payload):
                intent = payload.get("intent")
                if not intent:
                    return
                try:
                    action = str(intent.getAction())
                except Exception:
                    return
                if action == scan_action:
                    try:
                        activity.unregisterEnpafReceiver(mgr._scan_receiver)
                    except Exception:
                        pass
                    mgr._scan_receiver = None
                    try:
                        mgr._app.events.off("broadcast:wifi", mgr._on_broadcast)
                    except Exception:
                        pass
                    try:
                        results = w.getScanResults()
                        for r in results:
                            mgr._fire("wifi_scan_result", mgr._scan_to_dict(r))
                        mgr._fire("wifi_scan_finished", {"count": len(results)})
                    except Exception as e:
                        mgr._fire("wifi_error", {"error": str(e), "ssid": ""})

            self._on_broadcast = on_broadcast
            self._app.events.on("broadcast:wifi", on_broadcast)

            w.startScan()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def scan_sync(self, timeout=8.0):
        """Python helper: scan and RETURN the networks (blocks up to timeout).

        Example (main.py):
            nets = app.wifi.scan_sync()["networks"]
        """
        nets = self._collect("wifi_scan_result", "wifi_scan_finished",
                             self.scan, timeout)
        return {"networks": nets}

    def networks(self, **_):
        """Return the latest scan results synchronously."""
        if not self._is_android:
            return {"dev": True, "networks": [
                {"ssid": "HomeNet", "rssi": -42, "secure": True},
                {"ssid": "FreeCafe", "rssi": -73, "secure": False}]}
        try:
            return {"networks": [self._scan_to_dict(r) for r in self._wifi().getScanResults()]}
        except Exception as e:
            return {"networks": [], "error": str(e)}

    # ── control ──
    def enable(self, **_):
        """Turn Wi-Fi on. On Android 10+ opens the system Wi-Fi panel."""
        if not self._is_android:
            return {"ok": True, "dev": True}
        try:
            from android.os import Build
            from android.content import Intent
            if Build.VERSION.SDK_INT < 29:
                self._wifi().setWifiEnabled(True)
                return {"ok": True}
            from android.provider import Settings
            intent = Intent(Settings.Panel.ACTION_WIFI)
            activity = getattr(self._app.api, "_activity", None)
            if activity is not None:
                activity.startActivity(intent)
            else:
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                self._ctx().startActivity(intent)
            return {"ok": True, "panel": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def connect(self, ssid="", password="", **_):
        """Join a network. On Android 10+ this registers a suggestion the system
        connects to when possible; on older versions it connects directly."""
        if not self._is_android:
            self._fire("wifi_connected", {"ssid": ssid, "dev": True})
            return {"ok": True, "dev": True}
        try:
            from android.os import Build
            if Build.VERSION.SDK_INT >= 29:
                from android.net.wifi import WifiNetworkSuggestion
                from java.util import ArrayList
                b = WifiNetworkSuggestion.Builder().setSsid(ssid)
                if password:
                    b.setWpa2Passphrase(password)
                lst = ArrayList()
                lst.add(b.build())
                status = int(self._wifi().addNetworkSuggestions(lst))
                ok = status == 0
                if ok:
                    self._fire("wifi_connected", {"ssid": ssid, "suggested": True})
                return {"ok": ok, "suggested": True, "status": status,
                        "note": "система подключится к сети при возможности"}
            else:
                from android.net.wifi import WifiConfiguration
                w = self._wifi()
                cfg = WifiConfiguration()
                cfg.SSID = '"' + ssid + '"'
                if password:
                    cfg.preSharedKey = '"' + password + '"'
                else:
                    cfg.allowedKeyManagement.set(WifiConfiguration.KeyMgmt.NONE)
                nid = w.addNetwork(cfg)
                w.disconnect()
                w.enableNetwork(nid, True)
                w.reconnect()
                self._fire("wifi_connected", {"ssid": ssid})
                return {"ok": True, "network_id": int(nid)}
        except Exception as e:
            self._fire("wifi_error", {"error": str(e), "ssid": ssid})
            return {"ok": False, "error": str(e)}

    def disconnect(self, **_):
        if not self._is_android:
            return {"ok": True, "dev": True}
        try:
            return {"ok": True, "note": "use the Wi-Fi panel to forget a network"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

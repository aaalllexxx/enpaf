"""
ENPAF Core — Device API
Built-in APIs for device features (notifications, vibration, etc.).
In dev mode, these are stubs that log to console.
"""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("enpaf.api")

# Friendly sensor name -> android.hardware.Sensor.TYPE_* constant name.
# Resolved lazily (getattr) so this module still imports on desktop/dev.
_SENSOR_TYPES = {
    "accelerometer": "TYPE_ACCELEROMETER",
    "gyroscope": "TYPE_GYROSCOPE",
    "magnetometer": "TYPE_MAGNETIC_FIELD",
    "light": "TYPE_LIGHT",
    "proximity": "TYPE_PROXIMITY",
    "pressure": "TYPE_PRESSURE",
    "gravity": "TYPE_GRAVITY",
    "linear_acceleration": "TYPE_LINEAR_ACCELERATION",
    "rotation_vector": "TYPE_ROTATION_VECTOR",
    "step_counter": "TYPE_STEP_COUNTER",
    "step_detector": "TYPE_STEP_DETECTOR",
    "humidity": "TYPE_RELATIVE_HUMIDITY",
    "temperature": "TYPE_AMBIENT_TEMPERATURE",
    "heart_rate": "TYPE_HEART_RATE",
}

# Plausible values returned for the desktop "dev" mode so the demo UI shows
# something even though there is no real hardware to read.
_SENSOR_DEV_VALUES = {
    "accelerometer": [0.02, 9.79, 0.13],
    "gyroscope": [0.001, -0.002, 0.0],
    "magnetometer": [11.4, -3.2, 42.8],
    "light": [320.0],
    "proximity": [5.0],
    "pressure": [1013.2],
    "gravity": [0.0, 9.81, 0.0],
    "linear_acceleration": [0.0, 0.0, 0.0],
    "rotation_vector": [0.01, 0.02, 0.0],
    "step_counter": [4213.0],
    "humidity": [46.0],
    "temperature": [22.5],
    "heart_rate": [72.0],
}

# Friendly permission name -> full android.permission string (superset of the
# build-time catalog so any string the app passes can be resolved at runtime).
_PERMISSION_ALIASES = {
    "CAMERA": "android.permission.CAMERA",
    "RECORD_AUDIO": "android.permission.RECORD_AUDIO",
    "MICROPHONE": "android.permission.RECORD_AUDIO",
    "FINE_LOCATION": "android.permission.ACCESS_FINE_LOCATION",
    "LOCATION": "android.permission.ACCESS_FINE_LOCATION",
    "COARSE_LOCATION": "android.permission.ACCESS_COARSE_LOCATION",
    "BACKGROUND_LOCATION": "android.permission.ACCESS_BACKGROUND_LOCATION",
    "READ_STORAGE": "android.permission.READ_EXTERNAL_STORAGE",
    "WRITE_STORAGE": "android.permission.WRITE_EXTERNAL_STORAGE",
    "READ_CONTACTS": "android.permission.READ_CONTACTS",
    "CALL_PHONE": "android.permission.CALL_PHONE",
    "SEND_SMS": "android.permission.SEND_SMS",
    "BLUETOOTH_SCAN": "android.permission.BLUETOOTH_SCAN",
    "BLUETOOTH_CONNECT": "android.permission.BLUETOOTH_CONNECT",
    "NFC": "android.permission.NFC",
    "POST_NOTIFICATIONS": "android.permission.POST_NOTIFICATIONS",
    "BODY_SENSORS": "android.permission.BODY_SENSORS",
    "ACTIVITY_RECOGNITION": "android.permission.ACTIVITY_RECOGNITION",
    "READ_MEDIA_IMAGES": "android.permission.READ_MEDIA_IMAGES",
    "READ_MEDIA_VIDEO": "android.permission.READ_MEDIA_VIDEO",
    "READ_MEDIA_AUDIO": "android.permission.READ_MEDIA_AUDIO",
}


def resolve_permission(name: str) -> str:
    """Turn a short permission name into a full android.permission.* string."""
    if not name:
        return ""
    token = str(name).strip()
    if token.startswith("android.permission."):
        return token
    key = token.upper().replace(".", "_")
    if key in _PERMISSION_ALIASES:
        return _PERMISSION_ALIASES[key]
    return "android.permission." + key


def _bytes_to_hex(byte_array) -> str:
    """Hex string for a Java byte[] (Chaquopy hands it to us as Python bytes)."""
    try:
        return bytes(byte_array).hex().upper()
    except Exception:
        return ""


def _normalize_uri(uri: str) -> str:
    """Ensure a URI has a scheme so Android can act on it.

    A bare 'example.com' written as an NDEF URI record is NOT openable — the OS
    needs a scheme. We leave real schemes (https:, tel:, mailto:, geo:, sms:, …)
    untouched and prepend https:// to anything that looks scheme-less.
    """
    import re
    u = (uri or "").strip()
    if not u:
        return u
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:", u):  # already scheme:...
        return u
    if u.startswith("//"):
        return "https:" + u
    return "https://" + u


def _build_wifi_payload(ssid: str, password: str,
                        auth: str = "WPA2-PSK", encryption: str = "AES") -> bytes:
    """Build a Wi-Fi Simple Config (WSC) credential payload for the MIME type
    application/vnd.wfa.wsc — what 'tap to connect to Wi-Fi' tags carry."""
    import struct
    auth_map = {"OPEN": 0x0001, "WPA-PSK": 0x0002, "WPA2-PSK": 0x0020,
                "WPA/WPA2-PSK": 0x0022}
    enc_map = {"NONE": 0x0001, "WEP": 0x0002, "TKIP": 0x0004, "AES": 0x0008,
               "AES/TKIP": 0x000C}

    def tlv(tag: int, value: bytes) -> bytes:
        return struct.pack(">HH", tag, len(value)) + value

    cred = (
        tlv(0x1045, ssid.encode("utf-8")) +                              # SSID
        tlv(0x1003, struct.pack(">H", auth_map.get(auth.upper(), 0x0020))) +   # Auth type
        tlv(0x100F, struct.pack(">H", enc_map.get(encryption.upper(), 0x0008))) +  # Encrypt
        tlv(0x1027, password.encode("utf-8"))                            # Network key
    )
    return tlv(0x100E, cred)  # Credential


def _parse_ndef_record(record) -> Dict[str, Any]:
    """Decode a single android.nfc.NdefRecord into a plain dict."""
    try:
        from android.nfc import NdefRecord
        tnf = int(record.getTnf())
        type_bytes = bytes(record.getType())
        payload = bytes(record.getPayload())
        if tnf == NdefRecord.TNF_WELL_KNOWN and type_bytes == b"T":
            status = payload[0]
            lang_len = status & 0x3F
            lang = payload[1:1 + lang_len].decode("ascii", "replace")
            text = payload[1 + lang_len:].decode("utf-8", "replace")
            return {"type": "text", "lang": lang, "text": text}
        if tnf == NdefRecord.TNF_WELL_KNOWN and type_bytes == b"U":
            try:
                uri = str(record.toUri())
            except Exception:
                uri = payload[1:].decode("utf-8", "replace")
            return {"type": "uri", "uri": uri}
        return {"type": "raw", "tnf": tnf, "bytes": payload.hex().upper()}
    except Exception as e:
        return {"type": "error", "error": str(e)}


class DeviceAPI:
    """
    API for accessing device features.
    
    In dev mode (running in browser), these methods log their calls
    and return mock data. On Android, they forward to native APIs via Chaquopy.
    """

    def __init__(self, is_android: bool = False):
        self._is_android = is_android
        self._bridge = None
        self._activity = None  # set from Java once MainActivity exists (Android)
        self._pending_nfc = None  # an armed write/lock awaiting the next tag

    def set_bridge(self, bridge):
        """Set the bridge for Android communication."""
        self._bridge = bridge

    def set_activity(self, activity):
        """Store the Android Activity reference (needed to request permissions
        and run things on the UI thread). Called from MainActivity via Python."""
        self._activity = activity

    def toast(self, message: str, duration: str = "short") -> None:
        """Show a toast notification."""
        if self._is_android:
            try:
                from com.chaquo.python import Python
                from android.widget import Toast
                from android.os import Handler, Looper
                from java.lang import Runnable

                class ToastRunnable(Runnable):
                    def __init__(self, ctx, msg, dur):
                        self.ctx = ctx
                        self.msg = msg
                        self.dur = dur
                    def run(self):
                        Toast.makeText(self.ctx, self.msg, self.dur).show()

                context = Python.getPlatform().getApplication()
                dur = Toast.LENGTH_LONG if duration == "long" else Toast.LENGTH_SHORT
                handler = Handler(Looper.getMainLooper())
                handler.post(ToastRunnable(context, message, dur))
            except Exception as e:
                logger.error(f"Native toast error: {e}")
        else:
            logger.info(f"📱 Toast: {message} (duration={duration})")

    def vibrate(self, milliseconds: int = 100) -> None:
        """Vibrate the device."""
        if self._is_android:
            try:
                from com.chaquo.python import Python
                context = Python.getPlatform().getApplication()
                vibrator = context.getSystemService("vibrator")
                if vibrator:
                    vibrator.vibrate(milliseconds)
            except Exception as e:
                logger.error(f"Native vibrate error: {e}")
        else:
            logger.info(f"📱 Vibrate: {milliseconds}ms")

    def notify(self, title: str, text: str = "", notification_id: int = 1,
               payload: str = "", action: str = "",
               image_base64: str = None, buttons: list = None) -> None:
        """Show a system notification."""
        if self._is_android:
            try:
                from com.chaquo.python import Python
                from android.app import NotificationManager, NotificationChannel, PendingIntent
                from android.content import Context, Intent
                from android.os import Build
                from androidx.core.app import NotificationCompat

                context = Python.getPlatform().getApplication()
                nm = context.getSystemService(Context.NOTIFICATION_SERVICE)
                if not nm:
                    return

                channel_id = "enpaf_default"
                if Build.VERSION.SDK_INT >= 26: # Build.VERSION_CODES.O
                    channel = NotificationChannel(channel_id, "Notifications", NotificationManager.IMPORTANCE_DEFAULT)
                    nm.createNotificationChannel(channel)

                # Need an icon, using application info icon or default android icon
                icon_id = context.getApplicationInfo().icon
                if icon_id == 0:
                    icon_id = 17301651 # android.R.drawable.stat_notify_chat

                builder = NotificationCompat.Builder(context, channel_id)
                builder.setSmallIcon(icon_id)
                builder.setContentTitle(title)
                if text:
                    builder.setContentText(text)
                builder.setPriority(NotificationCompat.PRIORITY_DEFAULT)
                builder.setAutoCancel(True)

                # Intent to open MainActivity on click
                content_intent = context.getPackageManager().getLaunchIntentForPackage(context.getPackageName())
                content_intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP)
                if payload or action:
                    content_intent.putExtra("enpaf_action", action)
                    content_intent.putExtra("enpaf_payload", payload)
                
                pi_flags = PendingIntent.FLAG_UPDATE_CURRENT
                if Build.VERSION.SDK_INT >= 23: # M
                    pi_flags |= PendingIntent.FLAG_IMMUTABLE
                
                pi = PendingIntent.getActivity(context, notification_id, content_intent, pi_flags)
                builder.setContentIntent(pi)

                # Image
                if image_base64:
                    import base64
                    from android.graphics import BitmapFactory
                    img_data = base64.b64decode(image_base64)
                    bitmap = BitmapFactory.decodeByteArray(img_data, 0, len(img_data))
                    if bitmap:
                        style = NotificationCompat.BigPictureStyle().bigPicture(bitmap).bigLargeIcon(None)
                        builder.setStyle(style)
                        builder.setLargeIcon(bitmap)

                # Buttons
                if buttons:
                    for i, btn in enumerate(buttons):
                        btn_intent = context.getPackageManager().getLaunchIntentForPackage(context.getPackageName())
                        btn_intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP)
                        btn_intent.putExtra("enpaf_action", btn.get("action", ""))
                        btn_intent.putExtra("enpaf_payload", btn.get("payload", ""))
                        btn_pi = PendingIntent.getActivity(context, notification_id * 100 + i + 1, btn_intent, pi_flags)
                        builder.addAction(0, btn.get("text", ""), btn_pi)

                nm.notify(notification_id, builder.build())
            except Exception as e:
                logger.error(f"Native notify error: {e}")
        else:
            logger.info(f"📱 Notify: {title} — {text} (action={action}, payload={payload})")

    def get_device_info(self) -> Dict[str, Any]:
        """Get device information."""
        if self._is_android:
            try:
                from com.chaquo.python import Python
                from android.os import Build
                context = Python.getPlatform().getApplication()
                pkg_manager = context.getPackageManager()
                pkg_info = pkg_manager.getPackageInfo(context.getPackageName(), 0)
                app_version = pkg_info.versionName
                return {
                    "platform": "android",
                    "model": Build.MODEL,
                    "os_version": Build.VERSION.RELEASE,
                    "app_version": app_version,
                    "screen_width": context.getResources().getDisplayMetrics().widthPixels,
                    "screen_height": context.getResources().getDisplayMetrics().heightPixels,
                    "is_android": True,
                }
            except Exception as e:
                logger.error(f"Native get_device_info error: {e}")
                return {"is_android": True, "error": str(e)}
        else:
            return {
                "platform": "dev",
                "model": "Desktop Browser",
                "os_version": "N/A",
                "app_version": "1.0.0",
                "screen_width": 0,
                "screen_height": 0,
                "is_android": False,
            }

    def set_status_bar_color(self, color: str) -> None:
        """Set the status bar color (Android only)."""
        if self._is_android:
            logger.warning("📱 set_status_bar_color requires Activity reference, which is not available from Application Context in Python yet.")
        else:
            logger.info(f"📱 Status bar color: {color}")

    def set_orientation(self, orientation: str) -> None:
        """Lock screen orientation."""
        if self._is_android:
            logger.warning("📱 set_orientation requires Activity reference, which is not available from Application Context in Python yet.")
        else:
            logger.info(f"📱 Orientation: {orientation}")

    def open_url(self, url: str) -> None:
        """Open a URL in the system browser."""
        if self._is_android:
            try:
                from com.chaquo.python import Python
                from android.content import Intent
                from android.net import Uri
                context = Python.getPlatform().getApplication()
                intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
            except Exception as e:
                logger.error(f"Native open_url error: {e}")
        else:
            logger.info(f"📱 Open URL: {url}")
            import webbrowser
            webbrowser.open(url)

    def clipboard_set(self, text: str) -> None:
        """Copy text to clipboard."""
        if self._is_android:
            try:
                from com.chaquo.python import Python
                from android.content import Context, ClipData
                from android.os import Handler, Looper
                from java.lang import Runnable

                context = Python.getPlatform().getApplication()
                
                class ClipRunnable(Runnable):
                    def run(self):
                        cm = context.getSystemService(Context.CLIPBOARD_SERVICE)
                        if cm:
                            cm.setPrimaryClip(ClipData.newPlainText("enpaf", text))
                            
                handler = Handler(Looper.getMainLooper())
                handler.post(ClipRunnable())
            except Exception as e:
                logger.error(f"Native clipboard_set error: {e}")
        else:
            logger.info(f"📱 Clipboard: {text[:50]}...")

    def clipboard_get(self) -> str:
        """Get text from clipboard."""
        if self._is_android:
            try:
                from com.chaquo.python import Python
                from android.content import Context
                context = Python.getPlatform().getApplication()
                cm = context.getSystemService(Context.CLIPBOARD_SERVICE)
                if cm and cm.hasPrimaryClip() and cm.getPrimaryClip().getItemCount() > 0:
                    return str(cm.getPrimaryClip().getItemAt(0).getText())
            except Exception as e:
                logger.error(f"Native clipboard_get error: {e}")
            return ""
        else:
            logger.info("📱 Clipboard get (dev mode — returning empty)")
            return ""

    def share(self, text: str, title: str = "") -> None:
        """Share text via Android share dialog."""
        if self._is_android:
            try:
                from com.chaquo.python import Python
                from android.content import Intent
                context = Python.getPlatform().getApplication()
                intent = Intent(Intent.ACTION_SEND)
                intent.setType("text/plain")
                intent.putExtra(Intent.EXTRA_TEXT, text)
                chooser = Intent.createChooser(intent, title if title else "Share")
                chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(chooser)
            except Exception as e:
                logger.error(f"Native share error: {e}")
        else:
            logger.info(f"📱 Share: {title} — {text}")

    # ═══════════════════════════════════════════════════════════
    # Sensors & device readings
    # Each method returns a JSON-serializable dict. On desktop it returns a
    # `dev: true` stub so the same UI works while testing on the computer.
    # ═══════════════════════════════════════════════════════════

    def _application(self):
        """Return the Android Application context (Android only)."""
        from com.chaquo.python import Python
        return Python.getPlatform().getApplication()

    def read_sensor(self, sensor: str = "accelerometer", timeout: float = 2.0, **_) -> Dict[str, Any]:
        """Read a single snapshot from a hardware sensor.

        sensor: one of _SENSOR_TYPES keys (accelerometer, gyroscope, ...).
        """
        sensor = (sensor or "accelerometer").lower()
        const = _SENSOR_TYPES.get(sensor)
        if const is None:
            return {"available": False, "sensor": sensor, "error": "unknown sensor"}

        if not self._is_android:
            return {"available": False, "dev": True, "sensor": sensor,
                    "values": list(_SENSOR_DEV_VALUES.get(sensor, [0.0])),
                    "note": "sensors are read on-device; this is a desktop stub"}
        try:
            import threading
            from android.content import Context
            from android.hardware import Sensor, SensorManager, SensorEventListener
            from java import dynamic_proxy

            type_id = getattr(Sensor, const)
            ctx = self._application()
            sm = ctx.getSystemService(Context.SENSOR_SERVICE)
            s = sm.getDefaultSensor(type_id)
            if s is None:
                return {"available": False, "sensor": sensor, "note": "sensor not present"}

            box, done = {}, threading.Event()

            class _Listener(dynamic_proxy(SensorEventListener)):
                def onSensorChanged(self, event):
                    if not done.is_set():
                        box["values"] = [float(v) for v in event.values]
                        box["accuracy"] = int(event.accuracy)
                        done.set()

                def onAccuracyChanged(self, sensor_, accuracy):
                    pass

            listener = _Listener()
            sm.registerListener(listener, s, SensorManager.SENSOR_DELAY_NORMAL)
            done.wait(max(0.2, float(timeout)))
            sm.unregisterListener(listener)
            return {
                "available": True,
                "sensor": sensor,
                "name": str(s.getName()),
                "vendor": str(s.getVendor()),
                "values": box.get("values"),
                "accuracy": box.get("accuracy"),
                "fix": "values" in box,
            }
        except Exception as e:
            logger.error(f"read_sensor({sensor}) error: {e}")
            return {"available": False, "sensor": sensor, "error": str(e)}

    def list_sensors(self, **_) -> Dict[str, Any]:
        """List the hardware sensors present on the device."""
        if not self._is_android:
            return {"available": False, "dev": True,
                    "sensors": [{"name": k, "type": k} for k in _SENSOR_TYPES]}
        try:
            from android.content import Context
            from android.hardware import Sensor
            ctx = self._application()
            sm = ctx.getSystemService(Context.SENSOR_SERVICE)
            out = []
            for s in sm.getSensorList(Sensor.TYPE_ALL):
                out.append({
                    "name": str(s.getName()),
                    "vendor": str(s.getVendor()),
                    "type": int(s.getType()),
                    "power": float(s.getPower()),
                })
            return {"available": True, "sensors": out}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def get_location(self, timeout: float = 5.0, **_) -> Dict[str, Any]:
        """Return the most recent known location (last fix)."""
        if not self._is_android:
            return {"available": False, "dev": True, "fix": True,
                    "latitude": 55.751244, "longitude": 37.618423,
                    "accuracy": 30.0, "provider": "mock",
                    "note": "location is read on-device; desktop stub"}
        try:
            from android.content import Context
            ctx = self._application()
            lm = ctx.getSystemService(Context.LOCATION_SERVICE)
            if lm is None:
                return {"available": False, "error": "no location service"}
            best = None
            for p in ("gps", "network", "passive"):
                try:
                    loc = lm.getLastKnownLocation(p)
                except Exception:
                    loc = None  # SecurityException when permission not granted
                if loc is not None and (best is None or loc.getTime() > best.getTime()):
                    best = loc
            if best is None:
                return {"available": True, "fix": False,
                        "note": "no last-known location (grant location & open Maps once)"}
            return {
                "available": True, "fix": True,
                "latitude": float(best.getLatitude()),
                "longitude": float(best.getLongitude()),
                "accuracy": float(best.getAccuracy()),
                "altitude": float(best.getAltitude()),
                "provider": str(best.getProvider()),
                "time": int(best.getTime()),
            }
        except Exception as e:
            logger.error(f"get_location error: {e}")
            return {"available": False, "error": str(e)}

    def get_bluetooth(self, **_) -> Dict[str, Any]:
        """Return Bluetooth adapter state and bonded (paired) devices."""
        if not self._is_android:
            return {"available": False, "dev": True, "enabled": False,
                    "name": "Dev-Bluetooth", "bonded": [],
                    "note": "bluetooth is read on-device; desktop stub"}
        try:
            from android.bluetooth import BluetoothAdapter
            adapter = BluetoothAdapter.getDefaultAdapter()
            if adapter is None:
                return {"available": False, "note": "no bluetooth adapter"}
            info = {"available": True, "enabled": bool(adapter.isEnabled())}
            try:
                info["name"] = str(adapter.getName())
            except Exception:
                pass
            bonded = []
            try:  # requires BLUETOOTH_CONNECT on Android 12+
                for d in adapter.getBondedDevices():
                    bonded.append({"name": str(d.getName()), "address": str(d.getAddress())})
            except Exception as e:
                info["bonded_error"] = str(e)
            info["bonded"] = bonded
            return info
        except Exception as e:
            return {"available": False, "error": str(e)}

    def get_nfc(self, **_) -> Dict[str, Any]:
        """Return NFC adapter presence/state."""
        if not self._is_android:
            return {"available": False, "dev": True, "present": False, "enabled": False,
                    "note": "nfc is read on-device; desktop stub"}
        try:
            from android.nfc import NfcAdapter
            ctx = self._application()
            adapter = NfcAdapter.getDefaultAdapter(ctx)
            if adapter is None:
                return {"available": True, "present": False, "enabled": False,
                        "note": "device has no NFC"}
            return {"available": True, "present": True, "enabled": bool(adapter.isEnabled())}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def _last_nfc_tag(self):
        """Return the most recently scanned android.nfc.Tag (or None).

        MainActivity captures tags via NFC foreground dispatch and exposes them
        through getLastNfcTag(); reset_after consumes it so a stale tag is not
        re-used by a later write/lock by accident.
        """
        if self._activity is None:
            return None
        try:
            return self._activity.getLastNfcTag()
        except Exception:
            return None

    def nfc_read(self, **_) -> Dict[str, Any]:
        """Read the NDEF content of the last-tapped NFC tag."""
        if not self._is_android:
            return {"available": False, "dev": True, "tag": True,
                    "id": "DE:AD:BE:EF",
                    "records": [{"type": "text", "lang": "en",
                                 "text": getattr(self, "_dev_nfc_text", "ENPAF demo tag")}],
                    "writable": not getattr(self, "_dev_nfc_locked", False),
                    "note": "NFC reading happens on-device; desktop stub"}
        try:
            tag = self._last_nfc_tag()
            if tag is None:
                return {"available": True, "tag": False, "note": "tap an NFC tag to the phone"}
            from android.nfc.tech import Ndef
            info = {"available": True, "tag": True, "id": _bytes_to_hex(tag.getId())}
            ndef = Ndef.get(tag)
            if ndef is None:
                info["records"] = []
                info["note"] = "tag is not NDEF-formatted"
                return info
            ndef.connect()
            try:
                msg = ndef.getNdefMessage()
                info["writable"] = bool(ndef.isWritable())
                info["max_size"] = int(ndef.getMaxSize())
            finally:
                ndef.close()
            info["records"] = [_parse_ndef_record(r) for r in msg.getRecords()] if msg else []
            return info
        except Exception as e:
            logger.error(f"nfc_read error: {e}")
            return {"available": False, "error": str(e)}

    # ── NFC writing: every common NDEF record type ──────────────

    @staticmethod
    def _spec_summary(spec: Dict[str, Any]) -> str:
        """Short human description of a record spec (used by the dev stub)."""
        kind = spec.get("kind", "text")
        return {
            "text": f"text:{spec.get('text', '')}",
            "uri": f"uri:{spec.get('uri', '')}",
            "app": f"app:{spec.get('package', '')}",
            "mime": f"mime:{spec.get('mime', '')}",
            "external": f"ext:{spec.get('domain', '')}:{spec.get('type', '')}",
        }.get(kind, kind)

    def _ndef_record_from_spec(self, spec: Dict[str, Any]):
        """Build one android.nfc.NdefRecord from a {"kind": ...} spec (Android)."""
        from android.nfc import NdefRecord
        kind = spec.get("kind", "text")
        if kind == "text":
            return NdefRecord.createTextRecord(spec.get("lang", "en"), spec.get("text", ""))
        if kind == "uri":
            return NdefRecord.createUri(_normalize_uri(spec.get("uri", "")))
        if kind == "app":
            pkg = (spec.get("package") or "").strip()
            if not pkg:
                raise ValueError("app record requires a non-empty package name")
            return NdefRecord.createApplicationRecord(pkg)
        if kind == "mime":
            data = spec.get("data", "")
            payload = data.encode("utf-8") if isinstance(data, str) else bytes(data)
            return NdefRecord.createMime(spec.get("mime", "text/plain"), payload)
        if kind == "external":
            data = spec.get("data", "")
            payload = data.encode("utf-8") if isinstance(data, str) else bytes(data)
            return NdefRecord.createExternal(
                spec.get("domain", "com.enpaf"), spec.get("type", "app"), payload)
        raise ValueError(f"unknown NDEF record kind: {kind!r}")

    def _nfc_write_message(self, tag, msg) -> Dict[str, Any]:
        """Write an NdefMessage to a tag, formatting it first if it is blank."""
        from android.nfc.tech import Ndef, NdefFormatable
        ndef = Ndef.get(tag)
        if ndef is not None:
            ndef.connect()
            try:
                if not ndef.isWritable():
                    return {"written": False, "note": "tag is read-only"}
                needed = len(bytes(msg.toByteArray()))
                if int(ndef.getMaxSize()) < needed:
                    return {"written": False, "note": f"tag too small ({needed} bytes needed)"}
                ndef.writeNdefMessage(msg)
            finally:
                ndef.close()
            return {"written": True, "bytes": needed}
        formatable = NdefFormatable.get(tag)
        if formatable is not None:  # blank/unformatted tag
            formatable.connect()
            try:
                formatable.format(msg)
            finally:
                formatable.close()
            return {"written": True, "formatted": True}
        return {"written": False, "note": "tag does not support NDEF"}

    def nfc_write_records(self, records=None, **_) -> Dict[str, Any]:
        """Write an arbitrary list of NDEF record specs to the last-tapped tag.

        Each spec is a dict with a "kind": "text" | "uri" | "app" | "mime" |
        "external". This is the general form behind all the nfc_write_* helpers.
        """
        specs = records or []
        if not specs:
            return {"written": False, "note": "no records to write"}
        if not self._is_android:
            self._dev_nfc_text = "; ".join(self._spec_summary(s) for s in specs)
            if getattr(self, "_dev_nfc_locked", False):
                return {"written": False, "dev": True, "note": "tag is locked (read-only)"}
            return {"written": True, "dev": True,
                    "records": [self._spec_summary(s) for s in specs]}
        try:
            tag = self._last_nfc_tag()
            if tag is None:
                return {"written": False, "note": "tap an NFC tag to the phone"}
            from android.nfc import NdefMessage, NdefRecord
            from java import jarray
            recs = [self._ndef_record_from_spec(s) for s in specs]
            msg = NdefMessage(jarray(NdefRecord)(recs))
            return self._nfc_write_message(tag, msg)
        except Exception as e:
            logger.error(f"nfc_write_records error: {e}")
            return {"written": False, "error": str(e)}

    def nfc_write(self, text: str = "", uri: str = "", **_) -> Dict[str, Any]:
        """Write a single text (or URI) record — the simplest shortcut."""
        spec = ({"kind": "uri", "uri": _normalize_uri(uri)} if uri
                else {"kind": "text", "text": text})
        return self.nfc_write_records(records=[spec])

    def nfc_write_text(self, text: str = "", lang: str = "en", **_) -> Dict[str, Any]:
        """Write a plain-text record."""
        return self.nfc_write_records(records=[{"kind": "text", "text": text, "lang": lang}])

    def nfc_write_uri(self, uri: str = "", **_) -> Dict[str, Any]:
        """Write a URI/URL record (also covers tel:, mailto:, geo:, sms: …)."""
        return self.nfc_write_records(records=[{"kind": "uri", "uri": _normalize_uri(uri)}])

    def nfc_write_app(self, package: str = "", uri: str = "", **_) -> Dict[str, Any]:
        """Write an Android Application Record (AAR): tapping opens the app, or
        the Play Store if it is not installed. Optionally prepend a URI record.

        When `package` is omitted, defaults to this app's own package so a
        tapped tag re-launches the current app.
        """
        package = (package or "").strip()
        if not package and self._is_android:
            try:
                package = str(self._application().getPackageName())
            except Exception:
                package = ""
        if not package:
            return {"written": False,
                    "note": "package name is required for an app-launch record"}
        specs = []
        if uri:
            specs.append({"kind": "uri", "uri": _normalize_uri(uri)})
        specs.append({"kind": "app", "package": package})
        return self.nfc_write_records(records=specs)

    def nfc_write_mime(self, mime: str = "text/plain", data: str = "", **_) -> Dict[str, Any]:
        """Write a MIME-typed record (e.g. application/json, text/vcard)."""
        return self.nfc_write_records(records=[{"kind": "mime", "mime": mime, "data": data}])

    def nfc_write_wifi(self, ssid: str = "", password: str = "",
                       auth: str = "WPA2-PSK", encryption: str = "AES", **_) -> Dict[str, Any]:
        """Write Wi-Fi credentials (tap to join the network)."""
        payload = _build_wifi_payload(ssid, password, auth, encryption)
        return self.nfc_write_records(
            records=[{"kind": "mime", "mime": "application/vnd.wfa.wsc", "data": payload}])

    def nfc_write_contact(self, name: str = "", phone: str = "", email: str = "", **_) -> Dict[str, Any]:
        """Write a contact (vCard) record."""
        vcard = ("BEGIN:VCARD\r\nVERSION:3.0\r\n"
                 f"N:{name}\r\nFN:{name}\r\nTEL:{phone}\r\nEMAIL:{email}\r\n"
                 "END:VCARD\r\n")
        return self.nfc_write_records(records=[{"kind": "mime", "mime": "text/vcard", "data": vcard}])

    _ARMABLE_NFC = {
        "nfc_write", "nfc_write_text", "nfc_write_uri", "nfc_write_app",
        "nfc_write_mime", "nfc_write_wifi", "nfc_write_contact", "nfc_write_records",
    }

    def nfc_arm_write(self, method: str = "", args=None, lock: bool = False, **_) -> Dict[str, Any]:
        """Queue a write (and/or lock) to run on the NEXT tapped tag.

        This is the reliable pattern: an android.nfc.Tag handle goes stale the
        moment the tag leaves the field, so writing to an already-removed tag
        silently fails. Instead we arm the operation and execute it the instant
        a fresh tag is tapped (app._on_nfc_tag -> consume_pending_nfc). The
        outcome is delivered via the `nfc_write_result` event.
        """
        if method and method not in self._ARMABLE_NFC:
            return {"armed": False, "error": f"not an NFC write method: {method}"}
        self._pending_nfc = {"method": method or "", "args": args or {}, "lock": bool(lock)}
        return {"armed": True, "method": method, "lock": bool(lock)}

    def nfc_cancel_write(self, **_) -> Dict[str, Any]:
        """Cancel a queued write."""
        self._pending_nfc = None
        return {"armed": False}

    def consume_pending_nfc(self):
        """Run a queued write/lock against the freshly-tapped tag (Android).

        Called from app._on_nfc_tag right after MainActivity captured the tag,
        so the Tag handle is still valid. Returns a result dict or None.
        """
        pending = getattr(self, "_pending_nfc", None)
        if not pending:
            return None
        self._pending_nfc = None
        result = {}
        method = pending.get("method")
        if method and method in self._ARMABLE_NFC:
            result = getattr(self, method)(**(pending.get("args") or {}))
        if pending.get("lock") and (result.get("written", True) is not False):
            lock_res = self.nfc_make_readonly(confirm=True)
            result = {**result, "locked": lock_res.get("locked", False)}
        # Read the tag back so the UI can prove exactly what is on it (this is
        # where a scheme-less / wrong record shows up).
        if result.get("written") and self._is_android:
            try:
                verify = self.nfc_read()
                result["verify"] = verify.get("records")
            except Exception:
                pass
        return result or {"written": False, "note": "nothing armed"}

    def nfc_make_readonly(self, confirm: bool = False, **_) -> Dict[str, Any]:
        """Permanently lock the last-tapped tag to read-only ("block" it).

        This is IRREVERSIBLE, so it only proceeds when confirm=True.
        """
        if not confirm:
            return {"locked": False, "note": "irreversible — call with confirm=true"}
        if not self._is_android:
            self._dev_nfc_locked = True
            return {"locked": True, "dev": True,
                    "note": "tag would be permanently read-only on-device"}
        try:
            tag = self._last_nfc_tag()
            if tag is None:
                return {"locked": False, "note": "tap an NFC tag to the phone"}
            from android.nfc.tech import Ndef
            ndef = Ndef.get(tag)
            if ndef is None:
                return {"locked": False, "note": "tag is not NDEF-formatted"}
            ndef.connect()
            try:
                if not ndef.canMakeReadOnly():
                    return {"locked": False, "note": "this tag cannot be locked"}
                ok = bool(ndef.makeReadOnly())
            finally:
                ndef.close()
            return {"locked": ok}
        except Exception as e:
            logger.error(f"nfc_make_readonly error: {e}")
            return {"locked": False, "error": str(e)}

    def get_audio_level(self, duration: float = 0.4, **_) -> Dict[str, Any]:
        """Sample the microphone briefly and return its peak amplitude.

        Requires the RECORD_AUDIO permission to be granted.
        """
        if not self._is_android:
            return {"available": False, "dev": True, "amplitude": 1280, "db": 42.1,
                    "note": "microphone is read on-device; desktop stub"}
        recorder = None
        try:
            import os
            import time
            from android.media import MediaRecorder
            data_dir = os.environ.get("ENPAF_DATA_DIR", "/data/local/tmp")
            out = os.path.join(data_dir, "_enpaf_mic.3gp")
            recorder = MediaRecorder()
            recorder.setAudioSource(MediaRecorder.AudioSource.MIC)
            recorder.setOutputFormat(MediaRecorder.OutputFormat.THREE_GPP)
            recorder.setAudioEncoder(MediaRecorder.AudioEncoder.AMR_NB)
            recorder.setOutputFile(out)
            recorder.prepare()
            recorder.start()
            recorder.getMaxAmplitude()  # first call primes the counter
            time.sleep(max(0.1, float(duration)))
            amp = int(recorder.getMaxAmplitude())
            recorder.stop()
            import math
            db = round(20.0 * math.log10(amp), 1) if amp > 0 else 0.0
            return {"available": True, "amplitude": amp, "db": db}
        except Exception as e:
            logger.error(f"get_audio_level error: {e}")
            return {"available": False, "error": str(e)}
        finally:
            try:
                if recorder is not None:
                    recorder.release()
            except Exception:
                pass

    def get_battery(self, **_) -> Dict[str, Any]:
        """Return battery level and charging state."""
        if not self._is_android:
            return {"available": False, "dev": True, "level": 87, "charging": True,
                    "note": "battery is read on-device; desktop stub"}
        try:
            from android.content import Context, IntentFilter
            from android.os import BatteryManager
            ctx = self._application()
            bm = ctx.getSystemService(Context.BATTERY_SERVICE)
            level = int(bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY))
            status = ctx.registerReceiver(None, IntentFilter("android.intent.action.BATTERY_CHANGED"))
            charging = False
            if status is not None:
                st = status.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
                charging = st in (BatteryManager.BATTERY_STATUS_CHARGING,
                                  BatteryManager.BATTERY_STATUS_FULL)
            return {"available": True, "level": level, "charging": bool(charging)}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def get_network(self, **_) -> Dict[str, Any]:
        """Return basic connectivity info (type / connected)."""
        if not self._is_android:
            return {"available": False, "dev": True, "connected": True, "type": "wifi",
                    "note": "network is read on-device; desktop stub"}
        try:
            from android.content import Context
            ctx = self._application()
            cm = ctx.getSystemService(Context.CONNECTIVITY_SERVICE)
            active = cm.getActiveNetworkInfo()
            if active is None or not active.isConnected():
                return {"available": True, "connected": False, "type": "none"}
            return {"available": True, "connected": True,
                    "type": str(active.getTypeName()).lower(),
                    "subtype": str(active.getSubtypeName())}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def get_sensor_snapshot(self, **_) -> Dict[str, Any]:
        """Convenience: read the most common sensors plus device state in one call."""
        return {
            "location": self.get_location(),
            "accelerometer": self.read_sensor("accelerometer"),
            "gyroscope": self.read_sensor("gyroscope"),
            "magnetometer": self.read_sensor("magnetometer"),
            "light": self.read_sensor("light"),
            "proximity": self.read_sensor("proximity"),
            "bluetooth": self.get_bluetooth(),
            "nfc": self.get_nfc(),
            "battery": self.get_battery(),
            "network": self.get_network(),
        }

    # ═══════════════════════════════════════════════════════════
    # Runtime permissions (requested on demand, from Python)
    # ═══════════════════════════════════════════════════════════

    def check_permission(self, permission: str = "", **_) -> Dict[str, Any]:
        """Return whether a single permission is currently granted."""
        full = resolve_permission(permission)
        if not self._is_android:
            return {"permission": full, "granted": False, "dev": True}
        try:
            from androidx.core.content import ContextCompat
            from android.content.pm import PackageManager
            ctx = self._application()
            granted = ContextCompat.checkSelfPermission(ctx, full) == PackageManager.PERMISSION_GRANTED
            return {"permission": full, "granted": bool(granted)}
        except Exception as e:
            return {"permission": full, "granted": False, "error": str(e)}

    def check_permissions(self, permissions=None, **_) -> Dict[str, Any]:
        """Return granted status for a list of permissions."""
        perms = permissions or []
        results = {p: self.check_permission(p)["granted"] for p in perms}
        return {"results": results,
                "granted": [p for p, g in results.items() if g],
                "denied": [p for p, g in results.items() if not g]}

    def request_permissions(self, permissions=None, **_) -> Dict[str, Any]:
        """Ask the user to grant one or more runtime permissions, on demand.

        This is what makes the permission prompt appear *when you choose* (e.g.
        when a feature is first used) instead of at app launch. The final result
        is delivered asynchronously to JavaScript via the `permission_result`
        event (and to Python `@app.on("permission_result")` handlers).

        Returns immediately with what is already granted and what was requested.
        """
        perms = [resolve_permission(p) for p in (permissions or []) if p]
        perms = [p for p in perms if p]
        if not perms:
            return {"requested": [], "granted": [], "pending": False}

        if not self._is_android:
            # Nothing to prompt on the desktop; report everything as "not granted"
            # so the calling code can branch, and echo a result event for parity.
            result = {"code": 0, "results": {p: False for p in perms},
                      "granted": [], "denied": perms, "dev": True}
            self._emit_permission_result(result)
            return {"requested": perms, "granted": [], "pending": False, "dev": True}

        try:
            already = [p for p in perms if self.check_permission(p)["granted"]]
            to_request = [p for p in perms if p not in already]
            if not to_request:
                result = {"code": 0, "results": {p: True for p in perms},
                          "granted": perms, "denied": []}
                self._emit_permission_result(result)
                return {"requested": [], "granted": perms, "pending": False}

            code = self._next_permission_code()
            activity = self._activity
            if activity is None:
                return {"requested": to_request, "granted": already, "pending": False,
                        "error": "no Activity reference; cannot prompt"}

            from java import jarray
            from java.lang import String, Runnable
            from java import dynamic_proxy

            arr = jarray(String)(to_request)

            class _Req(dynamic_proxy(Runnable)):
                def run(self):
                    activity.requestPermissions(arr, code)

            activity.runOnUiThread(_Req())
            return {"requested": to_request, "granted": already, "pending": True, "code": code}
        except Exception as e:
            logger.error(f"request_permissions error: {e}")
            return {"requested": perms, "granted": [], "pending": False, "error": str(e)}

    _perm_code = 1900

    def _next_permission_code(self) -> int:
        DeviceAPI._perm_code = (DeviceAPI._perm_code + 1) % 60000 + 1900
        return DeviceAPI._perm_code

    def _emit_permission_result(self, result: Dict[str, Any]) -> None:
        """Fan a permission result out to JS and Python event handlers."""
        if self._bridge is not None:
            try:
                self._bridge.emit_to_js("permission_result", result)
            except Exception as e:
                logger.error(f"emit permission_result error: {e}")

    # ═══════════════════════════════════════════════════════════
    # Dispatcher used by the built-in __enpaf_api bridge handler
    # ═══════════════════════════════════════════════════════════

    _ALLOWED_METHODS = {
        "read_sensor", "list_sensors", "get_location", "get_bluetooth", "get_nfc",
        "nfc_read", "nfc_write", "nfc_write_records", "nfc_write_text", "nfc_write_uri",
        "nfc_write_app", "nfc_write_mime", "nfc_write_wifi", "nfc_write_contact",
        "nfc_arm_write", "nfc_cancel_write", "nfc_make_readonly",
        "get_audio_level", "get_battery", "get_network", "get_sensor_snapshot",
        "get_device_info", "check_permission", "check_permissions", "request_permissions",
        "toast", "vibrate", "notify", "share", "open_url", "clipboard_get", "clipboard_set",
    }

    def invoke(self, method: str, args: Dict[str, Any] = None) -> Any:
        """Call an allow-listed DeviceAPI method by name with keyword args."""
        if method not in self._ALLOWED_METHODS:
            raise ValueError(f"unknown api method: {method!r}")
        fn = getattr(self, method)
        return fn(**(args or {}))

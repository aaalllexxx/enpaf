"""
ENPAF Android — Hardware Features
<uses-feature> declarations so the app can advertise/optionally require
hardware: camera, NFC, sensors, bluetooth, etc.
"""

from xml.sax.saxutils import quoteattr

# key -> (android feature name, human description)
FEATURES = {
    "CAMERA": ("android.hardware.camera", "Camera"),
    "CAMERA_FRONT": ("android.hardware.camera.front", "Front camera"),
    "CAMERA_AUTOFOCUS": ("android.hardware.camera.autofocus", "Camera autofocus"),
    "NFC": ("android.hardware.nfc", "NFC"),
    "BLUETOOTH": ("android.hardware.bluetooth", "Bluetooth"),
    "BLUETOOTH_LE": ("android.hardware.bluetooth_le", "Bluetooth Low Energy"),
    "GPS": ("android.hardware.location.gps", "GPS location"),
    "LOCATION": ("android.hardware.location", "Location"),
    "MICROPHONE": ("android.hardware.microphone", "Microphone"),
    "WIFI": ("android.hardware.wifi", "Wi-Fi"),
    "TELEPHONY": ("android.hardware.telephony", "Telephony (SIM)"),
    "TOUCHSCREEN": ("android.hardware.touchscreen", "Touchscreen"),
    "FINGERPRINT": ("android.hardware.fingerprint", "Fingerprint sensor"),
    "ACCELEROMETER": ("android.hardware.sensor.accelerometer", "Accelerometer"),
    "GYROSCOPE": ("android.hardware.sensor.gyroscope", "Gyroscope"),
    "COMPASS": ("android.hardware.sensor.compass", "Compass / magnetometer"),
    "PROXIMITY": ("android.hardware.sensor.proximity", "Proximity sensor"),
    "LIGHT": ("android.hardware.sensor.light", "Light sensor"),
    "BAROMETER": ("android.hardware.sensor.barometer", "Barometer"),
    "STEP_COUNTER": ("android.hardware.sensor.stepcounter", "Step counter"),
    "HEART_RATE": ("android.hardware.sensor.heartrate", "Heart-rate sensor"),
}


def get_feature_catalog() -> list:
    """Return the known hardware features (for the settings UI)."""
    return [
        {"key": key, "android": FEATURES[key][0], "description": FEATURES[key][1]}
        for key in FEATURES
    ]


def _resolve(key: str) -> str:
    k = (key or "").strip()
    if k in FEATURES:
        return FEATURES[k][0]
    if k.startswith("android.hardware."):
        return k
    return "android.hardware." + k.lower().replace(" ", "_")


def get_feature_xml(features: list) -> str:
    """Generate <uses-feature> entries.

    Accepts a list of either strings (keys) or dicts {"key", "required"}.
    Defaults to required="false" so the app stays installable on devices that
    lack the hardware.
    """
    lines, seen = [], set()
    for feat in features or []:
        if isinstance(feat, dict):
            key = feat.get("key") or feat.get("name") or ""
            required = bool(feat.get("required", False))
        else:
            key, required = feat, False
        name = _resolve(key)
        if not name or name in seen:
            continue
        seen.add(name)
        req = "true" if required else "false"
        lines.append(f'    <uses-feature android:name={quoteattr(name)} android:required="{req}" />')
    return "\n".join(lines)

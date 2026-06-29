"""
ENPAF Android — Permissions
Android permission constants and helpers.
"""

# Common Android permissions
PERMISSIONS = {
    "INTERNET": "android.permission.INTERNET",
    "ACCESS_NETWORK_STATE": "android.permission.ACCESS_NETWORK_STATE",
    "ACCESS_WIFI_STATE": "android.permission.ACCESS_WIFI_STATE",
    "VIBRATE": "android.permission.VIBRATE",
    "CAMERA": "android.permission.CAMERA",
    "READ_STORAGE": "android.permission.READ_EXTERNAL_STORAGE",
    "WRITE_STORAGE": "android.permission.WRITE_EXTERNAL_STORAGE",
    "READ_MEDIA_IMAGES": "android.permission.READ_MEDIA_IMAGES",
    "READ_MEDIA_VIDEO": "android.permission.READ_MEDIA_VIDEO",
    "READ_MEDIA_AUDIO": "android.permission.READ_MEDIA_AUDIO",
    "FINE_LOCATION": "android.permission.ACCESS_FINE_LOCATION",
    "COARSE_LOCATION": "android.permission.ACCESS_COARSE_LOCATION",
    "BACKGROUND_LOCATION": "android.permission.ACCESS_BACKGROUND_LOCATION",
    "RECORD_AUDIO": "android.permission.RECORD_AUDIO",
    "BODY_SENSORS": "android.permission.BODY_SENSORS",
    "ACTIVITY_RECOGNITION": "android.permission.ACTIVITY_RECOGNITION",
    "READ_CONTACTS": "android.permission.READ_CONTACTS",
    "CALL_PHONE": "android.permission.CALL_PHONE",
    "READ_PHONE_STATE": "android.permission.READ_PHONE_STATE",
    "SEND_SMS": "android.permission.SEND_SMS",
    "RECEIVE_SMS": "android.permission.RECEIVE_SMS",
    "BLUETOOTH": "android.permission.BLUETOOTH",
    "BLUETOOTH_ADMIN": "android.permission.BLUETOOTH_ADMIN",
    "BLUETOOTH_SCAN": "android.permission.BLUETOOTH_SCAN",
    "BLUETOOTH_CONNECT": "android.permission.BLUETOOTH_CONNECT",
    "NFC": "android.permission.NFC",
    "WAKE_LOCK": "android.permission.WAKE_LOCK",
    "FOREGROUND_SERVICE": "android.permission.FOREGROUND_SERVICE",
    "POST_NOTIFICATIONS": "android.permission.POST_NOTIFICATIONS",
    "USE_BIOMETRIC": "android.permission.USE_BIOMETRIC",
    "USE_FINGERPRINT": "android.permission.USE_FINGERPRINT",
    "REQUEST_INSTALL_PACKAGES": "android.permission.REQUEST_INSTALL_PACKAGES",
    "CHANGE_WIFI_STATE": "android.permission.CHANGE_WIFI_STATE",
}


# Human-readable descriptions for the settings UI
PERMISSION_DESCRIPTIONS = {
    "INTERNET": "Network / HTTP access",
    "ACCESS_NETWORK_STATE": "Read network connectivity state",
    "ACCESS_WIFI_STATE": "Read Wi-Fi connection state",
    "VIBRATE": "Vibrate the device",
    "CAMERA": "Use the camera",
    "READ_STORAGE": "Read files from shared storage",
    "WRITE_STORAGE": "Write files to shared storage",
    "READ_MEDIA_IMAGES": "Read images (Android 13+)",
    "READ_MEDIA_VIDEO": "Read videos (Android 13+)",
    "READ_MEDIA_AUDIO": "Read audio files (Android 13+)",
    "FINE_LOCATION": "Precise (GPS) location",
    "COARSE_LOCATION": "Approximate (network) location",
    "BACKGROUND_LOCATION": "Location in the background",
    "RECORD_AUDIO": "Record audio / microphone",
    "BODY_SENSORS": "Body sensors (heart rate)",
    "ACTIVITY_RECOGNITION": "Step counter / activity recognition",
    "READ_CONTACTS": "Read the contact list",
    "CALL_PHONE": "Place phone calls",
    "READ_PHONE_STATE": "Read phone state",
    "SEND_SMS": "Send SMS messages",
    "RECEIVE_SMS": "Receive SMS messages",
    "BLUETOOTH": "Use Bluetooth (legacy)",
    "BLUETOOTH_ADMIN": "Manage Bluetooth (legacy)",
    "BLUETOOTH_SCAN": "Scan for Bluetooth devices (Android 12+)",
    "BLUETOOTH_CONNECT": "Connect to Bluetooth devices (Android 12+)",
    "NFC": "Use NFC",
    "WAKE_LOCK": "Keep the device awake",
    "FOREGROUND_SERVICE": "Run a foreground service",
    "POST_NOTIFICATIONS": "Show notifications (Android 13+)",
    "USE_BIOMETRIC": "Biometric authentication (fingerprint/face)",
    "USE_FINGERPRINT": "Fingerprint authentication (legacy)",
    "REQUEST_INSTALL_PACKAGES": "Install APK packages",
    "CHANGE_WIFI_STATE": "Change Wi-Fi state / connect",
}

# Permissions that are "dangerous" (must be granted at runtime, not just
# declared). Used by the settings UI to flag which ones need a runtime prompt.
RUNTIME_PERMISSIONS = {
    "CAMERA", "READ_STORAGE", "WRITE_STORAGE", "READ_MEDIA_IMAGES",
    "READ_MEDIA_VIDEO", "READ_MEDIA_AUDIO", "FINE_LOCATION", "COARSE_LOCATION",
    "BACKGROUND_LOCATION", "RECORD_AUDIO", "BODY_SENSORS", "ACTIVITY_RECOGNITION",
    "READ_CONTACTS", "CALL_PHONE", "READ_PHONE_STATE", "SEND_SMS", "RECEIVE_SMS",
    "BLUETOOTH_SCAN", "BLUETOOTH_CONNECT", "POST_NOTIFICATIONS",
}


def get_permission_catalog() -> list:
    """Return the known permissions with descriptions (for the settings UI)."""
    return [
        {
            "key": key,
            "android": PERMISSIONS[key],
            "description": PERMISSION_DESCRIPTIONS.get(key, ""),
            "runtime": key in RUNTIME_PERMISSIONS,
        }
        for key in PERMISSIONS
    ]


def resolve_permissions(permission_list: list) -> list:
    """
    Convert short permission names to full Android permission strings.
    
    Args:
        permission_list: List of permission names (e.g., ["INTERNET", "VIBRATE"])
        
    Returns:
        List of full Android permission strings
    """
    resolved = []
    for perm in permission_list:
        perm_upper = perm.upper().replace(".", "_")
        if perm_upper in PERMISSIONS:
            resolved.append(PERMISSIONS[perm_upper])
        elif perm.startswith("android.permission."):
            resolved.append(perm)
        else:
            resolved.append(f"android.permission.{perm_upper}")
    return resolved


class PermissionsManager:
    """Runtime-permission module: check and request permissions on demand.

    Reachable from JS as enpaf.permissions.* and from Python as app.permissions.
    Delegates to DeviceAPI (which has the Android + dev-stub implementations).
    """

    NAME = "permissions"
    _ALLOWED = {"check", "check_all", "request", "catalog"}

    def __init__(self, app):
        self._app = app
        self._api = getattr(app, "api", None)

    def invoke(self, method, args=None):
        if method not in self._ALLOWED:
            raise ValueError(f"permissions: unknown method {method!r}")
        return getattr(self, method)(**(args or {}))

    def check(self, permission="", **_):
        return self._api.check_permission(permission)

    def check_all(self, permissions=None, **_):
        return self._api.check_permissions(permissions or [])

    def request(self, permissions=None, **_):
        return self._api.request_permissions(permissions or [])

    def catalog(self, **_):
        return {"permissions": get_permission_catalog()}


def get_permission_xml(permission_list: list) -> str:
    """
    Generate AndroidManifest.xml permission entries.
    
    Args:
        permission_list: List of permission names
        
    Returns:
        XML string with <uses-permission> elements
    """
    resolved = resolve_permissions(permission_list)
    lines = []
    for perm in resolved:
        lines.append(f'    <uses-permission android:name="{perm}" />')
    return "\n".join(lines)

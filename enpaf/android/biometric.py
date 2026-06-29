"""
ENPAF Android — Biometric module
Fingerprint / face / device-credential authentication via the system
BiometricPrompt. The native prompt + its (abstract) callback live in Java
(MainActivity.authenticateBiometric); Python just starts it and re-emits the
result as the `biometric_result` event.

Usage:
    JS:     const r = await enpaf.biometric.authenticate({ title: "Unlock" });
            if (r.success) { ... }
    Python: app.biometric.authenticate(title="Unlock")
            @app.on("biometric_result")
            def _(d): print(d["success"])

No third-party imports at module top level — this file is bundled into the APK.
"""

from enpaf.android.manager import Manager


class BiometricManager(Manager):
    NAME = "biometric"
    _ALLOWED = {"available", "authenticate"}

    def available(self, **_):
        """Whether biometric (or device-credential) auth can be used.

        Returns {available, code}. code follows BiometricManager: 0 = success,
        11 = none enrolled, 12 = no hardware, ...
        """
        if not self._is_android:
            return {"available": True, "dev": True, "enrolled": True, "code": 0}
        try:
            activity = getattr(self._app.api, "_activity", None)
            if activity is None:
                return {"available": False, "error": "no activity"}
            code = int(activity.canAuthenticateBiometric())
            return {"available": code == 0, "code": code,
                    "enrolled": code != 11}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def authenticate(self, title="Authenticate", subtitle="", description="", **_):
        """Show the system biometric prompt.

        Returns immediately with {started: bool}; the final outcome arrives as
        the `biometric_result` event ({success, error}). The JS helper
        enpaf.biometric.authenticate() wraps this into a Promise.
        """
        if not self._is_android:
            self._fire("biometric_result", {"success": True, "dev": True})
            return {"started": True, "dev": True, "success": True}
        try:
            activity = getattr(self._app.api, "_activity", None)
            if activity is None:
                return {"started": False, "error": "no activity"}
            activity.authenticateBiometric(str(title), str(subtitle), str(description))
            return {"started": True}
        except Exception as e:
            return {"started": False, "error": str(e)}

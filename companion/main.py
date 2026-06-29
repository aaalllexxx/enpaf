"""
ENPAF Companion — Python backend
The "loader": downloads a dev-built APK over the local network and installs it
silently via the PackageInstaller API (no browser, no file picker).
"""

import os
import threading
import urllib.request

from enpaf.core.app import EnpafApp

app = EnpafApp(__name__)


def _emit(event, data=None):
    """Send an event to the UI (reaches JS — app.events.emit alone does not)."""
    app.emit(event, data or {})


@app.bridge_handler("can_install")
def can_install(payload):
    """Whether the app may install packages (Android 8+ requires a per-app grant)."""
    if not app.api._is_android:
        return {"can_install": True, "dev": True}
    try:
        from android.os import Build
        activity = app.api._activity
        if Build.VERSION.SDK_INT >= 26:
            return {"can_install": bool(activity.getPackageManager().canRequestPackageInstalls())}
        return {"can_install": True}
    except Exception as e:
        return {"can_install": False, "error": str(e)}


@app.bridge_handler("request_install_permission")
def request_install_permission(payload):
    """Open the "allow install from this source" settings screen."""
    if not app.api._is_android:
        return {"ok": True, "dev": True}
    try:
        from android.content import Intent
        from android.net import Uri
        from android.provider import Settings
        activity = app.api._activity
        intent = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES)
        intent.setData(Uri.parse("package:" + activity.getPackageName()))
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        activity.startActivity(intent)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.bridge_handler("install_apk")
def install_apk(payload):
    """Download an APK from `url` and hand it to the system installer.

    Progress + lifecycle are reported via events: download_start,
    download_progress {percent, downloaded, total}, download_complete,
    install_prompt (installer opened), install_error {error}.
    """
    url = payload.get("url")
    if not url:
        return {"ok": False, "error": "No URL provided"}

    if not app.api._is_android:
        # Dev: simulate a download so the UI can be tested on desktop.
        def sim():
            import time
            _emit("download_start", {"total": 100})
            for p in range(0, 101, 20):
                time.sleep(0.25)
                _emit("download_progress", {"percent": p, "downloaded": p, "total": 100})
            _emit("download_complete", {})
            _emit("install_prompt", {"dev": True})
        threading.Thread(target=sim, daemon=True).start()
        return {"ok": True, "dev": True}

    def download_and_install():
        session = None
        try:
            from android.content import Intent
            from android.content.pm import PackageInstaller
            from android.app import PendingIntent
            from android.net import Uri
            from android.os import Build
            from android.provider import Settings

            activity = app.api._activity
            pm = activity.getPackageManager()

            # Android 8+: need per-source install permission first.
            if Build.VERSION.SDK_INT >= 26 and not pm.canRequestPackageInstalls():
                app.api.toast("Allow ENPAF to install apps, then tap Install again", "long")
                intent = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES)
                intent.setData(Uri.parse("package:" + activity.getPackageName()))
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                activity.startActivity(intent)
                _emit("install_error", {"error": "install_permission_required"})
                return

            _emit("download_start", {})
            app.api.toast("Downloading APK…", "short")

            pi = pm.getPackageInstaller()
            params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL)
            session_id = pi.createSession(params)
            session = pi.openSession(session_id)

            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = int(resp.getheader("Content-Length", "0"))
                out = session.openWrite("package", 0, total if total > 0 else -1)
                downloaded = 0
                last_pct = -1
                while True:
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = int(downloaded / total * 100)
                        if pct != last_pct:
                            last_pct = pct
                            _emit("download_progress",
                                  {"percent": pct, "downloaded": downloaded, "total": total})
                session.fsync(out)
                out.close()

            _emit("download_complete", {"bytes": downloaded})
            app.api.toast("Download complete — opening installer…", "short")

            intent = Intent(activity, activity.getClass())
            intent.setAction("com.enpaf.companion.INSTALL_COMPLETE")
            intent.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
            flags = PendingIntent.FLAG_UPDATE_CURRENT
            if Build.VERSION.SDK_INT >= 31:
                flags |= getattr(PendingIntent, "FLAG_MUTABLE", 33554432)
            pi_intent = PendingIntent.getActivity(activity, 0, intent, flags)
            session.commit(pi_intent.getIntentSender())
            session.close()
            _emit("install_prompt", {})

        except Exception as e:
            try:
                if session is not None:
                    session.abandon()
            except Exception:
                pass
            app.api.toast(f"Install failed: {e}")
            _emit("install_error", {"error": str(e)})
            import traceback
            traceback.print_exc()

    threading.Thread(target=download_and_install, daemon=True).start()
    return {"ok": True}


# Start the application
app.run()

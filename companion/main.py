"""
ENPAF Companion — Python backend
The "loader": downloads a dev-built APK over the local network and installs it
silently via the PackageInstaller API (no browser, no file picker).
"""

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


@app.bridge_handler("probe_url")
def probe_url(payload):
    """HEAD a URL and return real headers (status, size, Last-Modified, ETag) +
    round-trip ms. Used by the connection tester and the auto-reload watcher —
    JS fetch(no-cors) cannot read these, but Python can.
    """
    import time
    url = payload.get("url")
    if not url:
        return {"ok": False, "error": "no url"}
    if not app.api._is_android:
        return {"ok": True, "status": 200, "length": 36_700_000,
                "last_modified": "dev", "etag": "dev", "ms": 11, "dev": True}

    def _len(v):
        if not v:
            return 0
        v = str(v)
        if "/" in v:                       # Content-Range: bytes 0-0/12345
            v = v.split("/")[-1]
        try:
            return int(v)
        except ValueError:
            return 0

    try:
        t0 = time.time()
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=6) as r:
            return {"ok": True, "status": getattr(r, "status", 200),
                    "length": _len(r.getheader("Content-Length")),
                    "last_modified": r.getheader("Last-Modified") or "",
                    "etag": r.getheader("ETag") or "",
                    "ms": int((time.time() - t0) * 1000)}
    except Exception:
        # Some static servers reject HEAD — fall back to a 1-byte ranged GET.
        try:
            t0 = time.time()
            req = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
            with urllib.request.urlopen(req, timeout=6) as r:
                return {"ok": True, "status": getattr(r, "status", 200),
                        "length": _len(r.getheader("Content-Range") or r.getheader("Content-Length")),
                        "last_modified": r.getheader("Last-Modified") or "",
                        "etag": r.getheader("ETag") or "",
                        "ms": int((time.time() - t0) * 1000)}
        except Exception as e:
            return {"ok": False, "error": str(e)}


@app.bridge_handler("diag_info")
def diag_info(payload):
    """A development environment report for this device: Android/API, model,
    ABI, screen, RAM, storage, WebView version, install permission."""
    out = {}
    try:
        out.update(app.api.get_device_info() or {})
    except Exception:
        pass

    if not app.api._is_android:
        out.update({"dev": True, "manufacturer": "Dev", "model": "Desktop",
                    "android": "—", "api_level": 34, "abi": "x86_64",
                    "ram_total": 8 * 10**9, "ram_avail": 4 * 10**9,
                    "storage_total": 256 * 10**9, "storage_free": 64 * 10**9,
                    "webview": "—", "can_install": True})
        return out

    try:
        from android.os import Build
        out["manufacturer"] = str(Build.MANUFACTURER)
        out["model"] = str(Build.MODEL)
        out["android"] = str(Build.VERSION.RELEASE)
        out["api_level"] = int(Build.VERSION.SDK_INT)
        out["abi"] = ", ".join(str(a) for a in Build.SUPPORTED_ABIS)
    except Exception as e:
        out["build_err"] = str(e)

    ctx = app.api._activity
    try:
        from android.content import Context
        from android.app import ActivityManager
        am = ctx.getSystemService(Context.ACTIVITY_SERVICE)
        mi = ActivityManager.MemoryInfo()
        am.getMemoryInfo(mi)
        out["ram_total"] = int(mi.totalMem)
        out["ram_avail"] = int(mi.availMem)
    except Exception as e:
        out["ram_err"] = str(e)

    try:
        from android.os import StatFs, Environment
        sf = StatFs(Environment.getDataDirectory().getPath())
        out["storage_total"] = int(sf.getTotalBytes())
        out["storage_free"] = int(sf.getAvailableBytes())
    except Exception as e:
        out["storage_err"] = str(e)

    try:
        from android.webkit import WebView
        pkg = WebView.getCurrentWebViewPackage()
        if pkg is not None:
            out["webview"] = str(pkg.versionName)
    except Exception as e:
        out["webview_err"] = str(e)

    try:
        from android.os import Build as _B
        if _B.VERSION.SDK_INT >= 26:
            out["can_install"] = bool(ctx.getPackageManager().canRequestPackageInstalls())
        else:
            out["can_install"] = True
    except Exception:
        pass

    return out


# Start the application
app.run()

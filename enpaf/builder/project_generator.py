"""
ENPAF Builder — Android Project Generator
Generates all files for the Gradle/Chaquopy Android project.
"""

import os
import shutil
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from xml.sax.saxutils import escape

from enpaf.android.permissions import get_permission_xml
from enpaf.android.deeplinks import get_deeplink_xml
from enpaf.android.features import get_feature_xml


def safe_copy(src: str, dst: str) -> None:
    """copy2 that first clears a read-only/cloud-placeholder destination.

    On Windows, files synced by OneDrive ('Files On-Demand') become read-only
    reparse points; opening them for overwrite raises WinError 5. Clearing the
    read-only bit beforehand lets rebuilds overwrite them.
    """
    if os.path.exists(dst):
        try:
            os.chmod(dst, stat.S_IWRITE)
        except OSError:
            pass
    shutil.copy2(src, dst)


def safe_rmtree(path: str, retries: int = 3) -> None:
    """Recursively delete *path*, tolerating Windows read-only files and
    OneDrive cloud placeholders that otherwise raise WinError 5 (Access Denied).
    """
    if not os.path.exists(path):
        return

    def _handle(func, target, _exc):
        try:
            os.chmod(target, stat.S_IWRITE)
        except OSError:
            pass
        func(target)

    for attempt in range(retries):
        try:
            if sys.version_info >= (3, 12):
                shutil.rmtree(path, onexc=_handle)
            else:
                shutil.rmtree(path, onerror=lambda f, p, _e: _handle(f, p, _e))
            return
        except OSError:
            if attempt == retries - 1:
                raise
            time.sleep(0.3)


class ProjectGenerator:
    """Generates a complete Android project structure with Gradle + Chaquopy."""

    CHAQUOPY_VERSION = "15.0.1"
    COMPILE_SDK = 34
    MIN_SDK = 24
    TARGET_SDK = 34
    GRADLE_VERSION = "8.4"

    def __init__(self, project_dir: str, config: dict, output_dir: str,
                 release: bool = False, keystore_path: str = None):
        self.project_dir = project_dir
        self.config = config
        self.output_dir = output_dir
        # Release builds must be signed or Android refuses to install them.
        self.release = release
        self.keystore_path = keystore_path

    def generate(self):
        """Generate the entire Android project."""
        package = self.config.get("package", "com.enpaf.app")
        package_path = package.replace(".", os.sep)
        app_name = self.config.get("name", "ENPAF App")
        version = self.config.get("version", "1.0.0")
        min_sdk = self.config.get("min_sdk", self.MIN_SDK)
        target_sdk = self.config.get("target_sdk", self.TARGET_SDK)
        permissions = self.config.get("permissions", ["INTERNET"])
        features = self.config.get("features", [])
        deeplinks = self.config.get("deeplinks", [])
        orientation = self.config.get("orientation", "portrait")
        py_requirements = self.config.get("python_requirements", [])
        theme = self.config.get("theme", {})
        primary_color = theme.get("primary_color", "#6C5CE7")
        status_bar_color = theme.get("status_bar_color", primary_color)

        # Create directories
        dirs = [
            f"app/src/main/java/{package_path}",
            "app/src/main/assets/www/css",
            "app/src/main/assets/www/js",
            "app/src/main/assets/www/img",
            "app/src/main/python/enpaf/core",
            "app/src/main/python/enpaf/android",
            "app/src/main/res/values",
            "app/src/main/res/layout",
            "app/src/main/res/drawable",
            "gradle/wrapper",
        ]
        for d in dirs:
            os.makedirs(os.path.join(self.output_dir, d), exist_ok=True)

        signing = self._signing_config() if self.release else None

        self._copy_web_files()
        self._copy_python_files()
        icon_res = self._copy_icon()
        self._write_settings_gradle()
        self._write_root_build_gradle()
        self._write_app_build_gradle(package, min_sdk, target_sdk, version,
                                     py_requirements, signing)
        self._write_manifest(package, app_name, permissions, features, deeplinks,
                             orientation, icon_res)
        self._write_main_activity(package, primary_color, status_bar_color)
        self._write_resources(app_name, primary_color)
        self._write_gradle_wrapper()
        self._write_gradle_properties()

    def _w(self, rel_path: str, content: str):
        """Write a file relative to output_dir."""
        path = os.path.join(self.output_dir, rel_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # A previous build may have left this file read-only (OneDrive sync),
        # which would make open("w") fail with WinError 5 on Windows.
        if os.path.exists(path):
            try:
                os.chmod(path, stat.S_IWRITE)
            except OSError:
                pass
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _copy_web_files(self):
        """Copy app/ HTML/CSS/JS to Android assets."""
        app_dir = os.path.join(self.project_dir, "app")
        assets_www = os.path.join(self.output_dir, "app/src/main/assets/www")
        if os.path.isdir(app_dir):
            for item in os.listdir(app_dir):
                src = os.path.join(app_dir, item)
                dst = os.path.join(assets_www, item)
                if os.path.isdir(src):
                    # Merge into the existing tree instead of rmtree+copytree:
                    # deleting OneDrive cloud placeholders raises WinError 5.
                    shutil.copytree(src, dst, dirs_exist_ok=True, copy_function=safe_copy)
                else:
                    safe_copy(src, dst)

        # Copy enpaf.js bridge
        try:
            from enpaf_bridge import bridge_js_path
            bridge_src = bridge_js_path()
        except Exception:
            bridge_src = os.path.normpath(os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "..", "enpaf_bridge", "enpaf.js"
            ))
        if os.path.isfile(bridge_src):
            safe_copy(bridge_src, os.path.join(assets_www, "js", "enpaf.js"))

        self._inject_bridge_into_assets(assets_www)

    def _inject_bridge_into_assets(self, assets_www: str):
        """Inject <script src=".../js/enpaf.js"> into every bundled HTML page.

        In dev mode the server injects the bridge at request time; inside the APK
        nothing does, so without this the page has no `enpaf` object and any
        enpaf.call(...) fails with 'enpaf is not defined'.
        """
        for root, _dirs, files in os.walk(assets_www):
            for fn in files:
                if not fn.lower().endswith((".html", ".htm")):
                    continue
                path = os.path.join(root, fn)
                with open(path, "r", encoding="utf-8") as f:
                    html = f.read()
                if "js/enpaf.js" in html:
                    continue  # already references the bridge
                rel = os.path.relpath(assets_www, root).replace(os.sep, "/")
                prefix = "" if rel == "." else rel + "/"
                tag = f'<script src="{prefix}js/enpaf.js"></script>'
                low = html.lower()
                if "</head>" in low:
                    i = low.index("</head>")
                    html = html[:i] + "    " + tag + "\n" + html[i:]
                elif "<body" in low:
                    i = low.index("<body")
                    j = html.index(">", i) + 1
                    html = html[:j] + "\n    " + tag + html[j:]
                else:
                    html = tag + "\n" + html
                if os.path.exists(path):
                    try:
                        os.chmod(path, stat.S_IWRITE)
                    except OSError:
                        pass
                with open(path, "w", encoding="utf-8") as f:
                    f.write(html)

    def _copy_icon(self):
        """Install the configured app icon as a proper **adaptive icon**.

        A plain bitmap set as android:icon gets wrapped by Android 8+ launchers
        into an adaptive icon with a white background + insets (the "white
        edges" users see). Instead we generate an adaptive icon that uses the
        image full-bleed as the background, so it fills the launcher shape with
        no white frame, plus a legacy bitmap fallback for Android 7 (API 24-25).

        Returns the manifest android:icon reference or None.
        """
        icon = self.config.get("icon")
        if not icon:
            return None
        src = icon if os.path.isabs(icon) else os.path.join(self.project_dir, icon)
        if not os.path.isfile(src):
            return None
        ext = os.path.splitext(src)[1].lower()
        if ext not in (".png", ".jpg", ".jpeg", ".webp"):
            return None
        # Trust the file's real content, not its name. An icon named ".png" that
        # is actually a JPEG makes AAPT's PNG cruncher fail ("file failed to
        # compile"). Sniff the magic bytes and store the bitmap under the
        # extension that matches its actual format.
        dst_ext = self._image_ext(src) or (".jpg" if ext == ".jpeg" else ext)
        res = os.path.join(self.output_dir, "app", "src", "main", "res")

        # 1) full-bleed source as a drawable (adaptive-icon background layer)
        draw = os.path.join(res, "drawable", "app_icon" + dst_ext)
        os.makedirs(os.path.dirname(draw), exist_ok=True)
        safe_copy(src, draw)

        # 2) legacy launcher bitmaps for Android < 8 (one hi-density bucket is
        #    enough — the system downscales it for lower-density screens).
        leg = os.path.join(res, "mipmap-xxxhdpi")
        os.makedirs(leg, exist_ok=True)
        safe_copy(src, os.path.join(leg, "ic_launcher" + dst_ext))
        safe_copy(src, os.path.join(leg, "ic_launcher_round" + dst_ext))

        # 3) adaptive icons for Android 8+ — image full-bleed, no white frame.
        adaptive = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '    <background android:drawable="@drawable/app_icon"/>\n'
            '    <foreground android:drawable="@android:color/transparent"/>\n'
            '</adaptive-icon>\n'
        )
        self._w("app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml", adaptive)
        self._w("app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml", adaptive)
        return "@mipmap/ic_launcher"

    @staticmethod
    def _image_ext(path):
        """Return the real image extension ('.png' / '.jpg' / '.webp') sniffed
        from the file's magic bytes, or None if it isn't a recognised bitmap."""
        try:
            with open(path, "rb") as f:
                head = f.read(12)
        except OSError:
            return None
        if head.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"
        if head.startswith(b"\xff\xd8\xff"):
            return ".jpg"
        if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            return ".webp"
        return None

    def _copy_python_files(self):
        """Copy Python source files for Android runtime."""
        py_dir = os.path.join(self.output_dir, "app/src/main/python")
        main_py = os.path.join(self.project_dir, "main.py")
        if os.path.isfile(main_py):
            safe_copy(main_py, os.path.join(py_dir, "main.py"))

        # Copy enpaf runtime modules
        enpaf_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        core_src = os.path.join(enpaf_src, "core")
        android_src = os.path.join(enpaf_src, "android")
        enpaf_rt = os.path.join(py_dir, "enpaf")

        for mod in ["__init__.py", "app.py", "bridge.py", "events.py", "storage.py", "router.py", "api.py"]:
            src = os.path.join(core_src, mod)
            if os.path.isfile(src):
                safe_copy(src, os.path.join(enpaf_rt, "core", mod))

        # Bundle every android/*.py module (bluetooth, wifi, sensors, location,
        # nfc, audio, battery, notifications, device, manager, permissions, …).
        # They only import android/java lazily, so this is safe to ship as-is.
        if os.path.isdir(android_src):
            for fn in os.listdir(android_src):
                if fn.endswith(".py"):
                    safe_copy(os.path.join(android_src, fn),
                              os.path.join(enpaf_rt, "android", fn))

        self._w("app/src/main/python/enpaf/__init__.py",
                '__version__="1.0.0"\nfrom enpaf.core.app import EnpafApp\n')

    def _write_settings_gradle(self):
        self._w("settings.gradle", '''pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
        maven { url "https://chaquo.com/maven" }
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "enpaf-app"
include ':app'
''')

    def _write_root_build_gradle(self):
        self._w("build.gradle", f'''plugins {{
    id 'com.android.application' version '8.2.0' apply false
    id 'com.chaquo.python' version '{self.CHAQUOPY_VERSION}' apply false
}}
''')

    def _write_app_build_gradle(self, package, min_sdk, target_sdk, version, py_reqs, signing=None):
        parts = version.split(".")
        vc = int(parts[0]) * 10000 + int(parts[1] if len(parts) > 1 else 0) * 100 + int(parts[2] if len(parts) > 2 else 0)
        pip = ""
        if py_reqs:
            pip = "\n        pip {\n" + "\n".join(f'            install "{r}"' for r in py_reqs) + "\n        }"

        # Sign the release so it installs. minifyEnabled stays off so R8 can't
        # strip the @JavascriptInterface bridge or Chaquopy's Python classes.
        signing_block = ""
        release_signing = ""
        if signing:
            store = signing["path"].replace("\\", "/")
            signing_block = f'''
    signingConfigs {{
        release {{
            storeFile file("{store}")
            storePassword "{signing['store_password']}"
            keyAlias "{signing['key_alias']}"
            keyPassword "{signing['key_password']}"
        }}
    }}'''
            release_signing = "\n            signingConfig signingConfigs.release"

        self._w("app/build.gradle", f'''plugins {{
    id 'com.android.application'
    id 'com.chaquo.python'
}}
android {{
    namespace "{package}"
    compileSdk {self.COMPILE_SDK}
    defaultConfig {{
        applicationId "{package}"
        minSdk {min_sdk}
        targetSdk {target_sdk}
        versionCode {vc}
        versionName "{version}"
        python {{
            version "3.11"{pip}
        }}
        ndk {{ abiFilters "arm64-v8a", "x86_64" }}
    }}{signing_block}
    buildTypes {{
        release {{
            minifyEnabled false{release_signing}
        }}
        debug {{ minifyEnabled false; debuggable true }}
    }}
    compileOptions {{
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }}
    sourceSets {{ main {{ python.srcDirs = ["src/main/python"] }} }}
}}
dependencies {{
    implementation 'androidx.core:core:1.12.0'
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'androidx.webkit:webkit:1.8.0'
    implementation 'com.google.android.material:material:1.10.0'
}}
''')

    def _write_manifest(self, package, app_name, permissions, features=None,
                        deeplinks=None, orientation="portrait", icon_res=None):
        perm_xml = get_permission_xml(permissions)
        feature_xml = get_feature_xml(features or [])
        deeplink_xml = get_deeplink_xml(deeplinks or [])
        decls = "\n".join(b for b in [perm_xml, feature_xml] if b)
        if icon_res:
            icon_attr = (f'\n        android:icon="{icon_res}"'
                         '\n        android:roundIcon="@mipmap/ic_launcher_round"')
        else:
            icon_attr = ""
        screen = self._orientation_attr(orientation)
        self._w("app/src/main/AndroidManifest.xml", f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
{decls}
    <application
        android:allowBackup="true"
        android:label="@string/app_name"{icon_attr}
        android:supportsRtl="true"
        android:theme="@style/Theme.EnpafApp"
        android:usesCleartextTraffic="true"
        android:name="com.chaquo.python.android.PyApplication">
        <activity android:name=".MainActivity" android:exported="true"{screen}
            android:configChanges="orientation|screenSize|keyboardHidden"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>{deeplink_xml}
        </activity>
    </application>
</manifest>
''')

    def _orientation_attr(self, orientation: str) -> str:
        mapping = {
            "portrait": "portrait", "landscape": "landscape",
            "auto": "fullUser", "sensor": "fullSensor", "unspecified": "unspecified",
        }
        val = mapping.get((orientation or "").lower())
        return f'\n            android:screenOrientation="{val}"' if val else ""

    def _write_main_activity(self, package, primary_color, status_bar_color=None):
        pkg_path = package.replace(".", os.sep)
        self._w(f"app/src/main/java/{pkg_path}/MainActivity.java",
                _MAIN_ACTIVITY_TEMPLATE.replace("{{PACKAGE}}", package)
                .replace("{{PRIMARY_COLOR}}", primary_color)
                .replace("{{STATUS_BAR_COLOR}}", status_bar_color or primary_color))

    def _write_resources(self, app_name, primary_color):
        self._w("app/src/main/res/values/colors.xml", f'''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="primary">{primary_color}</color>
    <color name="primary_dark">{primary_color}</color>
    <color name="accent">{primary_color}</color>
</resources>
''')
        self._w("app/src/main/res/values/strings.xml", f'''<?xml version="1.0" encoding="utf-8"?>
<resources><string name="app_name">{escape(app_name)}</string></resources>
''')
        self._w("app/src/main/res/values/themes.xml", '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.EnpafApp" parent="android:Theme.Material.Light.NoActionBar">
        <item name="android:colorPrimary">@color/primary</item>
        <item name="android:colorPrimaryDark">@color/primary_dark</item>
        <item name="android:colorAccent">@color/accent</item>
    </style>
</resources>
''')

    def _write_gradle_wrapper(self):
        self._w("gradle/wrapper/gradle-wrapper.properties",
                "distributionBase=GRADLE_USER_HOME\n"
                "distributionPath=wrapper/dists\n"
                f"distributionUrl=https\\://services.gradle.org/distributions/gradle-{self.GRADLE_VERSION}-bin.zip\n"
                "networkTimeout=10000\n"
                "validateDistributionUrl=true\n"
                "zipStoreBase=GRADLE_USER_HOME\n"
                "zipStorePath=wrapper/dists\n")

        # Fetch the OFFICIAL wrapper bootstrap. The previous hand-written
        # gradlew.bat referenced an unset %JAVA_EXE% (-> '""' is not recognized)
        # and no gradle-wrapper.jar was ever produced, so the build could never
        # start. The official scripts locate Java via JAVA_HOME or PATH, and the
        # jar bootstraps the Gradle distribution named in the properties file.
        tag = self._wrapper_tag()
        base = "https://raw.githubusercontent.com/gradle/gradle/" + tag + "/"
        downloads = {
            "gradle/wrapper/gradle-wrapper.jar": base + "gradle/wrapper/gradle-wrapper.jar",
            "gradlew.bat": base + "gradlew.bat",
            "gradlew": base + "gradlew",
        }
        for rel, url in downloads.items():
            dst = os.path.join(self.output_dir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst):
                try:
                    os.chmod(dst, stat.S_IWRITE)
                except OSError:
                    pass
            try:
                urllib.request.urlretrieve(url, dst)
            except (urllib.error.URLError, OSError) as e:
                raise RuntimeError(
                    f"Could not download Gradle wrapper file '{rel}'. "
                    f"Check your internet connection and try again. ({e})"
                )

        gw = os.path.join(self.output_dir, "gradlew")
        try:
            os.chmod(gw, os.stat(gw).st_mode | stat.S_IEXEC)
        except Exception:
            pass

    def _wrapper_tag(self) -> str:
        """GitHub release tag for the wrapper version (e.g. '8.4' -> 'v8.4.0')."""
        parts = self.GRADLE_VERSION.split(".")
        while len(parts) < 3:
            parts.append("0")
        return "v" + ".".join(parts)

    def _write_gradle_properties(self):
        self._w("gradle.properties", "org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8\nandroid.useAndroidX=true\n")

    # ─── Release signing ──────────────────────────────────────

    def _signing_config(self):
        """Return signing info for the release build, creating a keystore if
        needed. An unsigned release APK cannot be installed, so we always sign:
        either with a keystore from enpaf.json (`signing`) / --keystore, or with
        an auto-generated per-app keystore kept in ~/.enpaf/keystores.

        Returns a dict {path, store_password, key_alias, key_password} or None
        if no keystore could be produced (keytool missing).
        """
        package = self.config.get("package", "com.enpaf.app")
        sign = self.config.get("signing") or {}
        path = self.keystore_path or sign.get("keystore")
        store_pw = str(sign.get("store_password", "enpaf123"))
        alias = str(sign.get("key_alias", "enpaf"))
        key_pw = str(sign.get("key_password", store_pw))

        if not path:
            home = os.path.join(os.path.expanduser("~"), ".enpaf", "keystores")
            try:
                os.makedirs(home, exist_ok=True)
            except OSError:
                pass
            path = os.path.join(home, package + ".jks")
        path = os.path.abspath(path)

        if not os.path.isfile(path):
            if not self._create_keystore(path, store_pw, alias, key_pw):
                print("  ! Could not create a signing keystore (keytool not found). "
                      "Release APK will be unsigned and may not install.")
                return None
            print(f"  + Generated release keystore: {path}")

        return {"path": path, "store_password": store_pw,
                "key_alias": alias, "key_password": key_pw}

    def _find_keytool(self):
        """Locate keytool from JAVA_HOME (pinned by the build) or PATH."""
        exe = "keytool.exe" if os.name == "nt" else "keytool"
        home = os.environ.get("JAVA_HOME")
        if home:
            cand = os.path.join(home, "bin", exe)
            if os.path.isfile(cand):
                return cand
        return shutil.which("keytool")

    def _create_keystore(self, path, store_pw, alias, key_pw):
        """Create a self-signed RSA keystore with keytool. Returns True on success."""
        keytool = self._find_keytool()
        if not keytool:
            return False
        name = self.config.get("name", "ENPAF App")
        dname = f"CN={name}, OU=ENPAF, O=ENPAF, C=US"
        cmd = [
            keytool, "-genkeypair", "-noprompt",
            "-keystore", path, "-alias", alias,
            "-storepass", store_pw, "-keypass", key_pw,
            "-keyalg", "RSA", "-keysize", "2048",
            "-validity", "10000", "-dname", dname,
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=120)
            if r.returncode != 0:
                print("  ! keytool error:", (r.stderr or r.stdout or "").strip()[:300])
            return r.returncode == 0 and os.path.isfile(path)
        except Exception as e:
            print(f"  ! keytool failed: {e}")
            return False


# ─── MainActivity.java Template ──────────────────────────────

_MAIN_ACTIVITY_TEMPLATE = r'''package {{PACKAGE}};

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.graphics.Color;
import android.nfc.NfcAdapter;
import android.nfc.Tag;
import android.os.Build;
import android.os.Bundle;
import android.os.Vibrator;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.*;
import android.widget.Toast;
import android.content.*;
import android.content.pm.ActivityInfo;
import android.content.pm.PackageManager;
import android.net.Uri;

import androidx.core.app.ActivityCompat;
import androidx.core.app.NotificationCompat;
import androidx.core.content.ContextCompat;

import com.chaquo.python.*;
import com.chaquo.python.android.AndroidPlatform;

public class MainActivity extends Activity {
    private WebView webView;
    static final String CHANNEL_ID = "enpaf_default";

    // NFC: captured by foreground dispatch, read/written/locked from Python.
    private NfcAdapter nfcAdapter;
    private PendingIntent nfcPendingIntent;
    private volatile Tag lastNfcTag;
    private boolean nfcResumed = false;   // true while foreground dispatch is active

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        instance = this;
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            int barColor = Color.parseColor("{{STATUS_BAR_COLOR}}");
            // Match both system bars to the app so the UI looks frameless.
            getWindow().setStatusBarColor(barColor);
            getWindow().setNavigationBarColor(barColor);
            // On a light bar, switch the system icons to dark so they stay visible.
            double lum = 0.299 * Color.red(barColor) + 0.587 * Color.green(barColor) + 0.114 * Color.blue(barColor);
            if (lum > 150 && Build.VERSION.SDK_INT >= 23) {
                View dv = getWindow().getDecorView();
                int f = dv.getSystemUiVisibility() | View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;
                if (Build.VERSION.SDK_INT >= 26) f |= View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR;
                dv.setSystemUiVisibility(f);
            }
        }

        if (!Python.isStarted()) Python.start(new AndroidPlatform(this));
        Python py = Python.getInstance();
        // Tell the Python app it runs on Android and give it a writable data dir.
        // (The app sources live in a read-only asset location; writing the DB
        // next to them would crash the app on launch.)
        PyObject env = py.getModule("os").get("environ");
        env.callAttr("__setitem__", "ENPAF_ANDROID", "1");
        env.callAttr("__setitem__", "ENPAF_DATA_DIR", getFilesDir().getAbsolutePath());
        createNotificationChannel();
        py.getModule("main"); // init app

        webView = new WebView(this);
        setContentView(webView);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setDatabaseEnabled(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        // Let getUserMedia camera/mic previews autoplay without a user gesture,
        // otherwise the <video> element stays black (e.g. the QR scanner).
        s.setMediaPlaybackRequiresUserGesture(false);
        webView.setWebViewClient(new WebViewClient());
        // Grant in-WebView permission requests (camera/mic for getUserMedia).
        // The app must also hold the CAMERA/RECORD_AUDIO runtime permission.
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(new Runnable() {
                    public void run() { request.grant(request.getResources()); }
                });
            }
        });
        webView.addJavascriptInterface(new Bridge(this, py), "EnpafAndroidBridge");

        // Hand the Activity + WebView to the Python app so it can request
        // runtime permissions on demand and push events back into the WebView.
        // (Permissions are intentionally NOT requested at launch; call
        // enpaf.permissions.request([...]) from your app when you need them.)
        try {
            PyObject app = py.getModule("main").get("app");
            app.callAttr("_attach_android", this, webView);
        } catch (Exception e) { e.printStackTrace(); }

        webView.loadUrl("file:///android_asset/www/index.html");

        // NFC: prepare foreground dispatch so tapped tags reach this app while
        // it is open (no manifest intent-filter needed).
        nfcAdapter = NfcAdapter.getDefaultAdapter(this);
        if (nfcAdapter != null) {
            int piFlags = (Build.VERSION.SDK_INT >= 31) ? PendingIntent.FLAG_MUTABLE : 0;
            Intent ni = new Intent(this, getClass()).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
            nfcPendingIntent = PendingIntent.getActivity(this, 0, ni, piFlags);
        }

        handleIntent(getIntent());
        handleNfcIntent(getIntent(), true);   // true = app launched by this tap
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        try {
            Python py = Python.getInstance();
            PyObject app = py.getModule("main").get("app");
            app.callAttr("_on_permission_result", requestCode, permissions, grantResults);
        } catch (Exception e) { e.printStackTrace(); }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        try {
            Python py = Python.getInstance();
            PyObject app = py.getModule("main").get("app");
            app.callAttr("_on_activity_result", requestCode, resultCode, data);
        } catch (Exception e) { e.printStackTrace(); }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (nfcAdapter != null) {
            try { nfcAdapter.disableForegroundDispatch(this); } catch (Exception e) {}
        }
        try {
            Python py = Python.getInstance();
            PyObject app = py.getModule("main").get("app");
            app.get("events").callAttr("emit", "app_pause");
        } catch (Exception e) {}
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (nfcAdapter != null && nfcPendingIntent != null) {
            try { nfcAdapter.enableForegroundDispatch(this, nfcPendingIntent, null, null); } catch (Exception e) {}
        }
        try {
            Python py = Python.getInstance();
            PyObject app = py.getModule("main").get("app");
            app.get("events").callAttr("emit", "app_resume");
        } catch (Exception e) {}
    }

    @Override public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIntent(intent);
        handleNfcIntent(intent, false);
    }

    /** Capture a tapped NFC tag and notify Python (which forwards a JS event).
     *  fromLaunch is true when this tap cold-started the app (e.g. via an AAR),
     *  letting Python auto-open a URL stored on the tag. */
    private void handleNfcIntent(Intent intent, boolean fromLaunch) {
        if (intent == null) return;
        String action = intent.getAction();
        if (action == null) return;
        if (NfcAdapter.ACTION_NDEF_DISCOVERED.equals(action)
                || NfcAdapter.ACTION_TECH_DISCOVERED.equals(action)
                || NfcAdapter.ACTION_TAG_DISCOVERED.equals(action)) {
            Tag tag = intent.getParcelableExtra(NfcAdapter.EXTRA_TAG);
            if (tag != null) {
                lastNfcTag = tag;
                try {
                    Python py = Python.getInstance();
                    PyObject app = py.getModule("main").get("app");
                    app.callAttr("_on_nfc_tag", bytesToHex(tag.getId()), fromLaunch);
                } catch (Exception e) { e.printStackTrace(); }
            }
        }
    }

    /** Accessor used by Python (DeviceAPI) to read/write/lock the last tag. */
    public Tag getLastNfcTag() { return lastNfcTag; }

    static String bytesToHex(byte[] bytes) {
        if (bytes == null) return "";
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < bytes.length; i++) {
            if (i > 0) sb.append(':');
            sb.append(String.format("%02X", bytes[i] & 0xFF));
        }
        return sb.toString();
    }

    private void handleIntent(Intent intent) {
        if (intent != null) {
            // PackageInstaller result: a normal app must launch the system
            // confirmation UI itself when the status is PENDING_USER_ACTION.
            int piStatus = intent.getIntExtra(android.content.pm.PackageInstaller.EXTRA_STATUS, -999);
            if (piStatus != -999) {
                if (piStatus == android.content.pm.PackageInstaller.STATUS_PENDING_USER_ACTION) {
                    Intent confirm = intent.getParcelableExtra(Intent.EXTRA_INTENT);
                    if (confirm != null) {
                        confirm.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        try { startActivity(confirm); } catch (Exception e) { e.printStackTrace(); }
                    }
                } else {
                    try {
                        Python.getInstance().getModule("main").get("app").callAttr(
                            "_on_install_status", piStatus,
                            intent.getStringExtra(android.content.pm.PackageInstaller.EXTRA_STATUS_MESSAGE));
                    } catch (Exception e) {}
                }
                return;
            }
            String action = intent.getStringExtra("enpaf_action");
            String payload = intent.getStringExtra("enpaf_payload");
            if (action != null || payload != null) {
                try {
                    Python py = Python.getInstance();
                    PyObject app = py.getModule("main").get("app");
                    PyObject jsonLoads = py.getModule("json").get("loads");
                    String dataJson = "{\"action\":\"" + (action != null ? action : "") + "\",\"payload\":\"" + (payload != null ? payload : "") + "\"}";
                    app.get("events").callAttr("emit", "notification_click", jsonLoads.call(dataJson));
                } catch (Exception e) {}
            }
        }
    }

    void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel ch = new NotificationChannel(CHANNEL_ID, "Notifications",
                    NotificationManager.IMPORTANCE_DEFAULT);
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.createNotificationChannel(ch);
        }
    }

    void showNotification(int id, String title, String text) {
        int icon = getApplicationInfo().icon;
        if (icon == 0) icon = android.R.drawable.sym_def_app_icon;
        NotificationCompat.Builder b = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setSmallIcon(icon)
                .setContentTitle(title)
                .setContentText(text)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT);
        NotificationManager nm = getSystemService(NotificationManager.class);
        if (nm != null) nm.notify(id, b.build());
    }

    // Static reference so Python can access the Activity easily.
    private static MainActivity instance;
    public static MainActivity getInstance() { return instance; }

    // Broadcast receivers use a tag to route events in Python.
    public static class EnpafBroadcastReceiver extends BroadcastReceiver {
        private final String tag;
        public EnpafBroadcastReceiver(String tag) { this.tag = tag; }
        @Override
        public void onReceive(Context context, Intent intent) {
            android.util.Log.d("ENPAF", "BroadcastReceiver.onReceive tag=" + tag
                    + " action=" + intent.getAction());
            try {
                Python py = Python.getInstance();
                PyObject app = py.getModule("main").get("app");
                app.callAttr("_on_broadcast_receive", tag, intent);
            } catch (Exception e) {
                android.util.Log.e("ENPAF", "BroadcastReceiver callback error", e);
            }
        }
    }

    /** Create and register an EnpafBroadcastReceiver for the given actions.
     *  Called from Python: activity.registerEnpafReceiver("bt", ["action1","action2"]) */
    public BroadcastReceiver registerEnpafReceiver(String tag, String[] actions) {
        EnpafBroadcastReceiver r = new EnpafBroadcastReceiver(tag);
        IntentFilter filter = new IntentFilter();
        for (String a : actions) filter.addAction(a);
        registerReceiver(r, filter);
        android.util.Log.d("ENPAF", "Registered receiver tag=" + tag + " actions=" + java.util.Arrays.toString(actions));
        return r;
    }

    /** Unregister a previously registered receiver. Called from Python. */
    public void unregisterEnpafReceiver(BroadcastReceiver receiver) {
        try { unregisterReceiver(receiver); } catch (Exception e) {}
    }

    /** Launch an activity-for-result from the UI thread. Called from Python. */
    public void launchForResult(final Intent intent, final int requestCode) {
        runOnUiThread(new Runnable() {
            public void run() {
                startActivityForResult(intent, requestCode);
            }
        });
    }

    // ── Biometric authentication (fingerprint / face / device credential) ──
    // BiometricPrompt's callback is an abstract class (Chaquopy can't subclass
    // it), so the prompt lives here and forwards its result to Python.
    public void authenticateBiometric(final String title, final String subtitle, final String description) {
        runOnUiThread(new Runnable() { public void run() {
            try {
                if (Build.VERSION.SDK_INT < 28) { callPyBiometric(false, "unsupported"); return; }
                android.hardware.biometrics.BiometricPrompt.Builder b =
                        new android.hardware.biometrics.BiometricPrompt.Builder(MainActivity.this);
                b.setTitle((title == null || title.isEmpty()) ? "Authenticate" : title);
                if (subtitle != null && !subtitle.isEmpty()) b.setSubtitle(subtitle);
                if (description != null && !description.isEmpty()) b.setDescription(description);
                if (Build.VERSION.SDK_INT >= 30) {
                    b.setAllowedAuthenticators(
                        android.hardware.biometrics.BiometricManager.Authenticators.BIOMETRIC_WEAK
                        | android.hardware.biometrics.BiometricManager.Authenticators.DEVICE_CREDENTIAL);
                } else {
                    b.setNegativeButton("Cancel", getMainExecutor(),
                        new android.content.DialogInterface.OnClickListener() {
                            public void onClick(android.content.DialogInterface d, int w) {
                                callPyBiometric(false, "cancelled");
                            }
                        });
                }
                android.os.CancellationSignal cancel = new android.os.CancellationSignal();
                b.build().authenticate(cancel, getMainExecutor(),
                    new android.hardware.biometrics.BiometricPrompt.AuthenticationCallback() {
                        @Override
                        public void onAuthenticationSucceeded(android.hardware.biometrics.BiometricPrompt.AuthenticationResult r) {
                            callPyBiometric(true, "");
                        }
                        @Override
                        public void onAuthenticationError(int code, CharSequence err) {
                            callPyBiometric(false, err == null ? ("error " + code) : err.toString());
                        }
                    });
            } catch (Exception e) { callPyBiometric(false, e.getMessage()); }
        }});
    }

    /** 0 = available; 11 = none enrolled; 12 = no hardware (BiometricManager codes). */
    public int canAuthenticateBiometric() {
        try {
            if (Build.VERSION.SDK_INT < 29) {
                android.hardware.fingerprint.FingerprintManager fm =
                    (android.hardware.fingerprint.FingerprintManager) getSystemService(Context.FINGERPRINT_SERVICE);
                if (fm == null || !fm.isHardwareDetected()) return 12;
                return fm.hasEnrolledFingerprints() ? 0 : 11;
            }
            android.hardware.biometrics.BiometricManager bm =
                (android.hardware.biometrics.BiometricManager) getSystemService(Context.BIOMETRIC_SERVICE);
            if (bm == null) return 12;
            if (Build.VERSION.SDK_INT >= 30) {
                return bm.canAuthenticate(
                    android.hardware.biometrics.BiometricManager.Authenticators.BIOMETRIC_WEAK
                    | android.hardware.biometrics.BiometricManager.Authenticators.DEVICE_CREDENTIAL);
            }
            return bm.canAuthenticate();
        } catch (Exception e) { return 12; }
    }

    void callPyBiometric(boolean ok, String err) {
        try {
            Python.getInstance().getModule("main").get("app")
                .callAttr("_on_biometric_result", ok, err == null ? "" : err);
        } catch (Exception e) { e.printStackTrace(); }
    }

    public static class Bridge {
        private final Activity ctx;
        private final Python py;
        Bridge(Activity c, Python p) { ctx = c; py = p; }

        @JavascriptInterface
        public String call(String name, String params, String callId) {
            try {
                PyObject mod = py.getModule("main");
                PyObject app = mod.get("app");
                PyObject bridge = app.get("bridge");
                PyObject result = bridge.callAttr("handle_call", name,
                    py.getModule("json").callAttr("loads", params), callId);
                return py.getModule("json").callAttr("dumps", result).toString();
            } catch (Exception e) {
                return "{\"success\":false,\"error\":\"" + e.getMessage() + "\"}";
            }
        }

        @JavascriptInterface
        public void toast(String msg, String dur) {
            ctx.runOnUiThread(() -> Toast.makeText(ctx, msg,
                "long".equals(dur) ? Toast.LENGTH_LONG : Toast.LENGTH_SHORT).show());
        }

        @JavascriptInterface
        public void vibrate(int ms) {
            Vibrator v = (Vibrator) ctx.getSystemService(Context.VIBRATOR_SERVICE);
            if (v != null) v.vibrate(ms);
        }

        @JavascriptInterface
        public void openUrl(String url) {
            ctx.startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
        }

        @JavascriptInterface
        public void share(String text, String title) {
            Intent i = new Intent(Intent.ACTION_SEND);
            i.setType("text/plain");
            i.putExtra(Intent.EXTRA_TEXT, text);
            ctx.startActivity(Intent.createChooser(i, "Share"));
        }

        @JavascriptInterface
        public void emit(String event, String data) {
            try {
                PyObject app = py.getModule("main").get("app");
                app.get("bridge").callAttr("handle_js_event", event,
                    py.getModule("json").callAttr("loads", data));
            } catch (Exception e) { e.printStackTrace(); }
        }

        @JavascriptInterface
        public void notify(String title, String text, int id) {
            ctx.runOnUiThread(() -> ((MainActivity) ctx).showNotification(id, title, text));
        }

        @JavascriptInterface
        public void setOrientation(String mode) {
            final int o = "landscape".equals(mode) ? ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
                    : "portrait".equals(mode) ? ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
                    : ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED;
            ctx.runOnUiThread(() -> ctx.setRequestedOrientation(o));
        }

        @JavascriptInterface
        public void clipboardSet(String text) {
            ClipboardManager cm = (ClipboardManager) ctx.getSystemService(Context.CLIPBOARD_SERVICE);
            if (cm != null) cm.setPrimaryClip(ClipData.newPlainText("enpaf", text));
        }
    }
}
'''

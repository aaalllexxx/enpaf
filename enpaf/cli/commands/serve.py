"""
ENPAF CLI — Serve Command
Serves the built APK and generates a QR code for debugging.
"""

import os
import sys
import json
import socket
import subprocess
import time
import secrets
from urllib.parse import urlencode

from enpaf.cli import ui

def get_local_ip():
    if os.name == 'nt':
        try:
            cmd = (
                "Get-NetIPAddress -AddressFamily IPv4 | "
                "Where-Object { $_.InterfaceAlias -match 'Wi-Fi|Ethernet|Беспроводная' "
                "-and $_.InterfaceAlias -notmatch 'vEthernet|Hyper-V|VPN|Virtual|Loopback' } | "
                "Select-Object -First 1 -ExpandProperty IPAddress"
            )
            output = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", cmd],
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True
            ).strip()
            if output:
                return output
        except Exception:
            pass

    # Fallback
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Use a public IP to force routing through the default gateway
        s.connect(('8.8.8.8', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def get_windows_ssid():
    """Extract current Wi-Fi SSID on Windows."""
    if os.name != 'nt':
        return ""
    try:
        cmd = (
            "$profiles = Get-NetConnectionProfile;"
            "foreach ($p in $profiles) {"
            "  if ($p.InterfaceAlias -match 'Wi-Fi|Ethernet|Беспроводная' -and $p.InterfaceAlias -notmatch 'vEthernet|Hyper-V|VPN|Virtual|Loopback') {"
            "    $p.Name;"
            "    break;"
            "  }"
            "}"
        )
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", cmd],
            creationflags=subprocess.CREATE_NO_WINDOW,
            text=True
        ).strip()
        if output:
            return output
    except Exception:
        pass

    try:
        output = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"], 
            creationflags=subprocess.CREATE_NO_WINDOW,
            text=True
        )
        for line in output.split('\n'):
            if " SSID" in line and "BSSID" not in line:
                return line.split(":")[1].strip()
    except Exception:
        pass
    return ""

def cmd_serve(args):
    """Serve the built APK and print QR code."""
    ui.logo_small()

    config_path = os.path.join(os.getcwd(), "enpaf.json")
    if not os.path.isfile(config_path):
        ui.error("Not an ENPAF project!")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    app_name = config.get("name", "app").lower().replace(" ", "")
    version = config.get("version", "1.0.0")
    apk_filename = f"{app_name}-{version}.apk"
    apk_path = os.path.join(os.getcwd(), "dist", apk_filename)

    if not os.path.isfile(apk_path):
        ui.error(f"APK not found at dist/{apk_filename}")
        ui.info("Build the APK first using: paf build apk")
        return

    try:
        import qrcode
    except ImportError:
        ui.error("qrcode library is missing. Run 'pip install qrcode[pil]'")
        return

    ip = get_local_ip()
    port = args.port
    ssid = get_windows_ssid()
    
    # Generate API token for secure download
    token = secrets.token_urlsafe(16)

    url = f"http://{ip}:{port}/dist/{apk_filename}"
    
    qr_data = {
        "url": url,
        "token": token
    }
    if ssid:
        qr_data["ssid"] = ssid
        
    # Create an enpaf debug URI
    qr_uri = f"enpaf://debug?{urlencode(qr_data)}"

    ui.header("Scan to Debug")
    ui.newline()
    
    qr = qrcode.QRCode(version=1, box_size=1, border=2)
    qr.add_data(qr_uri)
    qr.make(fit=True)
    qr.print_ascii(out=sys.stdout, tty=False)
    
    ui.newline()
    if ssid:
        ui.info(f"Wi-Fi: {ssid}")
    ui.info(f"URL:   {url}")
    ui.newline()
    ui.dim(f"Starting local server on port {port}...")
    ui.dim("Press Ctrl+C to stop.")
    
    # Use standard library http.server to serve the current directory
    import http.server
    import socketserver
    
    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            ui.dim(f"{self.client_address[0]} - {format%args}")

        def _check_token(self):
            # Check token in query params
            from urllib.parse import urlparse, parse_qs
            query = parse_qs(urlparse(self.path).query)
            if query.get("token", [""])[0] == token:
                return True
            # Fallback to headers
            if self.headers.get("X-Enpaf-Token") == token:
                return True
            return False

        def do_GET(self):
            if not self._check_token():
                self.send_error(403, "Forbidden: Invalid or missing token")
                return
            super().do_GET()

        def do_HEAD(self):
            if not self._check_token():
                self.send_error(403, "Forbidden: Invalid or missing token")
                return
            super().do_HEAD()

        def handle(self):
            try:
                super().handle()
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                pass
            except Exception as e:
                import logging
                logging.error(f"Error handling request: {e}")

    with socketserver.TCPServer(("", port), CustomHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            ui.newline()
            ui.info("Server stopped.")

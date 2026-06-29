/* ENPAF Companion — developer tools + project loader */

const $ = (id) => document.getElementById(id);
const isDev = !enpaf.isAndroid;

function toast(msg, err) {
  const t = $("toast");
  t.textContent = msg;
  t.className = "toast show" + (err ? " err" : "");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (t.className = "toast" + (err ? " err" : "")), 2600);
}

// ── Storage helpers (values are JSON strings) ──
async function load(key, fallback) {
  try { const v = await enpaf.storage.get(key); return v != null ? JSON.parse(v) : fallback; }
  catch (e) { return fallback; }
}
async function save(key, val) { try { await enpaf.storage.set(key, JSON.stringify(val)); } catch (e) {} }

// ─────────────────────────── Boot ───────────────────────────
enpaf.ready(() => {
  $("conn-chip").classList.add("on");
  initLock();
  initNav();
  initConnect();
  initDeviceTab();
  initTools();
  initSettings();
});

// ─────────────────────────── Biometric lock ───────────────────────────
async function initLock() {
  const enabled = await load("bio_lock", false);
  if (!enabled) return;
  $("lock").classList.remove("hidden");
  document.body.style.overflow = "hidden";
  $("lock-btn").onclick = tryUnlock;
  tryUnlock();
}
async function tryUnlock() {
  $("lock-msg").textContent = "Authenticating…";
  try {
    const r = await enpaf.biometric.authenticate({ title: "Unlock ENPAF Companion" });
    if (r.success) { $("lock").classList.add("hidden"); document.body.style.overflow = ""; }
    else $("lock-msg").textContent = r.error ? "Failed: " + r.error : "Authentication failed";
  } catch (e) { $("lock-msg").textContent = "Error: " + e.message; }
}

// ─────────────────────────── Navigation ───────────────────────────
function initNav() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });
}
const TAB_TITLES = { connect: "Connect", device: "Device", tools: "Tools", settings: "Settings" };
function switchTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.dataset.view === name));
  $("appbar-sub").textContent = TAB_TITLES[name] || "Developer tools";
  if (name === "device") refreshDevice();
  if (name === "tools") refreshPermissions();
  if (name === "settings") refreshSettings();
  if (name !== "device") stopSensors();
}

// ═══════════════════════════ CONNECT (loader) ═══════════════════════════
let scanner = null, current = null, pingTimer = null;

function initConnect() {
  $("btn-scan").onclick = startScanner;
  $("btn-close-scanner").onclick = stopScanner;
  $("btn-manual").onclick = () => {
    const url = $("manual-url").value.trim();
    if (!url) return toast("Enter an APK URL", true);
    showFlow({ url });
  };
  $("btn-flow-back").onclick = backToHome;
  $("btn-wifi-settings").onclick = () => enpaf.wifi.enable().catch(() => {});
  $("btn-wifi-connect").onclick = connectWifi;
  $("btn-install").onclick = installApp;
  $("btn-clear-history").onclick = async () => { await save("history", []); renderHistory(); };
  bindDownloadEvents();
  renderHistory();
}

async function startScanner() {
  if (typeof Html5Qrcode === "undefined") return toast("QR library not loaded (no internet?)", true);
  if (enpaf.isAndroid) await enpaf.permissions.request(["CAMERA"]);
  $("reader-card").classList.remove("hidden");
  scanner = new Html5Qrcode("reader");
  scanner.start({ facingMode: "environment" }, { fps: 10, qrbox: { width: 240, height: 240 } }, onScan)
    .catch((e) => { toast("Camera error: " + e, true); stopScanner(); });
}
function stopScanner() {
  if (scanner) { scanner.stop().catch(() => {}); scanner = null; }
  $("reader-card").classList.add("hidden");
}
function onScan(text) {
  stopScanner();
  if (!text.startsWith("enpaf://debug")) return toast("Not an ENPAF QR code", true);
  const p = new URLSearchParams(text.split("?")[1] || "");
  const url = p.get("url");
  if (!url) return toast("Invalid ENPAF QR", true);
  showFlow({ url, ssid: p.get("ssid"), token: p.get("token") });
}

function backToHome() {
  if (pingTimer) clearInterval(pingTimer);
  current = null;
  $("flow-card").classList.add("hidden");
}

async function showFlow(proj) {
  current = proj;
  $("flow-card").classList.remove("hidden");
  $("reader-card").classList.add("hidden");
  $("flow-ssid").textContent = proj.ssid || "Local network";
  $("flow-url").textContent = proj.url;
  $("btn-wifi-connect").style.display = proj.ssid ? "" : "none";
  setStatus("Waiting for server…", "warn");
  $("flow-card").scrollIntoView({ behavior: "smooth" });

  if (pingTimer) clearInterval(pingTimer);
  const probe = async () => {
    if ($("flow-card").classList.contains("hidden")) { clearInterval(pingTimer); return; }
    const ok = await reachable(proj.token ? `${proj.url}?token=${proj.token}` : proj.url);
    if (ok) { setStatus("✓ Server reachable — ready to install", "ok"); $("btn-install").disabled = false; }
    else { setStatus("Waiting for server… (check Wi-Fi)", "warn"); $("btn-install").disabled = true; }
  };
  await probe();
  pingTimer = setInterval(probe, 2500);
}
function setStatus(msg, cls) { const s = $("flow-status"); s.textContent = msg; s.className = "status-line " + (cls || ""); }

async function reachable(url) {
  if (isDev) return true;
  try {
    const c = new AbortController(); const id = setTimeout(() => c.abort(), 2000);
    await fetch(url, { method: "HEAD", mode: "no-cors", cache: "no-store", signal: c.signal });
    clearTimeout(id); return true;
  } catch (e) { return false; }
}

async function connectWifi() {
  if (!current || !current.ssid) return;
  const b = $("btn-wifi-connect"); b.textContent = "Connecting…"; b.disabled = true;
  try {
    const res = await enpaf.wifi.connect(current.ssid, null);
    b.textContent = res.ok ? "Wi-Fi requested ✓" : "Failed";
    if (!res.ok) toast(res.error || res.note || "Connect failed", true);
  } catch (e) { toast("Wi-Fi error", true); }
  setTimeout(() => { b.textContent = "Connect Wi-Fi"; b.disabled = false; }, 2500);
}

async function installApp() {
  if (!current || !current.url) return;
  const url = current.token ? `${current.url}?token=${current.token}` : current.url;
  $("btn-install").disabled = true; $("btn-install").textContent = "Starting…";
  $("progress").classList.remove("hidden"); $("progress-text").classList.remove("hidden");
  $("progress-fill").style.width = "0%"; $("progress-text").textContent = "0%";
  try {
    const res = await enpaf.call("install_apk", { url });
    if (res && res.error) { toast(res.error, true); resetInstall(); }
    await saveHistory(current);
  } catch (e) { toast("Install failed", true); resetInstall(); }
}
function resetInstall() {
  $("btn-install").disabled = false; $("btn-install").textContent = "⬇ Download & Install";
  $("progress").classList.add("hidden"); $("progress-text").classList.add("hidden");
}
function bindDownloadEvents() {
  enpaf.on("download_start", () => { $("btn-install").textContent = "Downloading…"; });
  enpaf.on("download_progress", (d) => {
    $("progress").classList.remove("hidden"); $("progress-text").classList.remove("hidden");
    $("progress-fill").style.width = d.percent + "%";
    const mb = (b) => (b / 1048576).toFixed(1);
    $("progress-text").textContent = d.total ? `${d.percent}% (${mb(d.downloaded)} / ${mb(d.total)} MB)` : d.percent + "%";
  });
  enpaf.on("download_complete", () => { $("btn-install").textContent = "Opening installer…"; });
  enpaf.on("install_prompt", () => { toast("Installer opened"); setTimeout(resetInstall, 2000); });
  enpaf.on("install_status", (d) => {
    if (d.success) toast("App installed ✓");
    else if (d.status !== 3) toast("Install failed" + (d.message ? ": " + d.message : ""), true);
    resetInstall();
  });
  enpaf.on("install_error", (d) => {
    if (d.error === "install_permission_required") toast("Allow installs, then tap Install again", true);
    else toast("Install error: " + (d.error || ""), true);
    resetInstall();
  });
}

// History
async function saveHistory(proj) {
  let h = await load("history", []);
  h = h.filter((p) => p.url !== proj.url);
  h.unshift({ url: proj.url, ssid: proj.ssid || null, ts: Date.now() });
  if (h.length > 12) h = h.slice(0, 12);
  await save("history", h); renderHistory();
}
async function renderHistory() {
  const h = await load("history", []);
  const list = $("history");
  if (!h.length) { list.innerHTML = '<li class="empty">No projects yet.</li>'; return; }
  list.innerHTML = "";
  h.forEach((p) => {
    const li = document.createElement("li"); li.className = "row-item";
    li.innerHTML = `<div><div class="name">${p.ssid || "Local app"}</div><div class="sub">${p.url}</div></div>`;
    const b = document.createElement("button"); b.className = "btn btn-secondary sm"; b.textContent = "Open";
    b.onclick = () => showFlow({ url: p.url, ssid: p.ssid });
    li.appendChild(b); list.appendChild(li);
  });
}

// ═══════════════════════════ DEVICE ═══════════════════════════
function initDeviceTab() {
  $("btn-device-refresh").onclick = refreshDevice;
  $("sensors-toggle").addEventListener("change", (e) => (e.target.checked ? startSensors() : stopSensors()));
}
async function refreshDevice() {
  try {
    const [info, batt, net] = await Promise.all([
      enpaf.mod("device", "info"), enpaf.battery.info(), enpaf.battery.network(),
    ]);
    const rows = {
      Platform: info.platform, Model: info.model, "OS version": info.os_version,
      "App version": info.app_version, Screen: info.screen_width ? `${info.screen_width}×${info.screen_height}` : "—",
      Battery: batt.level != null ? `${batt.level}% ${batt.charging ? "⚡" : ""}` : "—",
      Network: net.connected ? net.type : "offline",
    };
    $("device-info").innerHTML = Object.entries(rows)
      .map(([k, v]) => `<div class="kv"><span>${k}</span><b>${v ?? "—"}</b></div>`).join("");
  } catch (e) { $("device-info").innerHTML = `<div class="empty">Error: ${e.message}</div>`; }
}

let sensorTimer = null;
const SENSORS = [["accelerometer", "Accel (m/s²)"], ["gyroscope", "Gyro (rad/s)"], ["magnetometer", "Magnet (µT)"], ["light", "Light (lx)"], ["proximity", "Proximity"], ["pressure", "Pressure (hPa)"]];
function startSensors() {
  const grid = $("sensor-grid");
  grid.innerHTML = SENSORS.map(([k, l]) => `<div class="sensor-card"><div class="l">${l}</div><div class="v" id="sv-${k}">…</div></div>`).join("");
  const tick = async () => {
    for (const [k] of SENSORS) {
      try {
        const r = await enpaf.sensors.read(k);
        const el = $("sv-" + k); if (!el) continue;
        el.textContent = Array.isArray(r.values) ? r.values.map((n) => (+n).toFixed(2)).join(", ") : (r.values ?? (r.available ? "—" : "n/a"));
      } catch (e) {}
    }
  };
  tick(); sensorTimer = setInterval(tick, 450);
}
function stopSensors() {
  if (sensorTimer) { clearInterval(sensorTimer); sensorTimer = null; }
  const t = $("sensors-toggle"); if (t) t.checked = false;
}

// ═══════════════════════════ TOOLS ═══════════════════════════
function initTools() {
  $("btn-wifi-scan").onclick = wifiScan;
  $("btn-bt-scan").onclick = btScan;
  $("btn-nfc-read").onclick = () => { $("nfc-out").textContent = "Hold an NFC tag to the phone…"; nfcRead(); };
  $("btn-perm-refresh").onclick = refreshPermissions;
  document.querySelectorAll("[data-act]").forEach((b) => b.addEventListener("click", () => quickAction(b.dataset.act)));

  enpaf.wifi.onResult((n) => addRow("wifi-list", `${n.secure ? "🔒 " : ""}${n.ssid}`, `${n.rssi} dBm`, "wifi-" + n.ssid));
  enpaf.wifi.onFinished(() => emptyIfBlank("wifi-list", "No networks found"));
  enpaf.bluetooth.onFound((d) => addRow("bt-list", d.name || "(unnamed)", `${d.address}${d.rssi ? " · " + d.rssi + " dBm" : ""}`, "bt-" + d.address));
  enpaf.bluetooth.onDiscoveryFinished(() => emptyIfBlank("bt-list", "No devices found"));
  enpaf.nfc.onTag(() => nfcRead());
}
function addRow(listId, name, sub, key) {
  const list = $(listId);
  if (list.querySelector(".empty")) list.innerHTML = "";
  if (key && list.querySelector(`[data-k="${key}"]`)) return;
  const li = document.createElement("li"); li.className = "row-item"; if (key) li.dataset.k = key;
  li.innerHTML = `<div><div class="name">${name}</div><div class="sub">${sub}</div></div>`;
  list.appendChild(li);
}
function emptyIfBlank(id, msg) { const l = $(id); if (!l.children.length || l.querySelector(".empty")) l.innerHTML = `<li class="empty">${msg}</li>`; }

async function wifiScan() {
  if (enpaf.isAndroid) await enpaf.permissions.request(["FINE_LOCATION"]);
  $("wifi-list").innerHTML = '<li class="empty">Scanning…</li>';
  await enpaf.wifi.scan();
}
async function btScan() {
  if (enpaf.isAndroid) await enpaf.permissions.request(["BLUETOOTH_SCAN", "BLUETOOTH_CONNECT", "FINE_LOCATION"]);
  $("bt-list").innerHTML = '<li class="empty">Scanning…</li>';
  const p = await enpaf.bluetooth.paired(); (p.devices || []).forEach((d) => addRow("bt-list", d.name || "(unnamed)", d.address + " · paired", "bt-" + d.address));
  await enpaf.bluetooth.discover();
}
async function nfcRead() {
  try {
    const r = await enpaf.nfc.read();
    if (!r.tag) { $("nfc-out").textContent = r.note || "No tag."; return; }
    const recs = (r.records || []).map((x) => x.type === "uri" ? "🔗 " + x.uri : x.type === "text" ? "📝 " + x.text : "· " + x.type).join(" | ");
    $("nfc-out").innerHTML = `<b>ID:</b> ${r.id || "—"}<br>${recs || "(empty)"}` + (r.dev ? " <span class='muted'>(dev)</span>" : "");
  } catch (e) { $("nfc-out").textContent = "Error: " + e.message; }
}

async function quickAction(act) {
  const out = $("action-out"); out.textContent = "";
  try {
    if (act === "vibrate") { enpaf.device.vibrate(140); out.textContent = "Vibrated."; }
    else if (act === "toast") { enpaf.device.toast("Hello from Companion 👋"); }
    else if (act === "notify") {
      if (enpaf.isAndroid) await enpaf.permissions.request(["POST_NOTIFICATIONS"]);
      await enpaf.notifications.notify({ title: "ENPAF Companion", text: "Test notification" });
      out.textContent = "Notification sent.";
    } else if (act === "clip-copy") { enpaf.device.clipboard("ENPAF Companion 🚀"); out.textContent = "Copied to clipboard."; }
    else if (act === "clip-read") { const r = await enpaf.mod("device", "clipboard_get"); out.textContent = "Clipboard: " + (r.text || "(empty)"); }
    else if (act === "share") { enpaf.device.share("Shared from ENPAF Companion", "ENPAF"); }
    else if (act === "location") {
      if (enpaf.isAndroid) await enpaf.permissions.request(["FINE_LOCATION"]);
      const l = await enpaf.location.get();
      out.textContent = l.fix ? `Lat ${(+l.latitude).toFixed(5)}, Lon ${(+l.longitude).toFixed(5)}` : (l.note || "No location");
    } else if (act === "biometric") {
      const r = await enpaf.biometric.authenticate({ title: "Biometric test" });
      out.textContent = r.success ? "✓ Authenticated" : "✗ " + (r.error || "failed");
    }
  } catch (e) { out.textContent = "Error: " + e.message; }
}

const PERM_LIST = ["CAMERA", "RECORD_AUDIO", "FINE_LOCATION", "BLUETOOTH_SCAN", "BLUETOOTH_CONNECT", "POST_NOTIFICATIONS", "NFC", "READ_CONTACTS"];
async function refreshPermissions() {
  const list = $("perm-list");
  try {
    const res = await enpaf.permissions.checkAll(PERM_LIST);
    const granted = new Set(res.granted || []);
    const full = (k) => "android.permission." + (k === "FINE_LOCATION" ? "ACCESS_FINE_LOCATION" : k === "RECORD_AUDIO" ? "RECORD_AUDIO" : k);
    list.innerHTML = "";
    PERM_LIST.forEach((k) => {
      const ok = [...granted].some((g) => g.endsWith(k) || g.endsWith(full(k).split(".").pop()));
      const li = document.createElement("li"); li.className = "perm-row";
      li.innerHTML = `<span>${k}</span><span class="badge ${ok ? "granted" : "denied"}">${ok ? "granted" : "request"}</span>`;
      if (!ok) li.querySelector(".badge").onclick = async () => { await enpaf.permissions.request([k]); refreshPermissions(); };
      list.appendChild(li);
    });
  } catch (e) { list.innerHTML = `<li class="empty">Error: ${e.message}</li>`; }
}

// ═══════════════════════════ SETTINGS ═══════════════════════════
function initSettings() {
  $("bio-toggle").addEventListener("change", async (e) => {
    if (e.target.checked) {
      const r = await enpaf.biometric.authenticate({ title: "Enable biometric lock" });
      if (!r.success) { e.target.checked = false; return toast("Authentication failed", true); }
    }
    await save("bio_lock", e.target.checked);
    toast(e.target.checked ? "Biometric lock enabled" : "Lock disabled");
  });
}
async function refreshSettings() {
  $("bio-toggle").checked = await load("bio_lock", false);
  try {
    const av = await enpaf.biometric.available();
    $("bio-state").textContent = av.available ? "Biometrics available on this device." : `Not enrolled/available (code ${av.code ?? "?"}).`;
  } catch (e) {}
  try {
    const cfg = await enpaf.call("__enpaf_get_config", {});
    const info = await enpaf.mod("device", "info");
    const rows = { App: cfg.name || "ENPAF Companion", Version: cfg.version || "—", Package: cfg.package || "—", Platform: info.platform, Model: info.model };
    $("about-info").innerHTML = Object.entries(rows).map(([k, v]) => `<div class="kv"><span>${k}</span><b>${v ?? "—"}</b></div>`).join("");
  } catch (e) {}
}

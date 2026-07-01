/* ENPAF Companion — developer project loader.
 * Tabs: Connect (load & install builds), Logs, Device (diagnostics + tester),
 * Settings. Dev features: auto-reload watch, paste URL, favorites,
 * device diagnostics, connection tester.
 */

const $ = (id) => document.getElementById(id);
const isDev = !enpaf.isAndroid;

function toast(msg, err) {
  const t = $("toast");
  t.textContent = msg;
  t.className = "toast show" + (err ? " err" : "");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (t.className = "toast" + (err ? " err" : "")), 2600);
}
function escapeHtml(s) { const d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }
function formatBytes(n) { return n ? (n / 1073741824 >= 1 ? (n / 1073741824).toFixed(1) + " GB" : (n / 1048576).toFixed(1) + " MB") : "—"; }
function hostOf(url) { try { return new URL(url).host; } catch (e) { return url; } }

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
  initLogs();
  initDevice();
  initSettings();
  refreshSelfNetwork();
  checkInstallPermission();
  renderFavorites();
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
const TAB_TITLES = { connect: "Project loader", logs: "Activity log", device: "Device diagnostics", settings: "Settings" };
function initNav() {
  document.querySelectorAll(".tab").forEach((tab) =>
    tab.addEventListener("click", () => switchTab(tab.dataset.tab)));
}
function switchTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.dataset.view === name));
  $("appbar-sub").textContent = TAB_TITLES[name] || "Project loader";
  if (name === "logs") renderLog();
  if (name === "device") { refreshDiag(); if (current && current.url && !$("probe-url").value) $("probe-url").value = current.url; }
  if (name === "settings") refreshSettings();
  if (name === "connect") { refreshSelfNetwork(); checkInstallPermission(); renderFavorites(); }
}

// ═══════════════════════════ ACTIVITY LOG ═══════════════════════════
let LOG = [];
function logLine(msg, kind) {
  LOG.push({ time: new Date().toLocaleTimeString(), msg, kind: kind || "info" });
  if (LOG.length > 200) LOG = LOG.slice(-200);
  const view = document.querySelector('[data-view="logs"]');
  if (view && view.classList.contains("active")) renderLog();
}
function initLogs() {
  $("btn-clear-log").onclick = () => { LOG = []; renderLog(); };
  $("btn-copy-log").onclick = () => {
    enpaf.device.clipboard(LOG.map((e) => `[${e.time}] ${e.msg}`).join("\n") || "");
    toast(LOG.length ? "Log copied" : "Log is empty");
  };
}
function renderLog() {
  const box = $("logbox");
  if (!LOG.length) { box.innerHTML = '<div class="empty">No activity yet.</div>'; return; }
  box.innerHTML = LOG.map((e) =>
    `<div class="logline ${e.kind}"><span class="t">${e.time}</span> ${escapeHtml(e.msg)}</div>`).join("");
  box.scrollTop = box.scrollHeight;
}

// ═══════════════════════════ CONNECT (loader) ═══════════════════════════
let scanner = null, current = null, pingTimer = null;

function initConnect() {
  $("btn-scan").onclick = startScanner;
  $("btn-close-scanner").onclick = stopScanner;
  $("btn-manual").onclick = () => {
    const url = $("manual-url").value.trim();
    if (!url) return toast("Enter a build URL", true);
    showFlow({ url });
  };
  $("btn-paste").onclick = pasteUrl;
  $("btn-flow-back").onclick = backToHome;
  $("btn-wifi-settings").onclick = () => enpaf.wifi.enable().catch(() => {});
  $("btn-wifi-connect").onclick = connectWifi;
  $("btn-install").onclick = installApp;
  $("btn-clear-history").onclick = async () => { await save("history", []); renderHistory(); };
  $("btn-allow-install").onclick = allowInstall;
  $("btn-fav-add").onclick = addFavorite;
  $("watch-toggle").addEventListener("change", (e) => (e.target.checked ? startWatch() : stopWatch()));
  bindDownloadEvents();
  renderHistory();
}

// Feature 2 — paste & auto-detect a build URL from the clipboard.
async function pasteUrl() {
  try {
    const r = await enpaf.mod("device", "clipboard_get");
    const text = ((r && r.text) || "").trim();
    if (!text) return toast("Clipboard is empty", true);
    if (text.startsWith("enpaf://debug")) { onScan(text); return; }
    const m = text.match(/https?:\/\/\S+/);
    if (m) { $("manual-url").value = m[0]; showFlow({ url: m[0] }); logLine("Pasted URL → " + m[0]); return; }
    toast("No build URL in clipboard", true);
  } catch (e) { toast("Clipboard unavailable", true); }
}

// This device's Wi-Fi / IP — helps match the dev machine's network.
async function refreshSelfNetwork() {
  const el = $("net-self");
  if (!el) return;
  if (isDev) { el.textContent = "dev (browser)"; return; }
  try {
    const w = await enpaf.wifi.info();
    const ssid = w.ssid || w.SSID || null;
    const ip = w.ip || w.ip_address || w.ipAddress || null;
    el.textContent = [ssid, ip].filter(Boolean).join(" · ") || "Wi-Fi off?";
    el.dataset.ssid = ssid || "";
  } catch (e) { el.textContent = "—"; }
}

// Install-permission gate (Android 8+ needs a per-app grant).
async function checkInstallPermission() {
  try {
    const r = await enpaf.call("can_install", {});
    const ok = !!r.can_install;
    $("perm-banner").classList.toggle("hidden", ok);
    const st = $("install-perm-state");
    if (st) { st.textContent = ok ? "Allowed ✓" : "Blocked"; st.className = ok ? "ok-text" : "warn-text"; }
    return ok;
  } catch (e) { return false; }
}
async function allowInstall() {
  try { await enpaf.call("request_install_permission", {}); logLine("Opened install-permission settings"); }
  catch (e) { toast("Could not open settings", true); }
}

async function startScanner() {
  if (typeof Html5Qrcode === "undefined") return toast("QR library failed to load", true);
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
  logLine("Scanned QR → " + url);
  showFlow({ url, ssid: p.get("ssid"), token: p.get("token") });
}

function backToHome() {
  if (pingTimer) clearInterval(pingTimer);
  stopWatch();
  current = null;
  $("flow-card").classList.add("hidden");
}

async function showFlow(proj) {
  current = proj;
  $("flow-card").classList.remove("hidden");
  $("reader-card").classList.add("hidden");
  $("watch-toggle").checked = false;
  $("flow-url").textContent = proj.url;
  const mine = ($("net-self").dataset.ssid || "").trim();
  let ssidLabel = proj.ssid || "Local network";
  if (proj.ssid && mine && proj.ssid !== mine) ssidLabel = `${proj.ssid} ⚠ (you: ${mine})`;
  $("flow-ssid").textContent = ssidLabel;
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
  setTimeout(() => { b.textContent = "Connect Wi-Fi"; b.disabled = false; refreshSelfNetwork(); }, 2500);
}

async function installApp() {
  if (!current || !current.url) return;
  if (!(await checkInstallPermission())) return toast("Allow installs first", true);
  const url = current.token ? `${current.url}?token=${current.token}` : current.url;
  $("btn-install").disabled = true; $("btn-install").textContent = "Starting…";
  $("progress").classList.remove("hidden"); $("progress-text").classList.remove("hidden");
  $("progress-fill").style.width = "0%"; $("progress-text").textContent = "0%";
  logLine("Install requested → " + current.url);
  try {
    const res = await enpaf.call("install_apk", { url });
    if (res && res.error) { toast(res.error, true); logLine("Install error: " + res.error, "err"); resetInstall(); }
    await saveHistory(current);
  } catch (e) { toast("Install failed", true); logLine("Install failed: " + e.message, "err"); resetInstall(); }
}
function resetInstall() {
  $("btn-install").disabled = false; $("btn-install").textContent = "Download & Install";
  $("progress").classList.add("hidden"); $("progress-text").classList.add("hidden");
}
function bindDownloadEvents() {
  enpaf.on("download_start", () => { $("btn-install").textContent = "Downloading…"; logLine("Download started"); });
  enpaf.on("download_progress", (d) => {
    $("progress").classList.remove("hidden"); $("progress-text").classList.remove("hidden");
    $("progress-fill").style.width = d.percent + "%";
    const mb = (b) => (b / 1048576).toFixed(1);
    $("progress-text").textContent = d.total ? `${d.percent}% (${mb(d.downloaded)} / ${mb(d.total)} MB)` : d.percent + "%";
    if (d.percent === 0 || d.percent === 50 || d.percent === 100) logLine(`Downloading… ${d.percent}%`);
  });
  enpaf.on("download_complete", (d) => {
    $("btn-install").textContent = "Opening installer…";
    logLine("Download complete" + (d && d.bytes ? ` (${(d.bytes / 1048576).toFixed(1)} MB)` : ""), "ok");
  });
  enpaf.on("install_prompt", () => { toast("Installer opened"); logLine("System installer opened"); setTimeout(resetInstall, 2000); });
  enpaf.on("install_status", (d) => {
    if (d.success) { toast("App installed ✓"); logLine("Installed ✓", "ok"); }
    else if (d.status !== 3) { toast("Install failed" + (d.message ? ": " + d.message : ""), true); logLine("Install failed" + (d.message ? ": " + d.message : ""), "err"); }
    else { logLine("Install cancelled"); }
    resetInstall();
  });
  enpaf.on("install_error", (d) => {
    if (d.error === "install_permission_required") { toast("Allow installs, then tap Install again", true); logLine("Install blocked — permission required", "err"); checkInstallPermission(); }
    else { toast("Install error: " + (d.error || ""), true); logLine("Install error: " + (d.error || ""), "err"); }
    resetInstall();
  });
}

// Feature 1 — auto-reload watch: poll the build URL and alert when it changes.
let watch = { url: null, sig: null, timer: null };
async function sigOf(url) {
  try { const r = await enpaf.call("probe_url", { url }); return r.ok ? `${r.etag}|${r.last_modified}|${r.length}` : null; }
  catch (e) { return null; }
}
async function startWatch() {
  if (!current || !current.url) { $("watch-toggle").checked = false; return toast("Open a build first", true); }
  watch.url = current.token ? `${current.url}?token=${current.token}` : current.url;
  watch.sig = await sigOf(watch.url);
  logLine("Watching build for changes…");
  if (watch.timer) clearInterval(watch.timer);
  watch.timer = setInterval(async () => {
    const s = await sigOf(watch.url);
    if (s && watch.sig && s !== watch.sig) {
      watch.sig = s;
      toast("New build available — reinstall");
      logLine("New build detected on server", "ok");
      enpaf.device.vibrate(120);
    }
  }, 5000);
}
function stopWatch() {
  if (watch.timer) clearInterval(watch.timer);
  watch.timer = null;
  const t = $("watch-toggle"); if (t) t.checked = false;
}

// History
async function saveHistory(proj) {
  let h = await load("history", []);
  h = h.filter((p) => p.url !== proj.url);
  h.unshift({ url: proj.url, ssid: proj.ssid || null, token: proj.token || null, ts: Date.now() });
  if (h.length > 12) h = h.slice(0, 12);
  await save("history", h); renderHistory();
}
async function renderHistory() {
  const h = await load("history", []);
  const list = $("history");
  if (!h.length) { list.innerHTML = '<li class="empty">No builds yet.</li>'; return; }
  list.innerHTML = "";
  h.forEach((p) => {
    const li = document.createElement("li"); li.className = "row-item";
    const when = p.ts ? new Date(p.ts).toLocaleString() : "";
    li.innerHTML = `<div><div class="name">${escapeHtml(p.ssid || hostOf(p.url))}</div><div class="sub mono">${escapeHtml(p.url)}</div><div class="sub muted">${when}</div></div>`;
    const actions = document.createElement("div"); actions.className = "row";
    const reinstall = document.createElement("button"); reinstall.className = "btn btn-secondary sm"; reinstall.textContent = "Reinstall";
    reinstall.onclick = () => showFlow({ url: p.url, ssid: p.ssid, token: p.token });
    const star = document.createElement("button"); star.className = "btn btn-ghost sm"; star.textContent = "☆";
    star.title = "Add to favorites";
    star.onclick = () => addFavorite({ url: p.url, ssid: p.ssid, token: p.token });
    const del = document.createElement("button"); del.className = "btn btn-ghost sm"; del.textContent = "✕";
    del.onclick = async () => { let hh = await load("history", []); hh = hh.filter((x) => x.url !== p.url); await save("history", hh); renderHistory(); };
    actions.append(reinstall, star, del);
    li.appendChild(actions); list.appendChild(li);
  });
}

// Feature 3 — favorites (pinned dev servers).
async function addFavorite(proj) {
  const p = proj && proj.url ? proj : current;
  if (!p || !p.url) return toast("Open a build first", true);
  let favs = await load("favorites", []);
  if (favs.some((f) => f.url === p.url)) return toast("Already in favorites");
  favs.unshift({ label: p.ssid || hostOf(p.url), url: p.url, ssid: p.ssid || null, token: p.token || null });
  if (favs.length > 20) favs = favs.slice(0, 20);
  await save("favorites", favs); renderFavorites(); toast("Saved to favorites ⭐");
}
async function renderFavorites() {
  const favs = await load("favorites", []);
  const card = $("fav-card"); const list = $("favorites");
  card.classList.toggle("hidden", favs.length === 0);
  list.innerHTML = "";
  favs.forEach((f) => {
    const li = document.createElement("li"); li.className = "row-item";
    li.innerHTML = `<div><div class="name">⭐ ${escapeHtml(f.label || "Build")}</div><div class="sub mono">${escapeHtml(f.url)}</div></div>`;
    const actions = document.createElement("div"); actions.className = "row";
    const open = document.createElement("button"); open.className = "btn btn-secondary sm"; open.textContent = "Reinstall";
    open.onclick = () => showFlow({ url: f.url, ssid: f.ssid, token: f.token });
    const del = document.createElement("button"); del.className = "btn btn-ghost sm"; del.textContent = "✕";
    del.onclick = async () => { let ff = await load("favorites", []); ff = ff.filter((x) => x.url !== f.url); await save("favorites", ff); renderFavorites(); };
    actions.append(open, del); li.appendChild(actions); list.appendChild(li);
  });
}

// ═══════════════════════════ DEVICE (diagnostics + tester) ═══════════════════════════
let DIAG = null;
function initDevice() {
  $("btn-diag-refresh").onclick = refreshDiag;
  $("btn-diag-copy").onclick = copyDiag;
  $("btn-probe").onclick = runProbe;
}

// Feature 4 — device diagnostics.
async function refreshDiag() {
  const box = $("diag-info"); box.innerHTML = '<div class="empty">Loading…</div>';
  try {
    const d = await enpaf.call("diag_info", {});
    DIAG = d;
    const gb = (n) => (n ? (n / 1073741824).toFixed(1) + " GB" : "—");
    const screen = d.screen_width ? `${d.screen_width}×${d.screen_height}${d.density ? " @" + d.density + "x" : ""}` : "—";
    const rows = {
      Device: [d.manufacturer, d.model].filter(Boolean).join(" ") || d.model || "—",
      Android: d.android ? `${d.android} (API ${d.api_level ?? "?"})` : "—",
      ABI: d.abi || "—",
      Screen: screen,
      RAM: d.ram_total ? `${gb(d.ram_avail)} free / ${gb(d.ram_total)}` : "—",
      Storage: d.storage_total ? `${gb(d.storage_free)} free / ${gb(d.storage_total)}` : "—",
      WebView: d.webview || "—",
      "Install perm": d.can_install ? "allowed ✓" : "blocked",
    };
    box.innerHTML = Object.entries(rows)
      .map(([k, v]) => `<div class="kv"><span>${k}</span><b>${escapeHtml(String(v))}</b></div>`).join("");
  } catch (e) { box.innerHTML = `<div class="empty">Error: ${e.message}</div>`; }
}
function copyDiag() {
  if (!DIAG) return toast("Nothing to copy", true);
  const lines = Object.entries(DIAG).filter(([k]) => !k.endsWith("_err")).map(([k, v]) => `${k}: ${v}`);
  enpaf.device.clipboard("ENPAF device report\n" + lines.join("\n"));
  toast("Report copied");
}

// Feature 5 — connection tester.
async function runProbe() {
  const url = $("probe-url").value.trim() || (current && current.url) || "";
  if (!url) return toast("Enter a URL", true);
  const out = $("probe-out"); out.innerHTML = '<div class="empty">Testing…</div>';
  try {
    const r = await enpaf.call("probe_url", { url });
    if (!r.ok) {
      out.innerHTML = `<div class="kv"><span>Status</span><b class="warn-text">Unreachable</b></div>` +
        `<div class="kv"><span>Error</span><b>${escapeHtml(r.error || "—")}</b></div>`;
      return;
    }
    const rows = {
      Status: `${r.status} ✓`, Latency: `${r.ms} ms`,
      Size: r.length ? formatBytes(r.length) : "—",
      "Last modified": r.last_modified || "—",
    };
    out.innerHTML = Object.entries(rows)
      .map(([k, v]) => `<div class="kv"><span>${k}</span><b>${escapeHtml(String(v))}</b></div>`).join("");
  } catch (e) { out.innerHTML = `<div class="empty">Error: ${e.message}</div>`; }
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
  $("btn-fix-install").onclick = allowInstall;
  $("btn-clear-data").onclick = async () => {
    await save("history", []);
    LOG = []; renderLog(); renderHistory();
    toast("History & log cleared");
  };
}
async function refreshSettings() {
  $("bio-toggle").checked = await load("bio_lock", false);
  try {
    const av = await enpaf.biometric.available();
    $("bio-state").textContent = av.available ? "Biometrics available on this device." : `Not enrolled/available (code ${av.code ?? "?"}).`;
  } catch (e) {}
  checkInstallPermission();
  try {
    const cfg = await enpaf.call("__enpaf_get_config", {});
    const info = await enpaf.mod("device", "info");
    const rows = {
      App: cfg.name || "ENPAF Companion", Version: cfg.version || "—", Package: cfg.package || "—",
      Platform: info.platform, Model: info.model, "OS version": info.os_version,
    };
    $("about-info").innerHTML = Object.entries(rows)
      .map(([k, v]) => `<div class="kv"><span>${k}</span><b>${v ?? "—"}</b></div>`).join("");
  } catch (e) {}
}

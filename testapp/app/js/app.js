/**
 * ENPAF Starter App — Main JavaScript
 * Demonstrates bridge calls, storage, events, and device APIs.
 */

// ─── Wait for ENPAF Bridge ──────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // Check connection status
    const checkConnection = setInterval(() => {
        if (typeof enpaf !== 'undefined' && enpaf.connected) {
            clearInterval(checkConnection);
            onConnected();
        }
    }, 200);

    // Timeout after 5s
    setTimeout(() => {
        clearInterval(checkConnection);
        if (typeof enpaf === 'undefined' || !enpaf.connected) {
            onConnected(); // Still show UI
        }
    }, 5000);
});

function onConnected() {
    const badge = document.getElementById('connectionBadge');
    const text = document.getElementById('connectionText');
    const dot = badge.querySelector('.badge-dot');

    dot.classList.add('connected');
    text.textContent = 'Connected to Python';
    badge.style.borderColor = 'rgba(0, 230, 118, 0.3)';
    badge.style.background = 'rgba(0, 230, 118, 0.1)';
    text.style.color = '#00E676';

    // Load notes
    loadNotes();
}

// ─── Bridge Demo: Call Python ────────────────────────────────

async function callPython() {
    const resultDiv = document.getElementById('heroResult');
    
    try {
        const name = prompt('Как тебя зовут?', 'Alex') || 'World';
        const result = await enpaf.call('hello', { name });
        
        resultDiv.innerHTML = `
            <div class="result-card">
                <div class="label">Python Response</div>
                <div class="value">${result.message}</div>
            </div>
        `;
    } catch (e) {
        resultDiv.innerHTML = `
            <div class="result-card" style="border-color: rgba(231,76,60,0.3)">
                <div class="label">Error</div>
                <div class="value" style="color: #E74C3C">${e.message}</div>
            </div>
        `;
    }
}

// ─── Bridge Demo: Get Time ───────────────────────────────────

async function showTime() {
    const resultDiv = document.getElementById('heroResult');
    
    try {
        const result = await enpaf.call('get_time', {});
        
        resultDiv.innerHTML = `
            <div class="result-card">
                <div class="label">Python → JS</div>
                <div class="value">🕐 ${result.time} · 📅 ${result.date}</div>
            </div>
        `;
    } catch (e) {
        resultDiv.innerHTML = `
            <div class="result-card" style="border-color: rgba(231,76,60,0.3)">
                <div class="value" style="color: #E74C3C">${e.message}</div>
            </div>
        `;
    }
}

// ─── Feature Cards Demos ─────────────────────────────────────

function demosBridge() {
    callPython();
}

function demosStorage() {
    document.getElementById('notesSection').scrollIntoView({ behavior: 'smooth' });
}

function demosEvents() {
    enpaf.emit('demo_event', { action: 'test', timestamp: Date.now() });
    enpaf.device.toast('Event sent to Python! ⚡');
}

function demosDevice() {
    enpaf.device.toast('Hello from Device API! 📱');
    enpaf.device.vibrate(100);
}

// ─── Notes (Storage Demo) ────────────────────────────────────

async function addNote() {
    const input = document.getElementById('noteInput');
    const text = input.value.trim();
    
    if (!text) return;
    
    try {
        await enpaf.call('save_note', { text });
        input.value = '';
        loadNotes();
        enpaf.device.toast('Заметка сохранена! ✅');
    } catch (e) {
        enpaf.device.toast('Ошибка: ' + e.message);
    }
}

async function loadNotes() {
    const listEl = document.getElementById('notesList');
    
    try {
        const result = await enpaf.call('get_notes', {});
        const notes = result.notes || [];
        
        if (notes.length === 0) {
            listEl.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">📋</span>
                    <p>Нет заметок. Добавьте первую!</p>
                </div>
            `;
            return;
        }
        
        listEl.innerHTML = notes.map(note => `
            <div class="note-item" id="note-${note._id}">
                <span class="note-text">${escapeHtml(note.text)}</span>
                <span class="note-time">${note._created_at || ''}</span>
                <button class="btn btn-danger btn-sm" onclick="deleteNote(${note._id})">✕</button>
            </div>
        `).join('');
        
    } catch (e) {
        listEl.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">⚠️</span>
                <p>Не удалось загрузить заметки</p>
            </div>
        `;
    }
}

async function deleteNote(id) {
    try {
        await enpaf.call('delete_note', { id });
        
        const el = document.getElementById('note-' + id);
        if (el) {
            el.style.opacity = '0';
            el.style.transform = 'translateX(20px)';
            setTimeout(() => loadNotes(), 300);
        }
    } catch (e) {
        enpaf.device.toast('Ошибка удаления');
    }
}

// ─── Calculator (Backend Calculation) ────────────────────────

async function calculate() {
    const a = document.getElementById('calcA').value;
    const b = document.getElementById('calcB').value;
    const op = document.getElementById('calcOp').value;
    const resultDiv = document.getElementById('calcResult');
    
    try {
        const result = await enpaf.call('calculate', { a, b, op });
        
        resultDiv.innerHTML = `
            <span class="result-value">${result.expression}</span>
        `;
    } catch (e) {
        resultDiv.innerHTML = `<span style="color: #E74C3C">${e.message}</span>`;
    }
}

// ─── Menu Toggle ─────────────────────────────────────────────

function toggleMenu() {
    enpaf.device.toast('Menu coming soon! 🚧');
}

// ─── Sensors (read from Python DeviceAPI) ────────────────────

function sensorCard(label, value, sub) {
    return `<div class="sensor-card">
        <div class="sensor-label">${label}</div>
        <div class="sensor-value">${value}</div>
        ${sub ? `<div class="sensor-sub">${sub}</div>` : ''}
    </div>`;
}

const fmt = v => (Array.isArray(v) ? v.map(n => (+n).toFixed(2)).join(', ') : v);

async function readSensors() {
    const grid = document.getElementById('sensorGrid');
    grid.innerHTML = '<div class="empty-state"><span class="empty-icon">⏳</span><p>Читаю датчики…</p></div>';
    try {
        // enpaf.sensors.* читает значения из Python (нативно на телефоне)
        const [accel, gyro, light, net] = await Promise.all([
            enpaf.sensors.read('accelerometer'),
            enpaf.sensors.read('gyroscope'),
            enpaf.sensors.read('light'),
            enpaf.sensors.network(),
        ]);
        const tag = a => a && a.dev ? 'dev-заглушка' : (a && a.available ? '' : 'нет датчика');
        grid.innerHTML =
            sensorCard('Акселерометр (м/с²)', fmt(accel.values), tag(accel)) +
            sensorCard('Гироскоп (рад/с)', fmt(gyro.values), tag(gyro)) +
            sensorCard('Освещённость (лк)', fmt(light.values), tag(light)) +
            sensorCard('Сеть', (net.connected ? net.type : 'нет'), tag(net));
    } catch (e) {
        grid.innerHTML = sensorCard('Ошибка', e.message);
    }
}

async function readLocation() {
    const grid = document.getElementById('sensorGrid');
    try {
        // Спросить разрешение в нужный момент, затем прочитать датчик
        const grant = await enpaf.permissions.request(['FINE_LOCATION']);
        if (grant.denied && grant.denied.length) {
            grid.innerHTML = sensorCard('Геолокация', 'доступ не выдан');
            return;
        }
        const loc = await enpaf.sensors.location();
        grid.innerHTML = loc.fix
            ? sensorCard('Широта', (+loc.latitude).toFixed(5)) +
              sensorCard('Долгота', (+loc.longitude).toFixed(5)) +
              sensorCard('Точность (м)', Math.round(loc.accuracy), loc.dev ? 'dev-заглушка' : loc.provider)
            : sensorCard('Геолокация', 'нет данных', loc.note || '');
    } catch (e) {
        grid.innerHTML = sensorCard('Ошибка', e.message);
    }
}

async function readBattery() {
    const grid = document.getElementById('sensorGrid');
    try {
        const b = await enpaf.sensors.battery();
        grid.innerHTML = sensorCard('Заряд', (b.level ?? '—') + '%',
            (b.charging ? '⚡ заряжается' : 'от батареи') + (b.dev ? ' · dev' : ''));
    } catch (e) {
        grid.innerHTML = sensorCard('Ошибка', e.message);
    }
}

// ─── NFC (read / write / lock) ───────────────────────────────

let APP_PACKAGE = '';   // this app's package id (for "URL + launch app" tags)

async function refreshNfcStatus() {
    try {
        const s = await enpaf.nfc.status();
        const el = document.getElementById('nfcStatus');
        el.textContent = s.dev ? 'dev-режим'
            : !s.present ? 'нет NFC'
            : s.enabled ? 'включён' : 'выключен';
    } catch (_) {}
}

let nfcBusy = false;   // true while an armed write/lock is awaiting a tap

async function nfcRead() {
    const out = document.getElementById('nfcResult');
    out.textContent = 'Чтение…';
    try {
        const r = await enpaf.nfc.read();
        if (!r.tag) { out.textContent = r.note || 'Метка не найдена'; return; }
        const text = (r.records || []).map(rec =>
            rec.type === 'text' ? `📝 ${rec.text}` :
            rec.type === 'uri' ? `🔗 ${rec.uri}` : `· ${rec.bytes || rec.type}`).join('<br>');
        out.innerHTML = `<b>ID:</b> ${r.id || '—'}<br>${text || '(пустая метка)'}` +
            (r.writable === false ? '<br><i>🔒 только чтение</i>' : '') +
            (r.dev ? '<br><small>dev-заглушка</small>' : '');
    } catch (e) { out.textContent = 'Ошибка: ' + e.message; }
}

function nfcTypeChange() {
    const t = document.getElementById('nfcType').value;
    const a = document.getElementById('nfcA'), b = document.getElementById('nfcB');
    const ph = { text: 'Текст для записи…', uri: 'https://example.com',
        app: 'com.android.chrome', email: 'mail@example.com',
        tel: '+7 999 123-45-67', wifi: 'Имя сети (SSID)', contact: 'Имя' };
    a.placeholder = ph[t] || '';
    if (t === 'wifi') { b.style.display = ''; b.placeholder = 'Пароль Wi-Fi'; }
    else if (t === 'contact') { b.style.display = ''; b.placeholder = 'Телефон'; }
    else { b.style.display = 'none'; b.value = ''; }
}

async function nfcWrite() {
    const out = document.getElementById('nfcResult');
    const t = document.getElementById('nfcType').value;
    const a = document.getElementById('nfcA').value.trim();
    const b = document.getElementById('nfcB').value.trim();
    // Arm the write, then ask the user to tap the tag (handle stays valid).
    out.innerHTML = '📲 <b>Поднесите метку к телефону…</b>';
    nfcBusy = true;
    try {
        let r;
        if (t === 'text') r = await enpaf.nfc.armText(a);
        else if (t === 'uri') r = await enpaf.nfc.armUri(a);
        else if (t === 'app') r = await enpaf.nfc.armApp(a);
        else if (t === 'email') r = await enpaf.nfc.armUri('mailto:' + a);
        else if (t === 'tel') r = await enpaf.nfc.armUri('tel:' + a.replace(/[^+\d]/g, ''));
        else if (t === 'wifi') r = await enpaf.nfc.armWifi(a, b);
        else if (t === 'contact') r = await enpaf.nfc.armContact({ name: a, phone: b });
        if (r.written) {
            const v = (r.verify || []).map(rec =>
                rec.type === 'uri' ? `🔗 ${rec.uri}` :
                rec.type === 'text' ? `📝 ${rec.text}` : `· ${rec.type}`).join('<br>');
            out.innerHTML = `✅ Записано (${t})` + (r.dev ? ' — dev-режим' : '') +
                (v ? `<br><small>На метке сейчас:</small><br>${v}` : '') +
                '<br><small>Выйдите из приложения и поднесите метку.</small>';
        } else {
            out.textContent = '⚠️ ' + (r.note || r.error || 'не удалось');
        }
        enpaf.device.vibrate(60);
    } catch (e) { out.textContent = 'Ошибка: ' + e.message; }
    finally { nfcBusy = false; }
}

async function nfcLock() {
    const out = document.getElementById('nfcResult');
    if (!confirm('Заблокировать метку НАВСЕГДА (только чтение)? Это необратимо.')) return;
    out.innerHTML = '📲 <b>Поднесите метку для блокировки…</b>';
    nfcBusy = true;
    try {
        const r = await enpaf.nfc.armLock();
        out.textContent = r.locked
            ? '🔒 Метка заблокирована (только чтение)' + (r.dev ? ' (dev)' : '')
            : '⚠️ ' + (r.note || r.error || 'не удалось');
    } catch (e) { out.textContent = 'Ошибка: ' + e.message; }
    finally { nfcBusy = false; }
}

// Авто-чтение, когда метку поднесли к телефону (но не во время записи)
if (typeof enpaf !== 'undefined') {
    enpaf.nfc.onTag((tag) => {
        if (nfcBusy) return;   // идёт запись/блокировка — не мешаем
        document.getElementById('nfcResult').textContent = '🏷️ Метка ' + (tag.id || '') + ' — чтение…';
        nfcRead();
    });
    enpaf.ready(async () => {
        refreshNfcStatus();
        try { const c = await enpaf.call('__enpaf_get_config', {}); APP_PACKAGE = (c && c.package) || ''; } catch (_) {}
    });
}

// ─── Camera (WebView getUserMedia) ───────────────────────────

let camStream = null, camFacing = 'environment';

async function camStart() {
    const v = document.getElementById('cam'), h = document.getElementById('camHint');
    try {
        if (enpaf.isAndroid) await enpaf.permissions.request(['CAMERA']);
        camStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: camFacing }, audio: false });
        v.srcObject = camStream; v.style.display = 'block';
        document.getElementById('shot').style.display = 'none';
        h.textContent = 'Камера включена';
    } catch (e) { h.textContent = 'Ошибка камеры: ' + e.message; }
}
function camStop() {
    if (camStream) { camStream.getTracks().forEach(t => t.stop()); camStream = null; }
    document.getElementById('camHint').textContent = 'Камера выключена';
}
async function camFlip() {
    camFacing = camFacing === 'environment' ? 'user' : 'environment';
    if (camStream) { camStop(); await camStart(); }
}
function camShot() {
    const v = document.getElementById('cam'); if (!camStream) return;
    const c = document.createElement('canvas');
    c.width = v.videoWidth; c.height = v.videoHeight;
    c.getContext('2d').drawImage(v, 0, 0);
    const img = document.getElementById('shot');
    img.src = c.toDataURL('image/png'); img.style.display = 'block';
    document.getElementById('camHint').textContent = 'Снимок сделан ✓';
}

// ─── Bluetooth (discover / connect / chat) ───────────────────

let btSeen = {};
async function btRefreshStatus() {
    try {
        const s = await enpaf.bluetooth.status();
        document.getElementById('btStatus').textContent =
            s.dev ? 'dev-режим' : (s.enabled ? ('вкл' + (s.name ? ' · ' + s.name : '')) : 'выключен');
    } catch (_) {}
}
function btDevRow(d, paired) {
    if (!d.address || btSeen[d.address]) return; btSeen[d.address] = true;
    const list = document.getElementById('btList');
    if (list.querySelector('.empty-state')) list.innerHTML = '';
    const el = document.createElement('div'); el.className = 'dev-row';
    el.innerHTML = `<div><div class="dev-name">${d.name || '(без имени)'}</div>
        <div class="dev-sub">${d.address}${paired ? ' · сопряжён' : ''}${d.rssi ? ' · ' + d.rssi + ' dBm' : ''}</div></div>`;
    const b = document.createElement('button'); b.className = 'btn btn-primary btn-sm'; b.textContent = 'Подключить';
    b.onclick = () => { enpaf.bluetooth.stopDiscovery(); enpaf.bluetooth.connect(d.address);
        document.getElementById('btStatus').textContent = 'Подключение к ' + (d.name || d.address) + '…'; };
    el.appendChild(b); list.appendChild(el);
}
async function btDiscover() {
    if (enpaf.isAndroid) await enpaf.permissions.request(['BLUETOOTH_SCAN', 'BLUETOOTH_CONNECT', 'FINE_LOCATION']);
    btSeen = {};
    document.getElementById('btList').innerHTML = '<div class="empty-state"><span class="empty-icon">🔎</span><p>Поиск…</p></div>';
    const p = await enpaf.bluetooth.paired(); (p.devices || []).forEach(d => btDevRow(d, true));
    await enpaf.bluetooth.discover();
}
async function btListen() {
    if (enpaf.isAndroid) await enpaf.permissions.request(['BLUETOOTH_CONNECT']);
    await enpaf.bluetooth.listen('ENPAF');
    document.getElementById('btStatus').textContent = 'Жду подключение…';
}
function btLog(text, me) {
    const log = document.getElementById('btLog');
    const d = document.createElement('div'); d.className = 'msg ' + (me ? 'me' : 'them'); d.textContent = text;
    log.appendChild(d); log.scrollTop = log.scrollHeight;
}
function btSend() {
    const i = document.getElementById('btMsg'); if (!i.value.trim()) return;
    enpaf.bluetooth.send(i.value); btLog(i.value, true); i.value = '';
}
function btDisconnect() { enpaf.bluetooth.disconnect(); document.getElementById('btChat').style.display = 'none'; }

// ─── Wi-Fi (scan / connect) ──────────────────────────────────

let wifiSeen = {};
async function wifiRefreshStatus() {
    try {
        const s = await enpaf.wifi.status();
        document.getElementById('wifiStatus').textContent =
            s.dev ? 'dev-режим' : (s.enabled ? ('вкл' + (s.ssid ? ' · ' + s.ssid : '')) : 'выключен');
    } catch (_) {}
}
function wifiRow(n) {
    if (!n.ssid || wifiSeen[n.ssid]) return; wifiSeen[n.ssid] = true;
    const list = document.getElementById('wifiList');
    if (list.querySelector('.empty-state')) list.innerHTML = '';
    const el = document.createElement('div'); el.className = 'dev-row';
    el.innerHTML = `<div><div class="dev-name">${n.secure ? '🔒 ' : ''}${n.ssid}</div>
        <div class="dev-sub">${n.rssi} dBm</div></div>`;
    const b = document.createElement('button'); b.className = 'btn btn-primary btn-sm'; b.textContent = 'Подключить';
    b.onclick = async () => {
        const pw = n.secure ? prompt('Пароль для ' + n.ssid) : '';
        if (n.secure && pw === null) return;
        const r = await enpaf.wifi.connect(n.ssid, pw || '');
        document.getElementById('wifiStatus').textContent = r.ok ? ('→ ' + n.ssid) : ('ошибка: ' + (r.error || r.note || ''));
    };
    el.appendChild(b); list.appendChild(el);
}
async function wifiScan() {
    if (enpaf.isAndroid) await enpaf.permissions.request(['FINE_LOCATION']);
    wifiSeen = {};
    document.getElementById('wifiList').innerHTML = '<div class="empty-state"><span class="empty-icon">🔎</span><p>Сканирование…</p></div>';
    await enpaf.wifi.scan();
}

// Wire module events once the bridge is up. Guard each namespace so a stale
// enpaf.js (missing one) can't break the rest.
if (typeof enpaf !== 'undefined') {
    if (enpaf.bluetooth) {
        enpaf.bluetooth.onFound(d => btDevRow(d, false));
        enpaf.bluetooth.onConnected(d => {
            document.getElementById('btStatus').textContent = '✅ ' + (d.name || d.address) + (d.role ? ' (' + d.role + ')' : '');
            document.getElementById('btChat').style.display = 'block';
            document.getElementById('btLog').innerHTML = '';
        });
        enpaf.bluetooth.onData(d => btLog(d.text, false));
        enpaf.bluetooth.onDisconnected(() => { document.getElementById('btStatus').textContent = 'отключено'; });
        enpaf.bluetooth.onDiscoveryFinished(() => {
            const l = document.getElementById('btList');
            if (l.querySelector('.empty-state')) l.innerHTML = '<div class="empty-state"><span class="empty-icon">🤷</span><p>Устройства не найдены</p></div>';
        });
        enpaf.bluetooth.onError(d => { document.getElementById('btStatus').textContent = '⚠️ ' + (d.error || ''); });
    }
    if (enpaf.wifi) {
        enpaf.wifi.onResult(wifiRow);
        enpaf.wifi.onFinished(() => {
            const l = document.getElementById('wifiList');
            if (l.querySelector('.empty-state')) l.innerHTML = '<div class="empty-state"><span class="empty-icon">🤷</span><p>Сети не найдены</p></div>';
        });
        enpaf.wifi.onConnected(d => { document.getElementById('wifiStatus').textContent = '✅ ' + (d.ssid || ''); });
        enpaf.wifi.onError(d => { document.getElementById('wifiStatus').textContent = '⚠️ ' + (d.error || ''); });
    }
    enpaf.ready(() => {
        if (enpaf.bluetooth) btRefreshStatus();
        if (enpaf.wifi) wifiRefreshStatus();
    });
}

// ─── Utility ─────────────────────────────────────────────────

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

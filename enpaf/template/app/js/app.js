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

// ─── Utility ─────────────────────────────────────────────────

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

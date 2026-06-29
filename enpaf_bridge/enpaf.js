/**
 * ENPAF.js — Client-side JavaScript SDK
 * Provides the bridge between JavaScript and Python backend.
 * 
 * Usage:
 *   // Call a Python function
 *   const data = await enpaf.call("get_users", { page: 1 });
 * 
 *   // Listen for events from Python
 *   enpaf.on("data_updated", (payload) => { ... });
 * 
 *   // Emit events to Python
 *   enpaf.emit("button_clicked", { id: "save" });
 * 
 *   // Storage API
 *   await enpaf.storage.set("theme", "dark");
 *   const theme = await enpaf.storage.get("theme");
 * 
 *   // Navigation
 *   enpaf.navigate("/about");
 * 
 *   // Device API
 *   enpaf.device.toast("Saved!");
 *   enpaf.device.vibrate(200);
 */

(function (global) {
    'use strict';

    // ─── Detect Environment ──────────────────────────────────
    const isAndroid = typeof window.EnpafAndroidBridge !== 'undefined';
    const hasSocketIO = typeof io !== 'undefined';

    // ─── Internal State ──────────────────────────────────────
    let _socket = null;
    let _callId = 0;
    let _pendingCalls = {};
    let _eventHandlers = {};
    let _connected = false;
    let _connectPromise = null;
    let _readyCallbacks = [];

    // ─── Generate Unique Call ID ─────────────────────────────
    function generateCallId() {
        _callId++;
        return 'call_' + _callId + '_' + Date.now();
    }

    // ─── Socket.IO Connection (Dev Mode) ─────────────────────
    function connectSocketIO() {
        if (_connectPromise) return _connectPromise;

        _connectPromise = new Promise((resolve) => {
            if (!hasSocketIO) {
                console.warn('[ENPAF] Socket.IO not available. Bridge calls will use HTTP fallback.');
                _connected = true;
                resolve();
                return;
            }

            _socket = io({
                transports: ['websocket', 'polling'],
                reconnection: true,
                reconnectionDelay: 1000,
                reconnectionAttempts: 10,
            });

            _socket.on('connect', () => {
                console.log('[ENPAF] 🔌 Connected to Python backend');
                _connected = true;
                resolve();
                _fireReady();
            });

            _socket.on('disconnect', () => {
                console.log('[ENPAF] 🔌 Disconnected from Python backend');
                _connected = false;
            });

            _socket.on('reconnect', () => {
                console.log('[ENPAF] 🔌 Reconnected to Python backend');
                _connected = true;
            });

            // Handle events from Python
            _socket.on('enpaf_event', (data) => {
                const event = data.event;
                const payload = data.data;
                _fireEvent(event, payload);
            });

            // Timeout - connect anyway after 3s
            setTimeout(() => {
                if (!_connected) {
                    console.warn('[ENPAF] Connection timeout, proceeding without WebSocket');
                    _connected = true;
                    resolve();
                }
            }, 3000);
        });

        return _connectPromise;
    }

    // ─── Fire Event Handlers ─────────────────────────────────
    function _fireEvent(event, data) {
        const handlers = _eventHandlers[event] || [];
        handlers.forEach(handler => {
            try {
                handler(data);
            } catch (e) {
                console.error(`[ENPAF] Event handler error (${event}):`, e);
            }
        });
    }

    function _fireReady() {
        _readyCallbacks.forEach(cb => {
            try { cb(); } catch (e) { console.error('[ENPAF] Ready callback error:', e); }
        });
        _readyCallbacks = [];
    }

    // ─── Call Python Function (via SocketIO) ─────────────────
    function callViaSocketIO(name, params) {
        return new Promise((resolve, reject) => {
            if (!_socket || !_connected) {
                // Fallback to HTTP
                callViaHTTP(name, params).then(resolve).catch(reject);
                return;
            }

            const callId = generateCallId();
            const timeout = setTimeout(() => {
                delete _pendingCalls[callId];
                reject(new Error(`Bridge call '${name}' timed out (10s)`));
            }, 10000);

            _socket.emit('enpaf_call', {
                name: name,
                params: params || {},
                callId: callId,
            }, (response) => {
                clearTimeout(timeout);
                if (response && response.success) {
                    resolve(response.data);
                } else {
                    reject(new Error(response ? response.error : 'Unknown bridge error'));
                }
            });
        });
    }

    // ─── Call Python Function (via HTTP fallback) ────────────
    async function callViaHTTP(name, params) {
        let response;
        try {
            response = await fetch('/enpaf-api/bridge-call', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, params: params || {} }),
            });
        } catch (e) {
            throw new Error(`Bridge call '${name}' failed: ${e.message}`);
        }

        // Read the body as text first so a non-JSON (e.g. HTML error) response
        // produces a readable error instead of "Unexpected token '<'".
        const raw = await response.text();
        let data;
        try {
            data = raw ? JSON.parse(raw) : {};
        } catch (e) {
            const snippet = raw.slice(0, 120).replace(/\s+/g, ' ').trim();
            throw new Error(`Bridge call '${name}' got a non-JSON response ` +
                `(HTTP ${response.status}): ${snippet}`);
        }

        // Accept the standard {success, data, error} envelope. Also tolerate a
        // legacy {result: ...} shape for backwards compatibility.
        if (data && typeof data.success === 'boolean') {
            if (data.success) return data.data;
            throw new Error(data.error || `Bridge call '${name}' failed`);
        }
        if (data && 'result' in data) return data.result;
        throw new Error(data && data.error ? data.error : `Bridge call '${name}' failed`);
    }

    // ─── Call Python Function (via Android Bridge) ───────────
    function callViaAndroid(name, params) {
        return new Promise((resolve, reject) => {
            try {
                const callId = generateCallId();
                _pendingCalls[callId] = { resolve, reject };

                const result = window.EnpafAndroidBridge.call(
                    name,
                    JSON.stringify(params || {}),
                    callId
                );

                // If synchronous result
                if (result !== undefined && result !== null) {
                    delete _pendingCalls[callId];
                    try {
                        const parsed = JSON.parse(result);
                        if (parsed.success) {
                            resolve(parsed.data);
                        } else {
                            reject(new Error(parsed.error));
                        }
                    } catch (e) {
                        resolve(result);
                    }
                }
            } catch (e) {
                reject(e);
            }
        });
    }

    // ─── Android Bridge Callback (called from Java) ──────────
    global.__enpaf_callback = function (callId, success, data) {
        const pending = _pendingCalls[callId];
        if (pending) {
            delete _pendingCalls[callId];
            if (success) {
                try {
                    pending.resolve(JSON.parse(data));
                } catch (e) {
                    pending.resolve(data);
                }
            } else {
                pending.reject(new Error(data));
            }
        }
    };

    // ─── Android Event Receiver (called from Java) ───────────
    global.__enpaf_event = function (event, dataJson) {
        try {
            const data = JSON.parse(dataJson);
            _fireEvent(event, data);
        } catch (e) {
            _fireEvent(event, dataJson);
        }
    };

    // ═══════════════════════════════════════════════════════
    // PUBLIC API
    // ═══════════════════════════════════════════════════════

    const enpaf = {
        /** Framework version */
        version: '1.0.0',

        /** Whether running on Android */
        isAndroid: isAndroid,

        /** Whether the bridge is connected */
        get connected() { return _connected; },

        /**
         * Call a Python function.
         * @param {string} name - Function name registered with @app.bridge_handler()
         * @param {object} params - Parameters to pass
         * @returns {Promise<any>} Result from Python
         * 
         * @example
         * const users = await enpaf.call("get_users", { page: 1 });
         */
        async call(name, params) {
            if (isAndroid) {
                return callViaAndroid(name, params);
            } else {
                await connectSocketIO();
                return callViaSocketIO(name, params);
            }
        },

        /**
         * Listen for an event from Python.
         * @param {string} event - Event name
         * @param {function} handler - Event handler
         * 
         * @example
         * enpaf.on("data_updated", (data) => {
         *     console.log("Data updated:", data);
         * });
         */
        on(event, handler) {
            if (!_eventHandlers[event]) {
                _eventHandlers[event] = [];
            }
            _eventHandlers[event].push(handler);
        },

        /**
         * Remove an event listener.
         * @param {string} event - Event name
         * @param {function} handler - Handler to remove (optional, removes all if omitted)
         */
        off(event, handler) {
            if (!handler) {
                delete _eventHandlers[event];
            } else {
                const handlers = _eventHandlers[event] || [];
                _eventHandlers[event] = handlers.filter(h => h !== handler);
            }
        },

        /**
         * Emit an event to Python.
         * @param {string} event - Event name
         * @param {any} data - Event data
         */
        emit(event, data) {
            if (isAndroid) {
                window.EnpafAndroidBridge.emit(event, JSON.stringify(data || {}));
            } else if (_socket && _connected) {
                _socket.emit('enpaf_event', { event, data });
            }
        },

        /**
         * Navigate to a page.
         * @param {string} path - Page path (e.g., "/about")
         */
        navigate(path) {
            if (path.startsWith('http')) {
                window.location.href = path;
            } else {
                window.location.href = path;
            }
        },

        /**
         * Register a callback for when the bridge is ready.
         * @param {function} callback
         */
        ready(callback) {
            if (_connected) {
                callback();
            } else {
                _readyCallbacks.push(callback);
            }
        },

        // ─── Storage API ─────────────────────────────────────
        storage: {
            /**
             * Get a value from storage.
             * @param {string} key
             * @returns {Promise<any>}
             */
            async get(key) {
                const result = await enpaf.call('__enpaf_storage_get', { key });
                return result ? result.value : null;
            },

            /**
             * Set a value in storage.
             * @param {string} key
             * @param {any} value
             */
            async set(key, value) {
                await enpaf.call('__enpaf_storage_set', { key, value });
            },

            /**
             * Delete a value from storage.
             * @param {string} key
             */
            async delete(key) {
                await enpaf.call('__enpaf_storage_delete', { key });
            },
        },

        // ─── Device API ──────────────────────────────────────
        device: {
            /**
             * Show a toast notification.
             * @param {string} message
             * @param {string} duration - "short" or "long"
             */
            toast(message, duration) {
                if (isAndroid) {
                    window.EnpafAndroidBridge.toast(message, duration || 'short');
                } else {
                    // Dev mode: show a CSS toast
                    _showDevToast(message);
                }
            },

            /**
             * Vibrate the device.
             * @param {number} ms - Duration in milliseconds
             */
            vibrate(ms) {
                if (isAndroid) {
                    window.EnpafAndroidBridge.vibrate(ms || 100);
                } else if (navigator.vibrate) {
                    navigator.vibrate(ms || 100);
                }
            },

            /**
             * Get device info.
             * @returns {Promise<object>}
             */
            async getInfo() {
                return enpaf.call('__enpaf_ping', {});
            },

            /**
             * Share text.
             * @param {string} text
             * @param {string} title
             */
            share(text, title) {
                if (navigator.share) {
                    navigator.share({ text, title });
                } else if (isAndroid) {
                    window.EnpafAndroidBridge.share(text, title || '');
                }
            },

            /**
             * Show a system notification.
             * @param {string} title
             * @param {string} text
             * @param {number} id - notification id (default 1)
             */
            notify(title, text, id) {
                if (isAndroid) {
                    window.EnpafAndroidBridge.notify(title, text || '', id || 1);
                } else if ('Notification' in window) {
                    if (Notification.permission === 'granted') {
                        new Notification(title, { body: text });
                    } else if (Notification.permission !== 'denied') {
                        Notification.requestPermission().then(p => {
                            if (p === 'granted') new Notification(title, { body: text });
                        });
                    }
                } else {
                    _showDevToast(title + (text ? ': ' + text : ''));
                }
            },

            /**
             * Lock or release screen orientation.
             * @param {string} mode - "portrait", "landscape" or "auto"
             */
            setOrientation(mode) {
                if (isAndroid) {
                    window.EnpafAndroidBridge.setOrientation(mode || 'auto');
                } else {
                    console.log('[ENPAF] setOrientation:', mode);
                }
            },

            /**
             * Copy text to the clipboard.
             * @param {string} text
             */
            clipboard(text) {
                if (isAndroid) {
                    window.EnpafAndroidBridge.clipboardSet(text);
                } else if (navigator.clipboard) {
                    navigator.clipboard.writeText(text);
                }
            },

            /**
             * Open a URL in the system browser.
             * @param {string} url
             */
            openUrl(url) {
                if (isAndroid) {
                    window.EnpafAndroidBridge.openUrl(url);
                } else {
                    window.open(url, '_blank');
                }
            },
        },

        /**
         * Low-level gateway to the Python DeviceAPI (sensors, permissions,
         * device features). Prefer the `sensors` / `permissions` helpers below.
         * @param {string} method - DeviceAPI method name
         * @param {object} args - keyword arguments
         */
        api(method, args) {
            return enpaf.call('__enpaf_api', { method, args: args || {} });
        },

        // ─── Sensors & device readings (read from Python) ────
        sensors: {
            /** Read one snapshot from a sensor: "accelerometer", "gyroscope",
             *  "magnetometer", "light", "proximity", "pressure", ... */
            read(name, opts) { return enpaf.api('read_sensor', { sensor: name, ...(opts || {}) }); },
            /** List hardware sensors present on the device. */
            list() { return enpaf.api('list_sensors', {}); },
            /** Last known location {latitude, longitude, accuracy, ...}. */
            location() { return enpaf.api('get_location', {}); },
            /** Bluetooth adapter state + bonded devices. */
            bluetooth() { return enpaf.api('get_bluetooth', {}); },
            /** NFC adapter presence/state. */
            nfc() { return enpaf.api('get_nfc', {}); },
            /** Microphone peak amplitude (needs RECORD_AUDIO). */
            audioLevel(duration) { return enpaf.api('get_audio_level', duration ? { duration } : {}); },
            /** Battery level + charging state. */
            battery() { return enpaf.api('get_battery', {}); },
            /** Network connectivity info. */
            network() { return enpaf.api('get_network', {}); },
            /** Read the most common sensors + device state in one call. */
            snapshot() { return enpaf.api('get_sensor_snapshot', {}); },
        },

        // ─── NFC: read / write (every record type) / lock ────
        nfc: {
            /** Adapter state {present, enabled}. */
            status() { return enpaf.api('get_nfc', {}); },
            /** Read NDEF content of the last-tapped tag -> {records:[...], ...}. */
            read() { return enpaf.api('nfc_read', {}); },
            /** Write a plain-text record. */
            writeText(text, lang) { return enpaf.api('nfc_write_text', { text, lang: lang || 'en' }); },
            /** Write a URL / URI record (also tel:, mailto:, geo:, sms:). */
            writeUri(uri) { return enpaf.api('nfc_write_uri', { uri }); },
            /** Write an app-launch record (AAR): opens the app or Play Store. */
            writeApp(pkg, uri) { return enpaf.api('nfc_write_app', { package: pkg, uri: uri || '' }); },
            /** Write a MIME record (e.g. "application/json", "text/vcard"). */
            writeMime(mime, data) { return enpaf.api('nfc_write_mime', { mime, data }); },
            /** Write Wi-Fi credentials (tap to join). */
            writeWifi(ssid, password, opts) {
                return enpaf.api('nfc_write_wifi', { ssid, password, ...(opts || {}) });
            },
            /** Write a contact (vCard). */
            writeContact(c) { return enpaf.api('nfc_write_contact', c || {}); },
            /** Write any list of record specs in one message. */
            writeRecords(records) { return enpaf.api('nfc_write_records', { records }); },
            /** Back-compat: write a text (or {uri}) record. */
            write(text) { return enpaf.api('nfc_write', { text }); },
            /** Permanently lock the tag to read-only (irreversible). */
            lock() { return enpaf.api('nfc_make_readonly', { confirm: true }); },
            /** Subscribe to "tag tapped" events. */
            onTag(handler) { enpaf.on('nfc_tag', handler); },
            /** Subscribe to results of armed writes. */
            onWriteResult(handler) { enpaf.on('nfc_write_result', handler); },
            /** Cancel a pending armed write. */
            cancel() { return enpaf.api('nfc_cancel_write', {}); },

            // ── Reliable "arm, then tap the tag to write" flow ──
            // Resolves once the user taps a tag (or times out). Use these
            // instead of write*() — a tag handle dies when it leaves the field.
            _arm(method, args, lock) {
                args = args || {};
                if (!enpaf.isAndroid) {              // dev: no real tag, run now
                    const run = method ? enpaf.api(method, args) : Promise.resolve({ written: true });
                    return run.then(r => lock
                        ? enpaf.api('nfc_make_readonly', { confirm: true }).then(l => ({ ...r, locked: l.locked }))
                        : r);
                }
                return new Promise((resolve) => {
                    enpaf.api('nfc_arm_write', { method: method || '', args, lock: !!lock }).then(() => {
                        const h = (res) => { enpaf.off('nfc_write_result', h); resolve(res); };
                        enpaf.on('nfc_write_result', h);
                        setTimeout(() => { enpaf.off('nfc_write_result', h);
                            resolve({ written: false, note: 'timeout — метка не поднесена' }); }, 60000);
                    });
                });
            },
            armText(text, lang) { return this._arm('nfc_write_text', { text, lang: lang || 'en' }); },
            armUri(uri) { return this._arm('nfc_write_uri', { uri }); },
            armApp(pkg, uri) { return this._arm('nfc_write_app', { package: pkg, uri: uri || '' }); },
            armMime(mime, data) { return this._arm('nfc_write_mime', { mime, data }); },
            armWifi(ssid, password, opts) { return this._arm('nfc_write_wifi', { ssid, password, ...(opts || {}) }); },
            armContact(c) { return this._arm('nfc_write_contact', c || {}); },
            armRecords(records) { return this._arm('nfc_write_records', { records }); },
            armLock() { return this._arm('', {}, true); },
        },

        // ─── Runtime permissions (request on demand) ─────────
        permissions: {
            /** Is a single permission currently granted? -> {granted: bool}. */
            check(permission) { return enpaf.api('check_permission', { permission }); },
            /** Granted/denied status for a list of permissions. */
            checkAll(list) { return enpaf.api('check_permissions', { permissions: list || [] }); },
            /**
             * Ask the user to grant permissions *now* (shows the system prompt).
             * Resolves with {granted:[...], denied:[...], results:{...}} once the
             * user responds.
             * @param {string|string[]} list - permission name(s)
             * @returns {Promise<object>}
             */
            request(list) {
                const perms = Array.isArray(list) ? list : [list];
                return new Promise((resolve) => {
                    enpaf.api('request_permissions', { permissions: perms }).then((res) => {
                        if (!res || !res.pending) { resolve(res || {}); return; }
                        const handler = (payload) => {
                            if (payload && payload.code === res.code) {
                                enpaf.off('permission_result', handler);
                                resolve(payload);
                            }
                        };
                        enpaf.on('permission_result', handler);
                        // Safety net: don't hang forever if no result arrives.
                        setTimeout(() => { enpaf.off('permission_result', handler); resolve(res); }, 120000);
                    }).catch((e) => resolve({ error: e.message }));
                });
            },
        },

        /** Gateway to a Python capability module (app.<name>). */
        mod(module, method, args) {
            return enpaf.call('__enpaf_mod', { module, method, args: args || {} });
        },

        // ─── Wi-Fi module (enpaf.wifi.*) ─────────────────────
        wifi: {
            status() { return enpaf.mod('wifi', 'status'); },
            info() { return enpaf.mod('wifi', 'info'); },
            scan() { return enpaf.mod('wifi', 'scan'); },            // -> wifi_scan_result events
            networks() { return enpaf.mod('wifi', 'networks'); },    // last results, sync
            enable() { return enpaf.mod('wifi', 'enable'); },
            connect(ssid, password) { return enpaf.mod('wifi', 'connect', { ssid, password: password || '' }); },
            disconnect() { return enpaf.mod('wifi', 'disconnect'); },
            onResult(h) { enpaf.on('wifi_scan_result', h); },
            onFinished(h) { enpaf.on('wifi_scan_finished', h); },
            onConnected(h) { enpaf.on('wifi_connected', h); },
            onError(h) { enpaf.on('wifi_error', h); },
        },

        // ─── Bluetooth module (enpaf.bluetooth.*) ────────────
        bluetooth: {
            status() { return enpaf.mod('bluetooth', 'status'); },
            enable() { return enpaf.mod('bluetooth', 'enable'); },
            paired() { return enpaf.mod('bluetooth', 'paired'); },
            discover() { return enpaf.mod('bluetooth', 'discover'); },   // -> bluetooth_device_found
            stopDiscovery() { return enpaf.mod('bluetooth', 'stop_discovery'); },
            connect(address) { return enpaf.mod('bluetooth', 'connect', { address }); },
            listen(name) { return enpaf.mod('bluetooth', 'listen', { name: name || 'ENPAF' }); },
            send(text) { return enpaf.mod('bluetooth', 'send', { text }); },
            disconnect() { return enpaf.mod('bluetooth', 'disconnect'); },
            onFound(h) { enpaf.on('bluetooth_device_found', h); },
            onConnected(h) { enpaf.on('bluetooth_connected', h); },
            onData(h) { enpaf.on('bluetooth_data', h); },
            onDisconnected(h) { enpaf.on('bluetooth_disconnected', h); },
            onDiscoveryFinished(h) { enpaf.on('bluetooth_discovery_finished', h); },
            onError(h) { enpaf.on('bluetooth_error', h); },
        },

        // ─── Media module (enpaf.media.*) ────────────────────
        media: {
            takePicture() { return enpaf.mod('media', 'take_picture'); },
            recordVideo() { return enpaf.mod('media', 'record_video'); },
            pickMedia(type) { return enpaf.mod('media', 'pick_media', { media_type: type || 'image' }); },
            recordAudio(duration) { return enpaf.mod('media', 'record_audio', { duration_sec: duration || 5 }); },
        },

        // ─── Other modules ───────────────────────────────────
        location: { get() { return enpaf.mod('location', 'get'); } },
        battery: {
            info() { return enpaf.mod('battery', 'info'); },
            network() { return enpaf.mod('battery', 'network'); },
        },
        audio: { level(duration) { return enpaf.mod('audio', 'level', duration ? { duration } : {}); } },
        notifications: { notify(opts) { return enpaf.mod('notifications', 'notify', opts || {}); } },

        // ─── Biometric (fingerprint / face / device credential) ──
        biometric: {
            /** {available, code, enrolled}. */
            available() { return enpaf.mod('biometric', 'available'); },
            /**
             * Show the system biometric prompt. Resolves with {success, error}.
             * @param {object} opts - { title, subtitle, description }
             */
            authenticate(opts) {
                opts = opts || {};
                return new Promise((resolve) => {
                    let settled = false;
                    const handler = (res) => {
                        if (settled) return;
                        settled = true;
                        enpaf.off('biometric_result', handler);
                        resolve(res || { success: false });
                    };
                    enpaf.on('biometric_result', handler);
                    enpaf.mod('biometric', 'authenticate', {
                        title: opts.title || 'Authenticate',
                        subtitle: opts.subtitle || '',
                        description: opts.description || '',
                    }).then((r) => {
                        if (r && r.started === false) handler({ success: false, error: r.error || 'not started' });
                    }).catch((e) => handler({ success: false, error: e.message }));
                    // Safety timeout
                    setTimeout(() => handler({ success: false, error: 'timeout' }), 60000);
                });
            },
        },

        // ─── Utils ───────────────────────────────────────────
        utils: {
            /**
             * Format a date.
             */
            formatDate(date, locale) {
                return new Date(date).toLocaleDateString(locale || 'ru-RU');
            },

            /**
             * Generate a unique ID.
             */
            uid() {
                return 'enpaf_' + Math.random().toString(36).substring(2, 11);
            },
        },
    };

    // ─── Dev Mode Toast ──────────────────────────────────────
    function _showDevToast(message) {
        let container = document.getElementById('enpaf-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'enpaf-toast-container';
            container.style.cssText = `
                position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
                z-index: 99999; display: flex; flex-direction: column; align-items: center; gap: 8px;
            `;
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.textContent = message;
        toast.style.cssText = `
            background: rgba(30, 30, 30, 0.92); color: #fff; padding: 12px 24px;
            border-radius: 12px; font-size: 14px; font-family: -apple-system, BlinkMacSystemFont, 
            'Segoe UI', Roboto, sans-serif; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            backdrop-filter: blur(10px); opacity: 0; transition: opacity 0.3s ease;
            max-width: 80vw; text-align: center;
        `;
        container.appendChild(toast);

        requestAnimationFrame(() => { toast.style.opacity = '1'; });
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 2500);
    }

    // ─── Auto-Connect ────────────────────────────────────────
    if (!isAndroid && hasSocketIO) {
        connectSocketIO();
    } else if (isAndroid) {
        _connected = true;
        setTimeout(_fireReady, 0);
    } else {
        // No SocketIO, no Android — just mark as connected for basic usage
        _connected = true;
        setTimeout(_fireReady, 100);
    }

    // ─── Lifecycle Events ────────────────────────────────────
    if (typeof window !== 'undefined') {
        const sendPageLoad = () => {
            enpaf.ready(() => {
                enpaf.emit('page_load', { path: window.location.pathname });
            });
        };
        if (document.readyState === 'loading') {
            window.addEventListener('DOMContentLoaded', sendPageLoad);
        } else {
            sendPageLoad();
        }
        window.addEventListener('beforeunload', () => {
            enpaf.emit('page_unload', { path: window.location.pathname });
        });
    }

    // ─── Export ──────────────────────────────────────────────
    global.enpaf = enpaf;

    // Also support ES modules
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = enpaf;
    }

    console.log('[ENPAF] 🚀 Bridge v' + enpaf.version + (isAndroid ? ' (Android)' : ' (Dev)'));

})(typeof window !== 'undefined' ? window : global);

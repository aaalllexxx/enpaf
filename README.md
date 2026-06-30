# 🚀 ENPAF — Engine for Native Python App Framework

[![CI](https://github.com/aaalllexxx/enpaf/actions/workflows/ci.yml/badge.svg)](https://github.com/aaalllexxx/enpaf/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%E2%80%933.13-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-1.1.2-informational.svg)](https://github.com/aaalllexxx/enpaf/releases)
[![License: PolyForm NC 1.0.0](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-orange.svg)](LICENSE)

**Создавайте Android-приложения на Python + HTML/CSS/JS и собирайте их в APK.**

> 📖 **Полная документация — в [Wiki](https://github.com/aaalllexxx/enpaf/wiki).**
> 💾 Готовые сборки (wheel фреймворка + APK приложений) — на странице
> [Releases](https://github.com/aaalllexxx/enpaf/releases).
> 📄 Лицензия **PolyForm Noncommercial 1.0.0** — бесплатно для некоммерческого
> использования, для коммерческого нужна платная лицензия (см. [Лицензия](#-лицензия)).

ENPAF — это фреймворк, который позволяет писать мобильные приложения, используя
привычный веб-стек (HTML/CSS/JS) для интерфейса и **Python** для логики. В режиме
разработки приложение работает как обычный сайт (Flask + WebSocket + hot-reload), а
готовый продукт собирается в настоящий **APK** на базе WebView + встроенного Python
(Chaquopy).

```
┌──────────────────────── Android APK ────────────────────────┐
│   ┌────────────┐   Bridge (JSON)   ┌────────────────────┐   │
│   │  WebView   │ ◄───────────────► │   Python (main.py) │   │
│   │ HTML/CSS/JS│                   │   enpaf core       │   │
│   │ + enpaf.js │                   │   ваш код          │   │
│   └────────────┘                   └────────────────────    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📑 Содержание

- [Возможности](#-возможности)
- [Установка](#-установка)
- [Требования](#-требования)
- [Быстрый старт](#-быстрый-старт)
- [Создание базового приложения с нуля](#-создание-базового-приложения-с-нуля)
- [CLI: команда `paf`](#-cli-команда-paf)
- [Структура проекта](#-структура-проекта)
- [Конфигурация `enpaf.json`](#-конфигурация-enpafjson)
- [Python API](#-python-api)
- [JavaScript SDK (`enpaf.js`)](#-javascript-sdk-enpafjs)
- [Датчики и сенсоры устройства](#-датчики-и-сенсоры-устройства)
- [Модули устройства (Wi-Fi, Bluetooth, камера…)](#-модули-устройства-wi-fi-bluetooth-камера)
- [NFC: чтение и запись меток](#-nfc-чтение-и-запись-меток)
- [Запрос разрешений во время работы (runtime)](#-запрос-разрешений-во-время-работы-runtime)
- [Панель настроек ⚙](#-панель-настроек-)
- [Разрешения и фичи устройства](#-разрешения-и-фичи-устройства)
- [Deep links (диплинки)](#-deep-links-диплинки)
- [Уведомления и нативные возможности](#-уведомления-и-нативные-возможности)
- [Сборка APK](#-сборка-apk)
- [Тесты и CI](#-тесты-и-ci)
- [Что можно импортировать](#-что-можно-импортировать)
- [Решение проблем](#-решение-проблем)
- [Документация (Wiki)](#-документация-wiki)
- [Лицензия](#-лицензия)

---

## ✨ Возможности

- 🐍 **Python для логики**, HTML/CSS/JS для интерфейса.
- 🔗 **Двусторонний мост** Python ↔ JavaScript (вызовы и события).
- 💾 **Встроенное хранилище** — key-value и коллекции на SQLite.
- ⚡ **Hot-reload** в режиме разработки.
- ⚙️ **Веб-панель настроек** — иконка, имя, ориентация, цвета, разрешения, фичи и диплинки настраиваются прямо в браузере и пишутся в `enpaf.json`.
- 📱 **Нативные API** — toast, вибрация, уведомления, буфер обмена, шаринг, ориентация.
- 🛰 **Чтение датчиков из Python** — геолокация, акселерометр, гироскоп, магнитометр,
  освещённость, NFC, Bluetooth, микрофон, батарея, сеть.
- 🧩 **Модули устройства** — `app.wifi`, `app.bluetooth`, `app.location`, `app.sensors`,
  `app.nfc`, `app.battery`, `app.audio`… единый стиль `app.<имя>` / `enpaf.<имя>.*`
  (камера — прямо в WebView).
- 📶 **Bluetooth и Wi-Fi** — поиск устройств/сетей, подключение, обмен сообщениями.
- 📷 **Камера** прямо в WebView (live‑превью + снимок).
- 🔐 **Разрешения по запросу** — запрашивайте доступ **в нужный момент** прямой функцией
  из Python (`app.api.request_permissions([...])`), а не при запуске.
- 🧩 **`uses-feature`** (камера, NFC, датчики, Bluetooth, GPS…).
- 🔗 **Deep links** (кастомные схемы и App Links).
- 📦 **Сборка в APK/AAB** на Windows/macOS/Linux через Gradle + Chaquopy.

---

## 📥 Установка

### Из исходников (рекомендуется)

```bash
git clone https://github.com/aaalllexxx/enpaf
cd enpaf
pip install setuptools wheel        # нужны для установки
pip install -e .                    # editable: правки сразу подхватываются
```

После установки доступна команда `paf` и пакет `enpaf` для импорта. Editable‑режим
удобен тем, что изменения в коде фреймворка применяются без переустановки.

### Из релиза (wheel)

Скачайте `enpaf-<версия>-py3-none-any.whl` со страницы
[Releases](https://github.com/aaalllexxx/enpaf/releases) и установите:

```bash
pip install enpaf-1.1.2-py3-none-any.whl
```

---

## 📋 Требования

| Что | Зачем | Версия |
|-----|-------|--------|
| **Python** | фреймворк и CLI | 3.9+ |
| **Java JDK** | сборка APK | **17–21** (рекомендуется 17) |
| **Android SDK** | сборка APK | Android Studio или command-line tools |

> Для **разработки** (`paf run`) нужен только Python. JDK и Android SDK нужны
> только для **сборки APK** (`paf build`). Проверить окружение: `paf doctor`.

---

## ⚡ Быстрый старт

```bash
paf create myapp          # создать проект
cd myapp
paf run                   # запустить dev-сервер → http://127.0.0.1:8080
# ... разрабатываете, правите app/ и main.py, страница перезагружается сама ...
paf build apk             # собрать APK → dist/myapp-1.0.0.apk
```

Установить APK на телефон:

```bash
adb install dist/myapp-1.0.0.apk
# либо просто перекиньте .apk на телефон и откройте
```

---

## 🧱 Создание базового приложения с нуля

Соберём небольшое приложение **«Заметки + датчик»**: кнопка зовёт Python, заметки
хранятся в SQLite, а отдельная кнопка читает геолокацию с устройства (предварительно
запросив разрешение). Все файлы — настоящие, можно копировать как есть.

### Шаг 1. Создать проект

```bash
paf create myapp
cd myapp
```

Получится дерево (см. [Структура проекта](#-структура-проекта)). Дальше правим четыре
файла: `enpaf.json`, `main.py`, `app/index.html`, `app/js/app.js`.

### Шаг 2. `enpaf.json` — метаданные и разрешения

`permissions` лишь **объявляют** разрешения в манифесте; сам системный диалог мы
покажем позже из Python (см. [Шаг 5](#шаг-5-mainpy--логика-на-python)).

```json
{
    "name": "MyApp",
    "package": "com.example.myapp",
    "version": "1.0.0",
    "orientation": "portrait",
    "permissions": ["INTERNET", "FINE_LOCATION", "VIBRATE"],
    "features": [
        { "key": "GPS", "required": false }
    ],
    "min_sdk": 24,
    "target_sdk": 34,
    "theme": { "primary_color": "#6C5CE7", "status_bar_color": "#5A4BD1" }
}
```

### Шаг 3. `app/index.html` — интерфейс

`enpaf.js` подключать **не нужно**: dev-сервер и сборщик APK внедряют мост сами.

```html
<!-- файл: app/index.html -->
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>MyApp</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <h1>MyApp</h1>

    <button onclick="sayHello()">Поздороваться с Python</button>
    <div id="greeting"></div>

    <h2>Заметки</h2>
    <input id="noteInput" placeholder="Текст заметки…">
    <button onclick="addNote()">Добавить</button>
    <ul id="notes"></ul>

    <h2>Где я?</h2>
    <button onclick="whereAmI()">Узнать геолокацию</button>
    <div id="location"></div>

    <!-- ваш код приложения -->
    <script src="js/app.js"></script>
</body>
</html>
```

### Шаг 4. `app/js/app.js` — фронтенд-логика

Весь обмен с Python идёт через глобальный объект `window.enpaf` (он готов после
загрузки страницы; дождаться можно через `enpaf.ready(...)`).

```javascript
// файл: app/js/app.js

// Вызвать Python-функцию "hello" (зарегистрирована в main.py)
async function sayHello() {
    const res = await enpaf.call("hello", { name: "Alex" });
    document.getElementById("greeting").textContent = res.message;
}

// Сохранить заметку через Python -> SQLite
async function addNote() {
    const input = document.getElementById("noteInput");
    if (!input.value.trim()) return;
    await enpaf.call("save_note", { text: input.value.trim() });
    input.value = "";
    loadNotes();
}

// Загрузить заметки из Python
async function loadNotes() {
    const { notes } = await enpaf.call("get_notes", {});
    document.getElementById("notes").innerHTML =
        notes.map(n => `<li>${n.text}</li>`).join("");
}

// Запросить разрешение на геолокацию в нужный момент, затем прочитать датчик
async function whereAmI() {
    const out = document.getElementById("location");

    // Системный диалог появится именно сейчас, по нажатию кнопки:
    const grant = await enpaf.permissions.request(["FINE_LOCATION"]);
    if (grant.denied && grant.denied.length) {
        out.textContent = "Доступ к геолокации не выдан";
        return;
    }

    const loc = await enpaf.sensors.location();
    out.textContent = loc.fix
        ? `Широта ${loc.latitude}, долгота ${loc.longitude}`
        : "Координаты пока недоступны";
}

// Подгрузить заметки сразу после готовности моста
enpaf.ready(loadNotes);
```

### Шаг 5. `main.py` — логика на Python

```python
# файл: main.py
from enpaf import EnpafApp

app = EnpafApp(__name__)


# ─── Страница ────────────────────────────────────────────────
@app.route("/")
def index():
    return app.render("index.html", title=app.name)


# ─── Bridge-функции (их зовёт app/js/app.js через enpaf.call) ─
@app.bridge_handler("hello")
def hello(params):
    name = params.get("name", "World")
    app.api.vibrate(150)                       # нативная вибрация
    return {"message": f"Привет, {name}! 👋"}


@app.bridge_handler("save_note")
def save_note(params):
    text = params.get("text", "").strip()
    if not text:
        return {"success": False}
    note_id = app.storage.collection("notes").add({"text": text})
    return {"success": True, "id": note_id}


@app.bridge_handler("get_notes")
def get_notes(params):
    return {"notes": app.storage.collection("notes").all()}


# ─── Реакция на результат запроса разрешения (необязательно) ──
@app.on("permission_result")
def on_permission(data):
    print("Выданы:", data["granted"], "| отклонены:", data["denied"])


if __name__ == "__main__":
    app.run()
```

### Шаг 6. Запустить и собрать

```bash
paf run            # http://127.0.0.1:8080 — проверяем в браузере (hot-reload)
paf build apk      # dist/myapp-1.0.0.apk — ставим на телефон
```

> 💡 В браузере (`paf run`) датчики и разрешения возвращают **dev-заглушки**
> (например, фиксированные координаты), чтобы интерфейс можно было отладить без
> телефона. На устройстве из APK читаются реальные значения.

---

## 🛠 CLI: команда `paf`

| Команда | Описание |
|---------|----------|
| `paf create <name>` | Создать новый проект из шаблона |
| `paf run` | Запустить dev-сервер (Flask + hot-reload) |
| `paf build apk` | Собрать **debug** APK |
| `paf build apk --release` | Собрать **release** APK |
| `paf build aab` | Собрать **release** Android App Bundle (`.aab`) |
| `paf doctor` | Проверить окружение (Python, JDK, Android SDK) |
| `paf info` | Показать информацию о текущем проекте |
| `paf update` | Обновить PAF до последней версии (PyPI) |

**Флаги `update`:**
- `--pre` — включая пред-релизные версии

**Флаги `create`:**
- `--package`, `-p` — Android package id (по умолчанию `com.enpaf.<name>`)
- `--template`, `-t` — шаблон проекта (по умолчанию `default`)

**Флаги `run`:**
- `--host` (по умолчанию `127.0.0.1`)
- `--port` (по умолчанию `8080`)
- `--no-browser` — не открывать браузер автоматически
- `--debug` — режим отладки

**Флаги `build`:**
- `--release` — релизная сборка
- `--keystore <path>` — keystore для подписи
- `--clean` — чистая сборка (удалить кэш сборки)

---

## 🏗 Структура проекта

```
myapp/
├── app/                  # Интерфейс (HTML/CSS/JS) → попадёт в assets APK
│   ├── index.html        # Главная страница
│   ├── css/style.css
│   ├── js/app.js
│   ├── pages/            # Доп. страницы
│   └── img/
├── main.py               # Python-логика (точка входа)
├── enpaf.json            # Конфигурация проекта
├── icon.png              # (опционально) иконка приложения
├── data/                 # Локальная БД (SQLite) — создаётся автоматически
└── dist/                 # Готовые APK после сборки
```

---

## ⚙️ Конфигурация `enpaf.json`

Полный пример со всеми полями:

```json
{
    "name": "My App",
    "package": "com.example.myapp",
    "version": "1.0.0",
    "description": "My ENPAF Application",
    "author": "Developer",
    "orientation": "portrait",
    "icon": "icon.png",
    "permissions": ["INTERNET", "CAMERA", "VIBRATE"],
    "features": [
        { "key": "CAMERA", "required": true },
        { "key": "NFC", "required": false }
    ],
    "deeplinks": [
        { "label": "Open profile", "scheme": "myapp", "host": "open",
          "path": "/profile", "pathType": "prefix", "autoVerify": false }
    ],
    "python_requirements": ["requests"],
    "min_sdk": 24,
    "target_sdk": 34,
    "theme": {
        "primary_color": "#6C5CE7",
        "status_bar_color": "#5A4BD1"
    }
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | string | Название приложения (ярлык на устройстве) |
| `package` | string | Android application id, напр. `com.example.myapp` |
| `version` | string | Версия (`major.minor.patch`) |
| `description`, `author` | string | Метаданные |
| `orientation` | string | `portrait` / `landscape` / `auto` / `sensor` / `unspecified` |
| `icon` | string | Путь к иконке (PNG/JPG/WebP) относительно проекта |
| `permissions` | string[] | Список ключей разрешений (см. [таблицу](#разрешения)) |
| `features` | object[] | `{ "key": "...", "required": true|false }` (`<uses-feature>`) |
| `deeplinks` | object[] | Диплинки (см. [раздел](#-deep-links-диплинки)) |
| `python_requirements` | string[] | pip-зависимости, встраиваемые в APK через Chaquopy |
| `min_sdk` / `target_sdk` | int | Android API levels (по умолчанию 24 / 34) |
| `theme.primary_color` | string | Основной цвет (HEX) |
| `theme.status_bar_color` | string | Цвет статус-бара (HEX) |
| `log_level` | string | Уровень логирования (`INFO`, `DEBUG`, …) |

> 💡 Эти поля удобнее всего редактировать через [панель настроек ⚙](#-панель-настроек-),
> не открывая JSON вручную.

---

## 🐍 Python API

### `main.py` — точка входа

```python
from enpaf import EnpafApp

app = EnpafApp(__name__)

# ─── Маршруты страниц (Jinja2-шаблоны, режим разработки) ───
@app.route("/")
def index():
    return app.render("index.html", title=app.name)

# ─── Bridge-функции (вызываются из JavaScript) ───
@app.bridge_handler("get_user")
def get_user(params):
    user_id = params.get("id")
    return {"id": user_id, "name": "Alex"}

# ─── События жизненного цикла ───
@app.on("app_start")
def on_start():
    print("Приложение запущено!")

if __name__ == "__main__":
    app.run()
```

### Класс `EnpafApp`

```python
EnpafApp(import_name, app_dir="app", config_file="enpaf.json")
```

**Декораторы / методы:**

| Метод | Назначение |
|-------|------------|
| `@app.route(path, methods=None)` | Зарегистрировать страницу-маршрут |
| `@app.bridge_handler(name)` / `@app.bridge_func(name)` | Зарегистрировать функцию, вызываемую из JS |
| `@app.on(event)` | Подписаться на событие |
| `app.emit(event, data=None)` | Отправить событие (в Python и в JS) |
| `app.render(template, **context)` | Отрендерить Jinja2-шаблон из `app/` |
| `app.run(host, port, debug, open_browser)` | Запустить (dev-сервер или Android runtime) |

**Свойства / компоненты:**

| Свойство | Тип | Описание |
|----------|-----|----------|
| `app.config` | dict | Содержимое `enpaf.json` |
| `app.name` | str | Имя приложения |
| `app.storage` | `Storage` | Локальное хранилище |
| `app.events` | `EventEmitter` | Система событий |
| `app.bridge` | `Bridge` | Мост Python↔JS |
| `app.api` | `DeviceAPI` | Доступ к функциям устройства |
| `app.router` | `Router` | Роутер/шаблонизатор |

### Хранилище — `app.storage`

Key-value:

```python
app.storage.set("theme", "dark")          # значение (str/int/float/bool/dict/list)
theme = app.storage.get("theme", "light") # с дефолтом
app.storage.delete("theme")
app.storage.exists("theme")               # -> bool
app.storage.keys("user_%")                # LIKE-паттерн
app.storage.all()                         # -> dict всех пар
app.storage.clear()
```

Коллекции (мини документ-стор):

```python
notes = app.storage.collection("notes")
note_id = notes.add({"text": "Привет"})   # -> int (id)
notes.all()                                # -> list[dict] (+ _id, _created_at)
notes.find({"text": "Привет"})            # -> list[dict]
notes.find_one({"text": "Привет"})        # -> dict | None
notes.update(note_id, {"text": "Пока"})
notes.delete(note_id)
notes.count()                              # -> int
notes.clear()
```

> На Android БД автоматически пишется в записываемый каталог приложения
> (`getFilesDir()`), а не рядом с исходниками.

### События — `app.events`

```python
@app.on("app_start")
def _(): ...

app.events.once("page_load", handler)   # сработает один раз
app.events.off("app_start", handler)    # отписаться
app.events.emit("my_event", payload)    # вызвать
```

**Встроенные lifecycle-события:** `app_start`, `app_stop`, `app_pause`,
`app_resume`, `app_error`, `page_load`, `page_unload`, `bridge_connect`,
`bridge_disconnect`.

### Функции устройства — `app.api` (`DeviceAPI`)

```python
app.api.toast("Сохранено!", duration="short")  # "short" | "long"
app.api.vibrate(200)                            # мс
app.api.get_device_info()                       # -> dict
app.api.set_status_bar_color("#000000")
app.api.set_orientation("portrait")             # "portrait"|"landscape"|"auto"
app.api.open_url("https://example.com")
app.api.clipboard_set("текст")
app.api.clipboard_get()
app.api.share("Посмотри!", title="Моё приложение")
```

### Датчики устройства — `app.api` (читаются из Python)

Каждый метод возвращает обычный `dict` (можно сразу `return` из bridge-функции).
В режиме `paf run` (браузер) возвращается заглушка с полем `"dev": true`.

```python
# файл: main.py
@app.bridge_handler("read_sensors")
def read_sensors(params):
    return {
        "gyro":     app.api.read_sensor("gyroscope"),     # {values:[x,y,z], ...}
        "accel":    app.api.read_sensor("accelerometer"),
        "location": app.api.get_location(),               # {latitude, longitude, accuracy, ...}
        "bt":       app.api.get_bluetooth(),              # {enabled, name, bonded:[...]}
        "nfc":      app.api.get_nfc(),                    # {present, enabled}
        "mic":      app.api.get_audio_level(),            # {amplitude, db}  (нужен RECORD_AUDIO)
        "battery":  app.api.get_battery(),                # {level, charging}
        "network":  app.api.get_network(),                # {connected, type}
    }
```

| Метод | Возвращает |
|-------|------------|
| `app.api.read_sensor(name, timeout=2.0)` | Снимок датчика: `accelerometer`, `gyroscope`, `magnetometer`, `light`, `proximity`, `pressure`, `gravity`, `rotation_vector`, `step_counter`, `heart_rate`, … |
| `app.api.list_sensors()` | Список всех датчиков устройства |
| `app.api.get_location()` | Последняя известная геопозиция |
| `app.api.get_bluetooth()` | Состояние Bluetooth + сопряжённые устройства |
| `app.api.get_nfc()` | Наличие/состояние NFC |
| `app.api.get_audio_level(duration=0.4)` | Пиковая громкость с микрофона |
| `app.api.get_battery()` | Уровень заряда и зарядка |
| `app.api.get_network()` | Тип подключения к сети |
| `app.api.get_sensor_snapshot()` | Всё самое частое одним вызовом |

### Разрешения по запросу — `app.api`

```python
# файл: main.py
@app.bridge_handler("enable_mic")
def enable_mic(params):
    # Показать системный диалог именно сейчас (не при запуске приложения).
    # Результат придёт в @app.on("permission_result") и в JS-событие.
    app.api.request_permissions(["RECORD_AUDIO"])
    return {"requested": True}

@app.bridge_handler("mic_ready")
def mic_ready(params):
    return app.api.check_permission("RECORD_AUDIO")   # {granted: bool}
```

Подробнее — в разделе [Запрос разрешений во время работы](#-запрос-разрешений-во-время-работы-runtime).

---

## 🌐 JavaScript SDK (`enpaf.js`)

Мост `enpaf.js` подключается автоматически: в режиме разработки его внедряет
сервер, а при сборке APK — билдер вставляет `<script src="js/enpaf.js">` в ваши
HTML-страницы. Глобальный объект — `window.enpaf`.

### Вызовы и события

```javascript
// Вызвать Python-функцию (-> Promise)
const user = await enpaf.call("get_user", { id: 42 });

// События из Python
enpaf.on("data_updated", (payload) => console.log(payload));
enpaf.off("data_updated");

// Отправить событие в Python
enpaf.emit("button_clicked", { id: "save" });

// Готовность моста
enpaf.ready(() => console.log("bridge ready"));

// Навигация между страницами
enpaf.navigate("/pages/about.html");

enpaf.version;    // "1.0.0"
enpaf.isAndroid;  // true в APK, false в браузере
```

### Хранилище из JS

```javascript
await enpaf.storage.set("theme", "dark");
const theme = await enpaf.storage.get("theme");
await enpaf.storage.delete("theme");
```

### Функции устройства — `enpaf.device`

| Метод | Описание |
|-------|----------|
| `enpaf.device.toast(msg, dur)` | Toast-уведомление (`"short"`/`"long"`) |
| `enpaf.device.vibrate(ms)` | Вибрация |
| `enpaf.device.notify(title, text, id)` | Системное уведомление |
| `enpaf.device.share(text, title)` | Системный «Поделиться» |
| `enpaf.device.setOrientation(mode)` | `"portrait"`/`"landscape"`/`"auto"` |
| `enpaf.device.clipboard(text)` | Скопировать в буфер обмена |
| `enpaf.device.openUrl(url)` | Открыть ссылку во внешнем браузере |
| `enpaf.device.getInfo()` | Информация об окружении (Promise) |

В браузере (dev) методы используют веб-аналоги (Web Notifications, `navigator.share`,
`navigator.clipboard` и т.д.), на Android — нативные вызовы.

### Утилиты

```javascript
enpaf.utils.formatDate(Date.now(), "ru-RU");
enpaf.utils.uid();   // случайный id
```

---

## 🛰 Датчики и сенсоры устройства

Датчики читаются **в Python** ([`app.api.*`](#датчики-устройства--appapi-читаются-из-python)),
а из интерфейса удобнее всего звать их через `enpaf.sensors.*` — каждый метод
возвращает `Promise` с тем же `dict`, что и Python.

```javascript
// файл: app/js/app.js
const gyro  = await enpaf.sensors.read("gyroscope");   // {values:[x,y,z], accuracy, ...}
const loc   = await enpaf.sensors.location();          // {latitude, longitude, accuracy, fix}
const bt    = await enpaf.sensors.bluetooth();         // {enabled, name, bonded:[...]}
const nfc   = await enpaf.sensors.nfc();               // {present, enabled}
const mic   = await enpaf.sensors.audioLevel();        // {amplitude, db}
const batt  = await enpaf.sensors.battery();           // {level, charging}
const net   = await enpaf.sensors.network();           // {connected, type}
const all   = await enpaf.sensors.snapshot();          // всё одним вызовом
const list  = await enpaf.sensors.list();              // список датчиков устройства
```

| JS-метод | Python-эквивалент |
|----------|-------------------|
| `enpaf.sensors.read(name, opts?)` | `app.api.read_sensor(name)` |
| `enpaf.sensors.list()` | `app.api.list_sensors()` |
| `enpaf.sensors.location()` | `app.api.get_location()` |
| `enpaf.sensors.bluetooth()` | `app.api.get_bluetooth()` |
| `enpaf.sensors.nfc()` | `app.api.get_nfc()` |
| `enpaf.sensors.audioLevel(dur?)` | `app.api.get_audio_level()` |
| `enpaf.sensors.battery()` | `app.api.get_battery()` |
| `enpaf.sensors.network()` | `app.api.get_network()` |
| `enpaf.sensors.snapshot()` | `app.api.get_sensor_snapshot()` |

**Какие нужны разрешения:** геолокация — `FINE_LOCATION`/`COARSE_LOCATION`;
микрофон — `RECORD_AUDIO`; сопряжённые Bluetooth-устройства (Android 12+) —
`BLUETOOTH_CONNECT`; NFC — `NFC`. Добавьте их в `enpaf.json` **и** запросите во
время работы (следующий раздел). Акселерометр, гироскоп, освещённость и т.п.
runtime-разрешений не требуют.

> В браузере (`paf run`) методы возвращают правдоподобные dev-заглушки
> (`{ "dev": true, ... }`), на устройстве — реальные показания.

---

## 🧩 Модули устройства (Wi-Fi, Bluetooth, камера…)

Возможности устройства разбиты на **модули**. Каждый доступен:
- из Python как `app.<имя>` (напр. `app.wifi`, `app.bluetooth`);
- из JS как `enpaf.<имя>.*` (напр. `enpaf.wifi.scan()`).

| Модуль | Python / JS | Что умеет |
|--------|-------------|-----------|
| `wifi` | `app.wifi` / `enpaf.wifi` | состояние, скан сетей, подключение |
| `bluetooth` | `app.bluetooth` / `enpaf.bluetooth` | поиск, подключение, обмен сообщениями |
| `location` | `app.location` / `enpaf.location` | геопозиция |
| `sensors` | `app.sensors` / `enpaf.sensors` | акселерометр, гироскоп, свет… |
| `nfc` | `app.nfc` / `enpaf.nfc` | чтение/запись меток |
| `audio` | `app.audio` / `enpaf.audio` | уровень микрофона |
| `battery` | `app.battery` / `enpaf.battery` | заряд, сеть |
| `notifications` | `app.notifications` | системные уведомления |
| `device` | `app.device` | инфо, вибрация, буфер, шаринг |
| `permissions` | `app.permissions` / `enpaf.permissions` | проверка/запрос разрешений |

> В браузере (`paf run`) модули возвращают `dev`‑заглушки и симулируют события,
> поэтому всё кликается и тестируется без телефона.

### Управление модулями из Python

Все модули — обычные объекты на `app`, поэтому Bluetooth/Wi-Fi/датчики можно
запускать **прямо из Python** (в `main.py`), а не только из JS:

```python
# файл: main.py
@app.bridge_handler("scan_now")
def scan_now(params):
    wifi = app.wifi.scan_sync()["networks"]        # скан и сразу результат
    bt   = app.bluetooth.discover_sync()["devices"]
    return {"wifi": wifi, "bluetooth": bt}

# одиночные действия
app.wifi.connect(ssid="МояСеть", password="пароль")
app.bluetooth.send(text="привет")
loc = app.location.get()
gyro = app.sensors.gyroscope()

# Python тоже получает события модулей
@app.on("bluetooth_device_found")
def found(dev):
    print("найдено:", dev["name"], dev["address"])
```

Асинхронные операции (`scan`, `discover`) шлют события; для Python есть «синхронные»
обёртки `app.wifi.scan_sync()` и `app.bluetooth.discover_sync()`, которые ждут и
**возвращают список** (с таймаутом).

### Wi-Fi — `enpaf.wifi`

```javascript
// файл: app/js/app.js
const info = await enpaf.wifi.status();       // {enabled, ssid, rssi, ip, ...}
enpaf.wifi.onResult(n => console.log(n.ssid, n.rssi, n.secure));
enpaf.wifi.onFinished(() => console.log('скан завершён'));
await enpaf.wifi.scan();                       // события wifi_scan_result
await enpaf.wifi.connect('МояСеть', 'пароль'); // Android 10+ — через предложение сети
enpaf.wifi.enable();                           // откроет системную панель Wi-Fi
```

### Bluetooth — `enpaf.bluetooth` (поиск, подключение, чат)

Классический Bluetooth (SPP): найти устройство, подключиться и обмениваться
текстовыми сообщениями между двумя телефонами.

```javascript
// файл: app/js/app.js
// 1) запросить разрешения и искать
await enpaf.permissions.request(['BLUETOOTH_SCAN', 'BLUETOOTH_CONNECT', 'FINE_LOCATION']);
enpaf.bluetooth.onFound(d => console.log(d.name, d.address, d.rssi));
await enpaf.bluetooth.discover();

// 2) одно устройство ждёт, второе подключается
await enpaf.bluetooth.listen('ENPAF');         // сервер
await enpaf.bluetooth.connect('AA:BB:CC:DD:EE:01');  // клиент

// 3) общаться
enpaf.bluetooth.onConnected(d => console.log('связь с', d.name, d.role));
enpaf.bluetooth.onData(d => console.log('получено:', d.text));
enpaf.bluetooth.send('Привет!');
enpaf.bluetooth.disconnect();
```

То же из Python: `app.bluetooth.discover()`, `app.bluetooth.connect(address=...)`,
`app.bluetooth.send(text=...)`. Нужны разрешения `BLUETOOTH_SCAN`,
`BLUETOOTH_CONNECT` (Android 12+), `FINE_LOCATION` (для поиска).

### Камера — `getUserMedia` в WebView

Камера работает прямо в вебвью (живое превью + снимок), как в браузере. Нужно
разрешение `CAMERA` (объявить в `enpaf.json` и запросить в рантайме). ENPAF сам
выдаёт WebView доступ к камере. **В `paf run` работает с веб‑камерой ноутбука.**

```javascript
// файл: app/js/app.js
async function startCamera() {
    if (enpaf.isAndroid) await enpaf.permissions.request(['CAMERA']);
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    document.getElementById('cam').srcObject = stream;   // <video id="cam" autoplay playsinline>
}
// снимок: нарисовать кадр на <canvas> и взять canvas.toDataURL('image/png')
```

---

## 🏷 NFC: чтение и запись меток

ENPAF включает **foreground dispatch**: пока приложение открыто, поднесённая
метка автоматически попадает в него (событие `nfc_tag`), а дальше её можно
**прочитать, перезаписать или заблокировать** из Python или JS. Добавьте
разрешение `NFC` в `enpaf.json`.

### Чтение

```javascript
// файл: app/js/app.js
enpaf.nfc.onTag(async (tag) => {                 // метку поднесли к телефону
    const data = await enpaf.nfc.read();
    // data.records: [{type:"text", text:"…"}] | [{type:"uri", uri:"…"}] | [{type:"raw", …}]
    console.log("ID:", data.id, "записи:", data.records);
});
```

### Запись — все типы меток

> ⚠️ **Важно:** дескриптор метки «умирает», как только метку убрали от телефона.
> Поэтому надёжный способ — **`arm*`-методы**: они откладывают запись и выполняют
> её в момент следующего касания. Сначала нажмите запись → потом поднесите метку.
> `Promise` завершится результатом записи.

```javascript
// файл: app/js/app.js  — РЕКОМЕНДУЕТСЯ (arm → поднести метку)
const r = await enpaf.nfc.armUri("https://example.com");  // ждёт касания метки
// r = {written: true, bytes: N} либо {written:false, note:"…"}
await enpaf.nfc.armText("Привет, NFC");
await enpaf.nfc.armWifi("МояСеть", "пароль123");
await enpaf.nfc.armApp("com.example.myapp");
await enpaf.nfc.armContact({ name: "Alex", phone: "+7999" });
await enpaf.nfc.armLock();                               // заблокировать след. метку
```

Прямые `write*`-методы (ниже) пишут в **уже поднесённую** метку — годятся внутри
обработчика `enpaf.nfc.onTag(...)`, когда метка точно в поле:

```javascript
// файл: app/js/app.js
await enpaf.nfc.writeText("Привет, NFC");           // текст
await enpaf.nfc.writeUri("https://example.com");      // ссылка (URL)
await enpaf.nfc.writeUri("tel:+79991234567");       // телефон
await enpaf.nfc.writeUri("mailto:hi@example.com");  // email
await enpaf.nfc.writeUri("geo:55.75,37.61");        // координаты
await enpaf.nfc.writeApp("com.android.chrome");     // запуск приложения (AAR)
await enpaf.nfc.writeWifi("МояСеть", "пароль123");  // Wi-Fi (tap-to-connect)
await enpaf.nfc.writeContact({ name: "Alex", phone: "+7999", email: "a@b.c" }); // контакт (vCard)
await enpaf.nfc.writeMime("application/json", '{"id":42}');                      // MIME
// Несколько записей в одном сообщении:
await enpaf.nfc.writeRecords([
    { kind: "uri", uri: "https://example.com" },
    { kind: "app", package: "com.example.myapp" },
]);
```

То же из Python:

```python
# файл: main.py
@app.bridge_handler("write_card")
def write_card(params):
    app.api.nfc_write_text("Привет")
    app.api.nfc_write_uri("https://example.com")
    app.api.nfc_write_app("com.example.myapp")
    app.api.nfc_write_wifi("МояСеть", "пароль123")
    return {"ok": True}
```

| Метод (`enpaf.nfc.*` / `app.api.*`) | Тип NDEF-записи |
|-------------------------------------|-----------------|
| `writeText(text)` / `nfc_write_text` | Текст (RTD_TEXT) |
| `writeUri(uri)` / `nfc_write_uri` | URL / `tel:` / `mailto:` / `geo:` / `sms:` |
| `writeApp(pkg)` / `nfc_write_app` | Запуск/установка приложения (AAR) |
| `writeMime(mime,data)` / `nfc_write_mime` | MIME (json, vcard, …) |
| `writeWifi(ssid,pass)` / `nfc_write_wifi` | Wi-Fi (vnd.wfa.wsc) |
| `writeContact({…})` / `nfc_write_contact` | Контакт (vCard) |
| `writeRecords([…])` / `nfc_write_records` | Любой набор записей |
| `read()` / `nfc_read` | Прочитать содержимое метки |
| `lock()` / `nfc_make_readonly` | **Заблокировать метку навсегда** (только чтение) |

> Пустые/неформатированные метки форматируются автоматически. `lock()`
> необратим — метку больше нельзя будет перезаписать.

### Открытие URL‑метки при касании (вне приложения)

Когда приложение **закрыто**, поднесённую метку обрабатывает **сама ОС**, а не код
ENPAF. Обычная URL‑метка (`writeUri`) корректна и открывается на большинстве
устройств и на iPhone. Но **поведение зависит от телефона**:

- На некоторых Android (например, **Xiaomi / HyperOS**) метка только считывается
  (вибрация), а браузер не открывается автоматически. Это настройка прошивки, а не
  содержимое метки. Проверьте: NFC включён, экран разблокирован, задан браузер по
  умолчанию, «безопасный элемент» NFC не перехватывается кошельком.
- Чтобы открытие ссылки работало **гарантированно на любом устройстве**, запишите
  метку с **записью запуска приложения** — `enpaf.nfc.writeApp(pkg, url)` (или
  `app.api.nfc_write_app`). Тогда касание запускает ваше приложение, а оно само
  открывает URL (см. событие `nfc_tag` с `from_launch`).

---

## 🔓 Запрос разрешений во время работы (runtime)

«Опасные» разрешения (камера, геолокация, микрофон, контакты…) недостаточно
объявить в `enpaf.json` — Android требует **согласия пользователя в рантайме**.
ENPAF **не** показывает эти диалоги при запуске: вы вызываете их **сами, в нужный
момент** — например, когда пользователь впервые жмёт «Записать аудио».

### Из Python (`main.py`)

```python
# файл: main.py

@app.bridge_handler("start_recording")
def start_recording(params):
    # Покажет системный диалог сейчас. Возвращает то, что уже выдано/запрошено.
    res = app.api.request_permissions(["RECORD_AUDIO"])
    return res        # {"requested":[...], "granted":[...], "pending": true|false}


# Итоговый ответ пользователя приходит сюда (и одновременно — в JS-событие):
@app.on("permission_result")
def on_permission_result(data):
    if "android.permission.RECORD_AUDIO" in data["granted"]:
        print("Микрофон разрешён — можно писать звук")
    else:
        print("Отклонено:", data["denied"])
```

| Метод Python | Назначение |
|--------------|------------|
| `app.api.request_permissions([...])` | Показать системный диалог сейчас |
| `app.api.check_permission("CAMERA")` | `{granted: bool}` — выдано ли одно |
| `app.api.check_permissions([...])` | Статус сразу нескольких |

Имена можно писать коротко (`"CAMERA"`, `"FINE_LOCATION"`, `"RECORD_AUDIO"`) или
полностью (`"android.permission.CAMERA"`).

### Из JavaScript (`app/js/app.js`)

`enpaf.permissions.request(...)` возвращает `Promise`, который **ждёт ответа
пользователя** и резолвится итогом — это самый удобный путь из интерфейса:

```javascript
// файл: app/js/app.js
async function recordAudio() {
    const r = await enpaf.permissions.request(["RECORD_AUDIO"]);
    if (r.granted.includes("android.permission.RECORD_AUDIO")) {
        const level = await enpaf.sensors.audioLevel();
        console.log("Громкость:", level.db, "дБ");
    } else {
        enpaf.device.toast("Нужен доступ к микрофону");
    }
}

// Уже выдано?
const cam = await enpaf.permissions.check("CAMERA");      // {granted: bool}
const many = await enpaf.permissions.checkAll(["CAMERA", "RECORD_AUDIO"]);
```

| JS-метод | Назначение |
|----------|------------|
| `enpaf.permissions.request(list)` | Диалог + `Promise` с результатом `{granted, denied, results}` |
| `enpaf.permissions.check(name)` | `{granted: bool}` |
| `enpaf.permissions.checkAll(list)` | `{granted:[...], denied:[...]}` |

> ⚠️ Запрос разрешений работает только в собранном APK. Изменения в `main.py`
> применяются **в новой сборке** (`paf build apk`) — переустановите APK.

---

## ⚙️ Панель настроек ⚙

Запустите `paf run` и откройте **`http://127.0.0.1:8080/enpaf-settings`** (или нажмите
плавающую кнопку **⚙** в правом нижнем углу страницы). Панель позволяет настроить и
сохранить в `enpaf.json` без ручного редактирования:

- **General** — имя приложения, **иконка** (загрузка с превью), ориентация, основной цвет и цвет статус-бара;
- **Permissions** — разрешения (`<uses-permission>`);
- **Hardware features** — фичи устройства (`<uses-feature>`) с флагом «required»;
- **Deep Links** — диплинки и App Links;
- **Manifest preview** — живой предпросмотр того, что попадёт в `AndroidManifest.xml`.

После «Save» изменения применятся при следующей `paf build`.

---

## 🔐 Разрешения и фичи устройства

### Разрешения

Указываются по коротким ключам в `permissions` (это лишь объявление в манифесте).
Доступные ключи:

`INTERNET`, `ACCESS_NETWORK_STATE`, `ACCESS_WIFI_STATE`, `VIBRATE`, `CAMERA`,
`READ_STORAGE`, `WRITE_STORAGE`, `READ_MEDIA_IMAGES`, `READ_MEDIA_VIDEO`,
`READ_MEDIA_AUDIO`, `FINE_LOCATION`, `COARSE_LOCATION`, `BACKGROUND_LOCATION`,
`RECORD_AUDIO`, `BODY_SENSORS`, `ACTIVITY_RECOGNITION`, `READ_CONTACTS`,
`CALL_PHONE`, `READ_PHONE_STATE`, `SEND_SMS`, `RECEIVE_SMS`, `BLUETOOTH`,
`BLUETOOTH_ADMIN`, `BLUETOOTH_SCAN`, `BLUETOOTH_CONNECT`, `NFC`, `WAKE_LOCK`,
`FOREGROUND_SERVICE`, `POST_NOTIFICATIONS`.

Можно указать и полное имя, напр. `android.permission.CAMERA`.

> 🔓 «Опасные» разрешения (камера, геолокация, микрофон, контакты, Bluetooth-скан,
> уведомления…) надо ещё и **запросить в рантайме** — `app.api.request_permissions([...])`
> или `enpaf.permissions.request([...])`. См.
> [Запрос разрешений во время работы](#-запрос-разрешений-во-время-работы-runtime).

### Фичи (`<uses-feature>`)

Формат: `{ "key": "<KEY>", "required": true|false }`. Доступные ключи:

`CAMERA`, `CAMERA_FRONT`, `CAMERA_AUTOFOCUS`, `NFC`, `BLUETOOTH`, `BLUETOOTH_LE`,
`GPS`, `LOCATION`, `MICROPHONE`, `WIFI`, `TELEPHONY`, `TOUCHSCREEN`, `FINGERPRINT`,
`ACCELEROMETER`, `GYROSCOPE`, `COMPASS`, `PROXIMITY`, `LIGHT`, `BAROMETER`,
`STEP_COUNTER`, `HEART_RATE`.

> `required: false` оставляет приложение устанавливаемым на устройствах без
> соответствующего железа.

---

## 🔗 Deep links (диплинки)

Каждый диплинк превращается в `<intent-filter>` на главной активности.

```json
"deeplinks": [
    { "label": "Профиль", "scheme": "myapp", "host": "open",
      "path": "/profile", "pathType": "prefix", "autoVerify": false }
]
```

| Поле | Описание |
|------|----------|
| `scheme` | Обязательно. Напр. `myapp` или `https` |
| `host` | Опционально. Напр. `example.com` |
| `path` | Опционально. Напр. `/profile` |
| `pathType` | `path` (точно) / `prefix` / `pattern` |
| `autoVerify` | `true` для App Links (проверяемые https-ссылки) |
| `label` | Только для UI-панели |

Проверить диплинк на устройстве:

```bash
adb shell am start -a android.intent.action.VIEW -d "myapp://open/profile"
```

---

## 🔔 Уведомления и нативные возможности

### Базовые уведомления (JavaScript)
Из JavaScript:
```javascript
enpaf.device.notify("Заголовок", "Текст уведомления", 1);
```

### Rich-уведомления (Python)
Из Python можно отправлять мощные системные уведомления с картинками и кнопками:

```python
import base64

with open("app/img/logo.png", "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode("utf-8")

app.api.notify(
    title="Новое сообщение",
    text="Привет!",
    notification_id=1,
    image_base64=img_b64,     # Показывает большую картинку
    action="open_chat",       # Передается при клике на уведомление
    payload="user_123",
    buttons=[
        {"text": "Ответить", "action": "reply"},
        {"text": "Закрыть", "action": "close"}
    ]
)
```

Нажатие на само уведомление или любую его кнопку автоматически разбудит/откроет приложение и сгенерирует событие в Python:
```python
@app.on("notification_click")
def on_notif_click(data):
    print(f"Action: {data.get('action')}, Payload: {data.get('payload')}")
```

> **Важно:** На Android 13+ приложение запрашивает разрешение `POST_NOTIFICATIONS` (добавьте его в `permissions` в вашем `enpaf.json`).

Доступные нативные методы моста (вызываются через `enpaf.device.*` в JS или `app.api.*` в Python): `toast`, `vibrate`, `notify`, `share`, `setOrientation`, `clipboard`, `openUrl`.

---

## 📦 Сборка APK

```bash
paf build apk            # debug
paf build apk --release  # release
paf build aab            # release bundle (.aab)
```

Что происходит:

1. Проверяется окружение (Python/JDK/Android SDK).
2. Подбирается совместимая **JDK 17–21** (учитывается `JAVA_HOME`; иначе ищется в стандартных местах, включая JBR из Android Studio).
3. Генерируется Gradle-проект (Chaquopy), скачивается официальный Gradle wrapper.
4. Gradle собирает APK; результат копируется в `dist/<name>-<version>.apk`.

**Первая сборка долгая** — Gradle докачивает Android platform/build-tools и **NDK
(~1 ГБ)** для Chaquopy. Дальнейшие сборки быстрее (всё кэшируется в `~/.gradle` и
Android SDK).

### Подпись release-сборки

Android **не устанавливает неподписанные** release-APK. ENPAF подписывает их
автоматически: при первой `paf build apk --release` создаётся keystore
`~/.enpaf/keystores/<package>.jks` (общий для всех последующих сборок этого
пакета — подпись стабильна, обновления ставятся поверх). Release собирается без
обфускации (`minifyEnabled false`), чтобы R8 не вырезал мост `@JavascriptInterface`
и классы Chaquopy.

Свой keystore (для публикации в Google Play) — через `--keystore` или блок
`signing` в `enpaf.json`:

```json
"signing": {
    "keystore": "release.jks",
    "store_password": "••••••",
    "key_alias": "myapp",
    "key_password": "••••••"
}
```

```bash
paf build apk --release --keystore release.jks
```

### OneDrive / облачные папки

Если проект лежит в OneDrive (или другой синхронизируемой папке), ENPAF
**автоматически** выносит каталог сборки в `%LOCALAPPDATA%\enpaf\builds\…`, потому что
синхронизация ломает удаление файлов Gradle. Путь можно переопределить переменной
окружения `ENPAF_BUILD_DIR`. Итоговый APK всё равно копируется в `dist/`.

---

## 🧪 Тесты и CI

В репозитории есть набор тестов на `pytest` (покрывают dev-режим: хранилище,
события, мост, роутер, DeviceAPI, модули, помощники сборки, CLI):

```bash
pip install -e ".[test]"   # пакет + pytest
pytest                      # запустить все тесты
```

**GitHub Actions** (`.github/workflows/`):

- **CI** (`ci.yml`) — на каждый push в `main` и каждый PR: матрица
  **Python 3.9–3.13 × Ubuntu + Windows**, прогон `pytest`, сборка и проверка
  дистрибутива (`python -m build` + `twine check`).
- **Release** (`release.yml`) — при пуше тега `v*` собирает wheel/sdist и
  прикрепляет их к GitHub Release.

```bash
git tag v1.2.0 && git push origin v1.2.0   # соберёт и опубликует дистрибутив
```

> APK в CI не собираются (нужны Android SDK + Chaquopy) — собирайте их локально
> и прикрепляйте к релизу. Подробнее: [Wiki → Testing & CI](https://github.com/aaalllexxx/enpaf/wiki/Testing-and-CI).

---

## 📥 Что можно импортировать

**Основное (рекомендуется):**

```python
from enpaf import EnpafApp, __version__
```

**Продвинутое** (обычно используется через `app.*`, но доступно напрямую):

```python
from enpaf.core.storage import Storage, Collection
from enpaf.core.events import EventEmitter
from enpaf.core.bridge import Bridge
from enpaf.core.router import Router
from enpaf.core.api import DeviceAPI

# Справочники для манифеста / панели настроек
from enpaf.android.permissions import PERMISSIONS, get_permission_catalog
from enpaf.android.features import FEATURES, get_feature_catalog
from enpaf.android.deeplinks import get_deeplink_xml

# Программная сборка APK
from enpaf.builder.apk_builder import APKBuilder

# Точка входа CLI
from enpaf.cli.main import main
```

Клиентский SDK для подключения вручную (если не используете авто-инъекцию):

```html
<script src="js/enpaf.js"></script>
```

---

## 🩺 Решение проблем

| Симптом | Причина и решение |
|---------|-------------------|
| **Приложение сразу закрывается** | Пересоберите APK — фиксы применяются только в новой сборке. Если повторяется — снимите лог: `adb logcat` (теги `AndroidRuntime`, `python.stderr`, `chaquopy`). |
| **`Bridge call failed` / `Unexpected token '<'` в `paf run`** | Старый билд `enpaf`: HTTP-фолбэк моста и Socket.IO-клиент чинятся в свежей версии. Обновите пакет (`pip install -U enpaf` или `pip install -e .` из исходников) и перезапустите `paf run`. |
| **`enpaf is not defined`** | Мост не подключён. Сборка вставляет `js/enpaf.js` автоматически; убедитесь, что собираете свежую версию. |
| **Датчик/геолокация возвращает `{"dev": true}`** | Это нормально в браузере (`paf run`) — реальные показания доступны только в APK на устройстве. |
| **`request_permissions` ничего не показывает** | Работает только в APK и только для «опасных» разрешений, которые объявлены в `enpaf.json`. Проверьте, что разрешение есть в `permissions`. |
| **Синий/неожиданный цвет статус-бара** | Это `theme.status_bar_color`. Поменяйте его в панели ⚙ → General или в `enpaf.json`. |
| **`Unable to delete directory … python\sources`** | OneDrive блокирует файлы. ENPAF собирает вне OneDrive автоматически; при желании задайте `ENPAF_BUILD_DIR`. |
| **`Incompatible Java version`** | Нужна JDK 17–21. Установите JDK 17 и задайте `JAVA_HOME`, либо дайте ENPAF найти её автоматически. |
| **release-APK не устанавливается** | Неподписанный release Android отклоняет. ENPAF подписывает release автоматически (keystore в `~/.enpaf/keystores/`). Обновите пакет и пересоберите `paf build apk --release`. Если меняли keystore — сначала удалите старую версию приложения (конфликт подписи). |
| **`keytool not found` при release** | keystore создаётся через `keytool` из JDK. Убедитесь, что JDK 17 установлен и найден (`paf doctor`). |
| **URL‑метка не открывается на Xiaomi (только вибрация)** | Содержимое метки корректно (на iPhone открывается) — это поведение HyperOS. Проверьте NFC, разблокировку экрана и браузер по умолчанию, либо записывайте метку через `enpaf.nfc.writeApp(pkg, url)` — тогда касание запустит приложение, и оно откроет ссылку. |
| **NFC‑запись «не доходит» до метки** | Дескриптор метки умирает, когда её убрали от телефона. Используйте `enpaf.nfc.armText/armUri/...` — сначала вызов, потом касание. |
| **`'""' is not recognized` при Gradle** | Старый сломанный wrapper. Удалите каталог сборки и соберите заново (`paf build apk --clean`). |

Полная диагностика окружения: `paf doctor`.

---

## 📚 Документация (Wiki)

Подробная документация ведётся в [GitHub Wiki](https://github.com/aaalllexxx/enpaf/wiki):

- [Home](https://github.com/aaalllexxx/enpaf/wiki) · [Installation](https://github.com/aaalllexxx/enpaf/wiki/Installation) · [Quick Start](https://github.com/aaalllexxx/enpaf/wiki/Quick-Start)
- [CLI Reference](https://github.com/aaalllexxx/enpaf/wiki/CLI-Reference) · [enpaf.json](https://github.com/aaalllexxx/enpaf/wiki/Project-Configuration) · [Project Structure](https://github.com/aaalllexxx/enpaf/wiki/Project-Structure)
- [Python API](https://github.com/aaalllexxx/enpaf/wiki/Python-API) · [JavaScript Bridge](https://github.com/aaalllexxx/enpaf/wiki/JavaScript-Bridge) · [Storage](https://github.com/aaalllexxx/enpaf/wiki/Storage) · [Events](https://github.com/aaalllexxx/enpaf/wiki/Events)
- [Device Capabilities](https://github.com/aaalllexxx/enpaf/wiki/Device-Capabilities) · [Building APKs](https://github.com/aaalllexxx/enpaf/wiki/Building-APKs) · [Release & Signing](https://github.com/aaalllexxx/enpaf/wiki/Release-and-Signing)
- [Companion App](https://github.com/aaalllexxx/enpaf/wiki/Companion-App) · [Architecture](https://github.com/aaalllexxx/enpaf/wiki/Architecture) · [Testing & CI](https://github.com/aaalllexxx/enpaf/wiki/Testing-and-CI) · [Troubleshooting](https://github.com/aaalllexxx/enpaf/wiki/Troubleshooting)

---

## 📄 Лицензия

ENPAF распространяется по лицензии **[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)** — см. [LICENSE](LICENSE).

- ✅ **Бесплатно для некоммерческого использования** — личные проекты,
  исследования, обучение, некоммерческие организации, госучреждения.
- 💼 **Коммерческое использование — платное**: требуется отдельная коммерческая
  лицензия. По вопросам её получения свяжитесь с автором.

Это source-available лицензия, а не OSI open-source. Подробности —
[Wiki → License](https://github.com/aaalllexxx/enpaf/wiki/License).

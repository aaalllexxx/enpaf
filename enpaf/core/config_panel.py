"""
ENPAF Core — Config Panel
Backend for the in-browser settings page (deep links & permissions).

Reads/writes the project's enpaf.json and produces a live preview of the
AndroidManifest fragments that the builder will generate from it.
"""

import json
import os
import re
import stat

from enpaf.android.permissions import get_permission_catalog, get_permission_xml
from enpaf.android.deeplinks import normalize_deeplink, get_deeplink_xml
from enpaf.android.features import get_feature_catalog, get_feature_xml

CONFIG_FILENAME = "enpaf.json"

_PERMISSION_RE = re.compile(r"[A-Za-z0-9_.]+")
_SCHEME_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*")
_PATH_TYPES = {"path", "prefix", "pattern", "pathPrefix", "pathPattern"}
_ORIENTATIONS = {"portrait", "landscape", "auto", "sensor", "unspecified"}
_ICON_EXT = {".png", ".jpg", ".jpeg", ".webp"}
_COLOR_RE = re.compile(r"#[0-9A-Fa-f]{3,8}")


# ─── enpaf.json I/O ───────────────────────────────────────────

def _config_path(project_dir: str) -> str:
    return os.path.join(project_dir, CONFIG_FILENAME)


def load_config(project_dir: str) -> dict:
    """Load enpaf.json (returns {} if missing)."""
    path = _config_path(project_dir)
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _safe_write_json(path: str, data: dict):
    """Write JSON, clearing a read-only/OneDrive-placeholder target first."""
    if os.path.exists(path):
        try:
            os.chmod(path, stat.S_IWRITE)
        except OSError:
            pass
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")


# ─── Validation ───────────────────────────────────────────────

def _clean_permissions(perms) -> list:
    if not isinstance(perms, list):
        raise ValueError("permissions must be a list")
    out, seen = [], set()
    for p in perms:
        if not isinstance(p, str):
            continue
        token = p.strip()
        if not token:
            continue
        if not _PERMISSION_RE.fullmatch(token):
            raise ValueError(f"invalid permission name: {p!r}")
        if token not in seen:
            seen.add(token)
            out.append(token)
    return out


def _clean_deeplinks(deeplinks) -> list:
    if not isinstance(deeplinks, list):
        raise ValueError("deeplinks must be a list")
    out = []
    for raw in deeplinks:
        if not isinstance(raw, dict):
            continue
        dl = normalize_deeplink(raw)
        if not dl["scheme"]:
            continue  # skip blank rows
        if not _SCHEME_RE.fullmatch(dl["scheme"]):
            raise ValueError(f"invalid URL scheme: {dl['scheme']!r}")
        if dl["pathType"] not in _PATH_TYPES:
            dl["pathType"] = "path"
        out.append(dl)
    return out


def _clean_features(features) -> list:
    if not isinstance(features, list):
        raise ValueError("features must be a list")
    out, seen = [], set()
    for f in features:
        if isinstance(f, str):
            key, required = f.strip(), False
        elif isinstance(f, dict):
            key = str(f.get("key", "")).strip()
            required = bool(f.get("required", False))
        else:
            continue
        if not key or key in seen:
            continue
        seen.add(key)
        out.append({"key": key, "required": required})
    return out


def _clean_general(general, config) -> None:
    """Merge general settings (name, orientation, colors, icon) into config."""
    if not isinstance(general, dict):
        return
    if "name" in general and str(general["name"]).strip():
        config["name"] = str(general["name"]).strip()
    if "orientation" in general:
        o = str(general["orientation"]).strip().lower()
        if o in _ORIENTATIONS:
            config["orientation"] = o
    if "icon" in general:
        config["icon"] = str(general["icon"]).strip()
    theme = config.get("theme") or {}
    for key in ("primary_color", "status_bar_color"):
        val = str(general.get(key, "")).strip()
        if val:
            if not _COLOR_RE.fullmatch(val):
                raise ValueError(f"invalid color: {val!r}")
            theme[key] = val
    if theme:
        config["theme"] = theme


def save_icon(project_dir: str, filename: str, content: bytes) -> str:
    """Save an uploaded icon into the project; return its relative path."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in _ICON_EXT:
        raise ValueError("icon must be a .png, .jpg or .webp file")
    if not content:
        raise ValueError("empty file")
    rel = "icon" + (".jpg" if ext == ".jpeg" else ext)
    dst = os.path.join(project_dir, rel)
    if os.path.exists(dst):
        try:
            os.chmod(dst, stat.S_IWRITE)
        except OSError:
            pass
    with open(dst, "wb") as f:
        f.write(content)
    return rel


# ─── State / preview / save ───────────────────────────────────

def build_preview(permissions, deeplinks, features=None) -> dict:
    """Render the manifest fragments (lenient — used while editing)."""
    perms = [p for p in (permissions or []) if isinstance(p, str) and p.strip()]
    dls = [d for d in (deeplinks or []) if isinstance(d, dict)]
    feats = [f for f in (features or []) if isinstance(f, (str, dict))]
    return {
        "permissions_xml": get_permission_xml(perms),
        "features_xml": get_feature_xml(feats),
        "deeplinks_xml": get_deeplink_xml(dls).lstrip("\n"),
    }


def build_state(project_dir: str) -> dict:
    """Full payload for the settings page on load."""
    config = load_config(project_dir)
    permissions = config.get("permissions", []) or []
    features = _clean_features(config.get("features", []) or [])
    deeplinks = [normalize_deeplink(d) for d in (config.get("deeplinks", []) or [])
                 if isinstance(d, dict)]
    theme = config.get("theme") or {}
    return {
        "project": config.get("name", ""),
        "package": config.get("package", ""),
        "general": {
            "name": config.get("name", ""),
            "orientation": config.get("orientation", "portrait"),
            "icon": config.get("icon", ""),
            "primary_color": theme.get("primary_color", "#6C5CE7"),
            "status_bar_color": theme.get("status_bar_color", "#5A4BD1"),
        },
        "permissions": permissions,
        "features": features,
        "deeplinks": deeplinks,
        "catalog": get_permission_catalog(),
        "feature_catalog": get_feature_catalog(),
        "preview": build_preview(permissions, deeplinks, features),
    }


def save_config(project_dir: str, data: dict) -> dict:
    """Validate and persist the settings payload into enpaf.json.

    Expected keys (all optional): general, permissions, features, deeplinks.
    """
    if not isinstance(data, dict):
        raise ValueError("invalid payload")
    path = _config_path(project_dir)
    if not os.path.isfile(path):
        raise FileNotFoundError("enpaf.json not found in project directory")

    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)

    if "general" in data:
        _clean_general(data.get("general"), config)
    if "permissions" in data:
        config["permissions"] = _clean_permissions(data.get("permissions"))
    if "features" in data:
        config["features"] = _clean_features(data.get("features"))
    if "deeplinks" in data:
        config["deeplinks"] = _clean_deeplinks(data.get("deeplinks"))

    _safe_write_json(path, config)
    return config


# ─── Settings page (self-contained HTML) ──────────────────────

def render_page() -> str:
    return _PAGE


_PAGE = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ENPAF · Настройки приложения</title>
<style>
  :root{
    --accent:#7C6CF0; --accent2:#9D8DF5; --accent-ink:#fff;
    --bg:#0a0c16; --bg2:#0e1120; --surface:#141830; --surface2:#1b2040;
    --line:rgba(255,255,255,.08); --line2:rgba(255,255,255,.14);
    --txt:#eceefb; --mut:#9298c0; --dim:#6a6f97;
    --ok:#33d49b; --warn:#ffb454; --err:#ff6b81;
    --r:14px; --r-sm:10px;
    --shadow:0 10px 40px rgba(0,0,0,.45);
    --font:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
    --mono:ui-monospace,'SF Mono',Consolas,monospace;
  }
  *{box-sizing:border-box}
  html,body{margin:0}
  body{font:14px/1.55 var(--font);color:var(--txt);
    background:radial-gradient(1200px 600px at 80% -10%,rgba(124,108,240,.18),transparent 60%),
               radial-gradient(900px 500px at -10% 110%,rgba(51,212,155,.10),transparent 55%),var(--bg);}
  a{color:inherit}
  code{font-family:var(--mono);font-size:.85em;color:var(--accent2);
    background:rgba(124,108,240,.12);padding:1px 6px;border-radius:6px}

  /* Topbar */
  .topbar{position:sticky;top:0;z-index:30;display:flex;align-items:center;gap:14px;
    padding:12px 22px;background:rgba(10,12,22,.72);backdrop-filter:blur(14px);
    border-bottom:1px solid var(--line)}
  .brand{display:flex;align-items:center;gap:12px;min-width:0}
  .logo{width:38px;height:38px;border-radius:11px;display:grid;place-items:center;font-size:19px;
    background:linear-gradient(135deg,var(--accent),var(--accent2));box-shadow:0 6px 18px rgba(124,108,240,.45)}
  .brand .t{font-weight:700;font-size:15px;line-height:1.1}
  .brand .p{font-size:12px;color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:42vw}
  .grow{flex:1}
  .dirty{display:none;align-items:center;gap:7px;color:var(--warn);font-size:12.5px;font-weight:600}
  .dirty.on{display:inline-flex}
  .dirty .d{width:8px;height:8px;border-radius:50%;background:var(--warn);box-shadow:0 0 0 4px rgba(255,180,84,.18)}
  .btn{font:inherit;font-weight:600;cursor:pointer;border:1px solid transparent;border-radius:10px;
    padding:9px 15px;transition:.15s;white-space:nowrap;text-decoration:none;display:inline-flex;align-items:center;gap:7px}
  .btn:active{transform:translateY(1px)}
  .btn.primary{background:linear-gradient(135deg,var(--accent),var(--accent2));color:var(--accent-ink);
    box-shadow:0 8px 22px rgba(124,108,240,.35)}
  .btn.primary:hover{filter:brightness(1.07)}
  .btn.ghost{background:transparent;color:var(--txt);border-color:var(--line2)}
  .btn.ghost:hover{background:var(--surface)}
  .btn.sm{padding:6px 11px;font-size:12.5px;border-radius:8px}
  .btn.danger{background:transparent;color:var(--err);border-color:rgba(255,107,129,.4)}
  .btn.danger:hover{background:rgba(255,107,129,.12)}

  /* Layout */
  .shell{display:grid;grid-template-columns:212px 1fr;gap:26px;max-width:1180px;margin:0 auto;padding:26px 22px 80px}
  .side{position:sticky;top:78px;align-self:start;display:flex;flex-direction:column;gap:3px}
  .side a{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:10px;color:var(--mut);
    font-weight:600;font-size:13.5px;transition:.15s}
  .side a .i{width:18px;text-align:center}
  .side a:hover{background:var(--surface);color:var(--txt)}
  .side a.active{background:linear-gradient(135deg,rgba(124,108,240,.22),rgba(124,108,240,.08));
    color:var(--txt);box-shadow:inset 0 0 0 1px var(--line)}
  .content{min-width:0;display:flex;flex-direction:column;gap:22px}
  @media(max-width:840px){ .shell{grid-template-columns:1fr} .side{position:static;flex-direction:row;flex-wrap:wrap;top:0}
    .brand .p{max-width:30vw} }

  /* Cards */
  .card{background:linear-gradient(180deg,var(--surface),var(--bg2));border:1px solid var(--line);
    border-radius:18px;padding:20px 20px 22px;box-shadow:var(--shadow);scroll-margin-top:80px}
  .card>h2{margin:0;font-size:16px;display:flex;align-items:center;gap:10px}
  .card>h2 .badge{margin-left:auto;font-size:11.5px;font-weight:700;color:var(--mut);
    background:var(--surface2);border:1px solid var(--line);padding:3px 9px;border-radius:999px}
  .card>.hint{margin:6px 0 18px;color:var(--mut);font-size:12.5px}

  .grid2{display:grid;gap:14px;grid-template-columns:1fr 1fr}
  @media(max-width:560px){ .grid2{grid-template-columns:1fr} }
  label.f{display:flex;flex-direction:column;gap:6px;font-size:12px;color:var(--mut);font-weight:600}
  input[type=text],select{font:inherit;color:var(--txt);background:var(--bg2);border:1px solid var(--line2);
    border-radius:10px;padding:10px 12px;transition:.15s;width:100%}
  input[type=text]:focus,select:focus{outline:none;border-color:var(--accent);
    box-shadow:0 0 0 3px rgba(124,108,240,.22)}
  input::placeholder{color:var(--dim)}

  /* Color picker row */
  .color{display:flex;align-items:center;gap:10px;background:var(--bg2);border:1px solid var(--line2);
    border-radius:10px;padding:6px 10px}
  .color input[type=color]{appearance:none;-webkit-appearance:none;width:34px;height:34px;border:none;
    background:none;cursor:pointer;padding:0}
  .color input[type=color]::-webkit-color-swatch-wrapper{padding:0}
  .color input[type=color]::-webkit-color-swatch{border:1px solid var(--line2);border-radius:8px}
  .color .hex{font-family:var(--mono);font-size:13px;color:var(--txt);text-transform:uppercase}

  /* Icon */
  .iconrow{display:flex;align-items:center;gap:16px;margin-top:16px}
  .iconprev{width:72px;height:72px;border-radius:18px;object-fit:cover;background:var(--bg2);
    border:1px solid var(--line2);display:grid;place-items:center;color:var(--dim);font-size:24px}
  .iconmeta .d{color:var(--mut);font-size:12px;margin-top:7px}

  /* Toggle rows (perms / features) */
  .toolbar{display:flex;align-items:center;gap:10px;margin-bottom:12px}
  .search{flex:1;position:relative}
  .search input{padding-left:34px}
  .search::before{content:"🔍";position:absolute;left:11px;top:50%;transform:translateY(-50%);font-size:13px;opacity:.6}
  .rows{display:flex;flex-direction:column}
  .row{display:flex;align-items:center;gap:14px;padding:11px 12px;border-radius:11px;cursor:pointer;transition:.12s}
  .row:hover{background:var(--surface2)}
  .row.on{background:rgba(124,108,240,.08)}
  .row .rm{min-width:0;flex:1}
  .row .rt{font-weight:600;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
  .row .rs{color:var(--mut);font-size:12px;margin-top:3px;word-break:break-word}
  .chip{font-size:10.5px;font-weight:700;letter-spacing:.02em;text-transform:uppercase;
    padding:2px 7px;border-radius:999px;background:rgba(124,108,240,.18);color:var(--accent2)}
  .chip.req{background:rgba(51,212,155,.16);color:var(--ok)}
  .chip.run{background:rgba(255,180,84,.16);color:var(--warn)}
  .empty{color:var(--dim);font-size:13px;padding:14px 4px;text-align:center}

  /* Switch */
  .switch{position:relative;flex:0 0 auto;width:42px;height:24px}
  .switch input{opacity:0;width:0;height:0;position:absolute}
  .slider{position:absolute;inset:0;border-radius:999px;background:var(--surface2);
    border:1px solid var(--line2);transition:.18s;cursor:pointer}
  .slider::before{content:"";position:absolute;width:18px;height:18px;left:2px;top:2px;border-radius:50%;
    background:#cfd2ef;transition:.18s}
  .switch input:checked+.slider{background:linear-gradient(135deg,var(--accent),var(--accent2));border-color:transparent}
  .switch input:checked+.slider::before{transform:translateX(18px);background:#fff}
  .switch input:disabled+.slider{opacity:.55;cursor:not-allowed}
  .sub-req{display:flex;align-items:center;gap:7px;color:var(--mut);font-size:12px;margin-right:4px}

  /* Deep links */
  .dl{border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:12px;background:var(--bg2)}
  .dl .row3{display:grid;gap:10px;grid-template-columns:repeat(2,1fr)}
  @media(max-width:560px){ .dl .row3{grid-template-columns:1fr} }
  .dl .full{grid-column:1/-1}
  .dl .opts{display:flex;align-items:center;justify-content:space-between;margin-top:12px;gap:10px;flex-wrap:wrap}
  .chk{display:flex;align-items:center;gap:9px;font-size:12.5px;color:var(--txt);cursor:pointer}
  .uri{font-family:var(--mono);font-size:12px;color:var(--accent2);background:var(--bg);
    padding:4px 9px;border-radius:7px;display:inline-block;margin-top:10px;word-break:break-all;border:1px solid var(--line)}
  .add{width:100%;justify-content:center;background:transparent;color:var(--txt);
    border:1px dashed var(--line2);padding:11px}
  .add:hover{background:var(--surface);border-color:var(--accent)}

  /* Preview */
  .pvhead{display:flex;align-items:center;gap:10px;margin-bottom:10px}
  pre{background:#070912;border:1px solid var(--line);border-radius:12px;padding:16px;margin:0;
    overflow:auto;font-family:var(--mono);font-size:12px;color:#cdd6ff;line-height:1.55}

  /* Toast */
  .toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%) translateY(24px);
    background:var(--ok);color:#04130c;padding:12px 20px;border-radius:12px;font-weight:700;
    opacity:0;pointer-events:none;transition:.28s;z-index:60;box-shadow:var(--shadow)}
  .toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
  .toast.err{background:var(--err);color:#1b0207}
</style>
</head>
<body>

<header class="topbar">
  <div class="brand">
    <div class="logo">⚙</div>
    <div style="min-width:0">
      <div class="t">Настройки приложения</div>
      <div class="p" id="proj">…</div>
    </div>
  </div>
  <div class="grow"></div>
  <span class="dirty" id="dirty"><span class="d"></span> Есть несохранённые изменения</span>
  <a class="btn ghost" href="/">← В приложение</a>
  <button class="btn primary" id="save" onclick="save()">Сохранить</button>
</header>

<div class="shell">
  <nav class="side" id="side">
    <a href="#sec-general" class="active"><span class="i">🎨</span> Основное</a>
    <a href="#sec-perms"><span class="i">🔐</span> Разрешения</a>
    <a href="#sec-feats"><span class="i">🧩</span> Оборудование</a>
    <a href="#sec-links"><span class="i">🔗</span> Deep Links</a>
    <a href="#sec-preview"><span class="i">📄</span> Манифест</a>
  </nav>

  <div class="content">
    <!-- General -->
    <section class="card" id="sec-general">
      <h2>🎨 Основное</h2>
      <p class="hint">Имя, иконка, ориентация и цвета приложения. Пишется в enpaf.json и манифест.</p>
      <div class="grid2">
        <label class="f">Название приложения
          <input type="text" id="g_name" placeholder="My App" oninput="GEN.name=this.value;markDirty()"></label>
        <label class="f">Ориентация
          <select id="g_or" onchange="GEN.orientation=this.value;markDirty()">
            <option value="portrait">Портрет</option>
            <option value="landscape">Ландшафт</option>
            <option value="auto">Автоповорот</option>
            <option value="unspecified">Как в системе</option>
          </select></label>
        <label class="f">Основной цвет
          <span class="color"><input type="color" id="g_pc"
            oninput="GEN.primary_color=this.value;$('#g_pc_h').textContent=this.value;markDirty()">
            <span class="hex" id="g_pc_h">#6C5CE7</span></span></label>
        <label class="f">Цвет статус-бара
          <span class="color"><input type="color" id="g_sb"
            oninput="GEN.status_bar_color=this.value;$('#g_sb_h').textContent=this.value;markDirty()">
            <span class="hex" id="g_sb_h">#5A4BD1</span></span></label>
      </div>
      <div class="iconrow">
        <img id="iconimg" class="iconprev" alt="" style="display:none">
        <div id="iconph" class="iconprev">🖼️</div>
        <div class="iconmeta">
          <input type="file" id="iconfile" accept="image/png,image/jpeg,image/webp" style="display:none" onchange="uploadIcon(this)">
          <button class="btn ghost sm" onclick="document.getElementById('iconfile').click()">Выбрать иконку…</button>
          <div class="d" id="iconname">Иконка не задана — будет стандартная Android</div>
        </div>
      </div>
    </section>

    <!-- Permissions -->
    <section class="card" id="sec-perms">
      <h2>🔐 Разрешения <span class="badge" id="permCount">0 выбрано</span></h2>
      <p class="hint">Пишутся как <code>&lt;uses-permission&gt;</code>. «Опасные» (метка <span class="chip run">runtime</span>)
        нужно ещё и запрашивать во время работы: <code>enpaf.permissions.request([...])</code>.</p>
      <div class="toolbar">
        <div class="search"><input type="text" id="permSearch" placeholder="Поиск разрешения…" oninput="renderPerms()"></div>
      </div>
      <div class="rows" id="perms"></div>
    </section>

    <!-- Features -->
    <section class="card" id="sec-feats">
      <h2>🧩 Оборудование</h2>
      <p class="hint">Объявляется как <code>&lt;uses-feature&gt;</code> (камера, NFC, датчики…). Оставьте «required» выключенным,
        чтобы приложение ставилось и без этого железа.</p>
      <div class="rows" id="feats"></div>
    </section>

    <!-- Deep links -->
    <section class="card" id="sec-links">
      <h2>🔗 Deep Links</h2>
      <p class="hint">Каждая ссылка — отдельный <code>&lt;intent-filter&gt;</code>. Для проверяемых доменных ссылок —
        <b>https</b> + <b>App Links</b>.</p>
      <div id="dls"></div>
      <button class="btn add" onclick="addDeeplink()">+ Добавить deep link</button>
    </section>

    <!-- Preview -->
    <section class="card" id="sec-preview">
      <div class="pvhead">
        <h2 style="margin:0">📄 Превью манифеста</h2>
        <div class="grow"></div>
        <button class="btn ghost sm" onclick="copyPreview()">Скопировать</button>
      </div>
      <p class="hint">Живой предпросмотр того, что билдер вставит в AndroidManifest.xml (только чтение).</p>
      <pre id="preview">…</pre>
    </section>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let GEN={}, CAT=[], FEATCAT=[], PERMS=new Set(), FEATS={}, DLS=[], DIRTY=false;
const $ = s => document.querySelector(s);

function markDirty(){ DIRTY=true; $('#dirty').classList.add('on'); }
function clearDirty(){ DIRTY=false; $('#dirty').classList.remove('on'); }

async function load(){
  const r = await fetch('/enpaf-api/config');
  const s = await r.json();
  GEN = s.general || {};
  CAT = s.catalog || [];
  FEATCAT = s.feature_catalog || [];
  PERMS = new Set(s.permissions || []);
  FEATS = {}; (s.features || []).forEach(f => FEATS[f.key] = !!f.required);
  DLS = (s.deeplinks || []).map(d => ({...d}));
  $('#proj').textContent = (s.project || 'Без имени') + (s.package ? '  ·  ' + s.package : '');
  renderGeneral(); renderPerms(); renderFeatures(); renderDeeplinks(); refreshPreview();
  clearDirty();
}

function renderGeneral(){
  $('#g_name').value = GEN.name || '';
  $('#g_or').value = GEN.orientation || 'portrait';
  const pc = GEN.primary_color || '#6C5CE7', sb = GEN.status_bar_color || '#5A4BD1';
  $('#g_pc').value = pc; $('#g_pc_h').textContent = pc.toUpperCase();
  $('#g_sb').value = sb; $('#g_sb_h').textContent = sb.toUpperCase();
  if (GEN.icon){
    const img=$('#iconimg'); img.src='/enpaf-api/icon?t='+Date.now();
    img.style.display='block'; $('#iconph').style.display='none'; $('#iconname').textContent=GEN.icon;
  }
}

async function uploadIcon(input){
  const file=input.files[0]; if(!file) return;
  const fd=new FormData(); fd.append('icon', file);
  const res=await (await fetch('/enpaf-api/icon',{method:'POST',body:fd})).json();
  if(res.success){
    GEN.icon=res.icon;
    const img=$('#iconimg'); img.src=URL.createObjectURL(file); img.style.display='block';
    $('#iconph').style.display='none';
    $('#iconname').textContent=res.icon+'  (применится при сохранении)';
    markDirty(); toast('Иконка загружена ✓');
  } else toast(res.error||'Ошибка загрузки', true);
}

function renderPerms(){
  const q=($('#permSearch')?.value||'').toLowerCase();
  $('#perms').innerHTML = CAT.filter(c=>{
    const hay=(c.key+' '+(c.description||'')+' '+c.android).toLowerCase();
    return !q || hay.includes(q);
  }).map(c=>{
    const req = c.key==='INTERNET';
    const on = PERMS.has(c.key) || req;
    return `<label class="row ${on?'on':''}">
      <div class="rm">
        <div class="rt">${c.key}
          ${req?'<span class="chip req">required</span>':''}
          ${c.runtime?'<span class="chip run">runtime</span>':''}</div>
        <div class="rs">${c.description||''} · <code>${c.android}</code></div>
      </div>
      <span class="switch"><input type="checkbox" data-k="${c.key}" ${on?'checked':''} ${req?'disabled':''}
        onchange="togglePerm(this)"><span class="slider"></span></span>
    </label>`;
  }).join('') || '<div class="empty">Ничего не найдено</div>';
  PERMS.add('INTERNET');
  updatePermCount();
}
function togglePerm(el){
  if(el.checked)PERMS.add(el.dataset.k); else PERMS.delete(el.dataset.k);
  el.closest('.row').classList.toggle('on', el.checked);
  updatePermCount(); markDirty(); refreshPreview();
}
function updatePermCount(){ $('#permCount').textContent = PERMS.size + ' выбрано'; }

function renderFeatures(){
  $('#feats').innerHTML = FEATCAT.map(c=>{
    const on = c.key in FEATS;
    return `<div class="row ${on?'on':''}">
      <div class="rm">
        <div class="rt">${c.description}</div>
        <div class="rs"><code>${c.android}</code></div>
      </div>
      ${on?`<span class="sub-req">
        <label class="switch"><input type="checkbox" data-r="${c.key}" ${FEATS[c.key]?'checked':''} onchange="reqFeat(this)"><span class="slider"></span></label>
        required</span>`:''}
      <label class="switch"><input type="checkbox" data-k="${c.key}" ${on?'checked':''}
        onchange="toggleFeat(this)"><span class="slider"></span></label>
    </div>`;
  }).join('');
}
function toggleFeat(el){ if(el.checked)FEATS[el.dataset.k]=false; else delete FEATS[el.dataset.k];
  renderFeatures(); markDirty(); refreshPreview(); }
function reqFeat(el){ if(el.dataset.r in FEATS)FEATS[el.dataset.r]=el.checked; markDirty(); refreshPreview(); }

function uriFor(d){
  let u=(d.scheme||'scheme')+'://'+(d.host||'');
  if(d.path) u+=(d.path.startsWith('/')?'':'/')+d.path;
  return u;
}
function renderDeeplinks(){
  const host=$('#dls');
  if(!DLS.length){ host.innerHTML='<div class="empty">Пока нет deep links — добавьте ниже.</div>'; return; }
  host.innerHTML = DLS.map((d,i)=>`
    <div class="dl">
      <div class="row3">
        <label class="f">Метка (необязательно)
          <input type="text" value="${esc(d.label)}" oninput="upd(${i},'label',this.value)" placeholder="Открыть профиль"></label>
        <label class="f">Схема *
          <input type="text" value="${esc(d.scheme)}" oninput="upd(${i},'scheme',this.value)" placeholder="myapp или https"></label>
        <label class="f">Хост (необязательно)
          <input type="text" value="${esc(d.host)}" oninput="upd(${i},'host',this.value)" placeholder="example.com"></label>
        <label class="f">Тип пути
          <select onchange="upd(${i},'pathType',this.value)">
            <option value="path" ${d.pathType==='path'?'selected':''}>Точный путь</option>
            <option value="prefix" ${(d.pathType==='prefix'||d.pathType==='pathPrefix')?'selected':''}>Префикс</option>
            <option value="pattern" ${(d.pathType==='pattern'||d.pathType==='pathPattern')?'selected':''}>Шаблон</option>
          </select></label>
        <label class="f full">Путь (необязательно)
          <input type="text" value="${esc(d.path)}" oninput="upd(${i},'path',this.value)" placeholder="/profile"></label>
      </div>
      <div class="opts">
        <label class="chk"><span class="switch"><input type="checkbox" ${d.autoVerify?'checked':''}
          onchange="upd(${i},'autoVerify',this.checked)"><span class="slider"></span></span>
          Verify (App Links, autoVerify)</label>
        <button class="btn danger sm" onclick="removeDeeplink(${i})">Удалить</button>
      </div>
      <span class="uri">${esc(uriFor(d))}</span>
    </div>`).join('');
}
function upd(i,k,v){ DLS[i][k]=v; if(k==='scheme'||k==='host'||k==='path') renderUri(i); markDirty(); refreshPreview(); }
function renderUri(i){ const el=document.querySelectorAll('.dl')[i]?.querySelector('.uri'); if(el) el.textContent=uriFor(DLS[i]); }
function addDeeplink(){ DLS.push({label:'',scheme:'myapp',host:'',path:'',pathType:'path',autoVerify:false});
  renderDeeplinks(); markDirty(); refreshPreview(); }
function removeDeeplink(i){ DLS.splice(i,1); renderDeeplinks(); markDirty(); refreshPreview(); }

let pvTimer=null;
function refreshPreview(){ clearTimeout(pvTimer); pvTimer=setTimeout(doPreview,180); }
async function doPreview(){
  const r=await fetch('/enpaf-api/config/preview',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(collect())});
  showPreview(await r.json());
}
function collect(){
  return {
    general: GEN,
    permissions: [...PERMS],
    features: Object.keys(FEATS).map(k=>({key:k,required:FEATS[k]})),
    deeplinks: DLS,
  };
}
async function save(){
  const btn=$('#save'); btn.disabled=true; const old=btn.textContent; btn.textContent='Сохранение…';
  try{
    const r=await fetch('/enpaf-api/config',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(collect())});
    const res=await r.json();
    if(res.success){ toast('Сохранено в enpaf.json ✓'); clearDirty(); if(res.preview) showPreview(res.preview); }
    else toast(res.error||'Не удалось сохранить', true);
  }catch(e){ toast('Ошибка: '+e, true); }
  btn.disabled=false; btn.textContent=old;
}
function showPreview(p){
  const perm=p.permissions_xml||'    (нет разрешений)';
  const feat=p.features_xml||'    (нет фич)';
  const dl=p.deeplinks_xml||'            (нет deep links)';
  $('#preview').textContent='<!-- в <manifest> -->\n'+perm+'\n'+feat+'\n\n<!-- внутри <activity> -->\n'+dl;
}
function copyPreview(){ navigator.clipboard.writeText($('#preview').textContent).then(()=>toast('Скопировано ✓')); }

function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function toast(msg,err){ const t=$('#toast'); t.textContent=msg; t.className='toast show'+(err?' err':'');
  setTimeout(()=>t.className='toast'+(err?' err':''),2600); }

// Sidebar active state on scroll
const _secs=[...document.querySelectorAll('.card[id]')];
const _navs=[...document.querySelectorAll('.side a')];
const _spy=new IntersectionObserver(es=>{
  es.forEach(e=>{ if(e.isIntersecting){
    _navs.forEach(n=>n.classList.toggle('active', n.getAttribute('href')==='#'+e.target.id)); }});
},{rootMargin:'-45% 0px -50% 0px'});
_secs.forEach(s=>_spy.observe(s));

window.addEventListener('beforeunload', e=>{ if(DIRTY){ e.preventDefault(); e.returnValue=''; } });
load();
</script>
</body>
</html>
"""

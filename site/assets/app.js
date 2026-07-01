/* ENPAF site — logo injection + animations. No dependencies. */
(function () {
  "use strict";

  let _uid = 0;
  function grad(id) {
    return `<linearGradient id="${id}" x1="0" y1="0" x2="1" y2="1">` +
      `<stop offset="0" stop-color="#4aa6ff"/>` +
      `<stop offset=".45" stop-color="#5b8cff"/>` +
      `<stop offset="1" stop-color="#ff6ad5"/></linearGradient>`;
  }

  // ── ENPAF brand mark: an isometric gradient cube — a packaged build (your
  //    Python + Web app, shipped as an APK). Abstract & geometric. ──
  function makeBrandLogo() {
    const id = "lg" + _uid++;
    // vertices (cx 100, cy 102, R 66)
    const top = "100,36", tr = "157.2,69", br = "157.2,135",
      bot = "100,168", bl = "42.8,135", tl = "42.8,69", M = "100,102";
    return `
<svg viewBox="0 0 200 200" width="100%" height="100%">
  <defs>${grad(id)}</defs>
  <g stroke="url(#${id})" stroke-width="2" stroke-linejoin="round">
    <polygon points="${top} ${tr} ${M} ${tl}" fill="url(#${id})"/>
    <polygon points="${tl} ${M} ${bot} ${bl}" fill="url(#${id})"/>
    <polygon points="${tr} ${br} ${bot} ${M}" fill="url(#${id})"/>
  </g>
  <polygon points="${top} ${tr} ${M} ${tl}" fill="#ffffff" opacity=".22"/>
  <polygon points="${tr} ${br} ${bot} ${M}" fill="#0a0e27" opacity=".34"/>
</svg>`;
  }

  // ── Companion mark: three evenly-spaced concentric strokes — ring, C, O ──
  function makeCompanionLogo() {
    const id = "lg" + _uid++;
    return `
<svg viewBox="0 0 200 200" width="100%" height="100%">
  <defs>${grad(id)}</defs>
  <g fill="none" stroke="url(#${id})" stroke-width="13">
    <circle cx="100" cy="100" r="78"/>
    <path d="M135.6 65.3 A50 50 0 1 0 135.6 134.7"/>
    <circle cx="100" cy="100" r="22"/>
  </g>
</svg>`;
  }

  ["brandMark", "heroLogo", "footMark"].forEach(function (sel) {
    const el = document.getElementById(sel);
    if (el) el.innerHTML = makeBrandLogo();
  });
  const phoneLogoEl = document.getElementById("phoneLogo");
  if (phoneLogoEl) phoneLogoEl.innerHTML = makeCompanionLogo();

  const translations = {
    ru: {
      htmlLang: "ru",
      title: "ENPAF — Android-приложения на Python и веб-технологиях",
      description: "ENPAF помогает собирать Android APK из Python-логики и интерфейса на HTML/CSS/JS. Быстрый старт, живой предпросмотр и сборка установочного APK одной командой.",
      ogDescription: "Создавайте Android-приложения с Python-логикой, веб-интерфейсом и сборкой APK одной командой.",
      copy: "Копировать",
      copied: "Скопировано ✓",
      entries: [
        [".nav-links a[href='#features']", "Возможности"],
        [".nav-links a[href='#how']", "Как работает"],
        [".nav-links a[href='#cli']", "CLI"],
        [".nav-links a[href='#companion']", "Companion"],
        [".nav-links a[href='#docs']", "Документация"],
        [".nav-cta > a.btn-ghost", "GitHub"],
        [".nav-cta > a.btn-primary", "Старт"],
        [".pill-row .pill:first-child", "Python + Web → APK"],
        [".hero-title", "Android-приложения <span class='grad'>на Python</span><br />и привычном Web UI", "html"],
        [".hero-sub", "ENPAF соединяет Python-логику с интерфейсом на HTML/CSS/JS и собирает проект в устанавливаемый <strong>APK</strong>. Быстрый предпросмотр в браузере, доступ к возможностям устройства и без лишней инфраструктуры.", "html"],
        [".hero .hero-actions .btn-primary", "Начать работу →"],
        [".hero .hero-actions .btn-glass", "Открыть документацию"],
        [".hero .copy-btn", "Копировать"],
        [".badges .badge:nth-child(1)", "Python 3.9+"],
        [".badges .badge:nth-child(2)", "12 модулей для Android"],
        [".badges .badge:nth-child(3)", "171 тест · CI"],
        [".badges .badge:nth-child(4)", "Бесплатно для некоммерческих проектов"],
        ["#features .eyebrow", "Зачем ENPAF"],
        ["#features h2", "Пишите мобильную логику на Python, а интерфейс — как обычный сайт"],
        ["#features .lead", "Один проект вместо разрозненной связки инструментов: разработка, предпросмотр и сборка APK в понятном рабочем процессе."],
        [".features .card:nth-child(1) h3", "Python-бэкенд"],
        [".features .card:nth-child(1) p", "Маршруты, обработчики bridge, события и SQLite-хранилище остаются в Python-коде, без переписывания бизнес-логики на Java или Kotlin."],
        [".features .card:nth-child(2) h3", "Веб-фронтенд"],
        [".features .card:nth-child(2) p", "Интерфейс пишется на HTML/CSS/JS. Можно начать с простых файлов и не тащить сборщик, пока он действительно не нужен."],
        [".features .card:nth-child(3) h3", "Двусторонний bridge"],
        [".features .card:nth-child(3) p", "Фронтенд вызывает Python через <code>await enpaf.call()</code>, а Python отправляет события обратно через <code>app.emit()</code>. Связь предсказуемая и явная.", "html"],
        [".features .card:nth-child(4) h3", "Возможности устройства"],
        [".features .card:nth-child(4) p", "Wi-Fi, Bluetooth, сенсоры, NFC, геолокация, камера, аудио, батарея, уведомления, биометрия и разрешения доступны из Python и JS."],
        [".features .card:nth-child(5) h3", "Сборка одной командой"],
        [".features .card:nth-child(5) p", "<code>paf build apk</code> собирает устанавливаемый APK на Windows, macOS или Linux через Gradle + Chaquopy.", "html"],
        [".features .card:nth-child(6) h3", "Живой dev-сервер"],
        [".features .card:nth-child(6) p", "<code>paf run</code> запускает приложение в браузере с hot-reload, чтобы быстро проверять изменения без постоянной установки на телефон.", "html"],
        ["#how .eyebrow", "Как это работает"],
        ["#how h2", "Python-логика для интерфейса на JavaScript"],
        ["#how .lead", "Опишите обработчик в Python, вызовите его из UI и получите результат обратно. Для событий работает тот же понятный канал."],
        [".code-split .code-card:nth-child(2) pre.code", "<span class='c'>// Вызов Python из интерфейса</span>\n<span class='k'>const</span> res = <span class='k'>await</span> enpaf.<span class='fn'>call</span>(<span class='s'>\"hello\"</span>, { name: <span class='s'>\"Alex\"</span> });\nenpaf.device.<span class='fn'>toast</span>(res.message); <span class='c'>// \"Hi, Alex!\"</span>\n\n<span class='c'>// События из Python</span>\nenpaf.<span class='fn'>on</span>(<span class='s'>\"progress\"</span>, (d) => updateBar(d.percent));\n\n<span class='c'>// Данные, датчики и разрешения из JS</span>\n<span class='k'>await</span> enpaf.storage.<span class='fn'>set</span>(<span class='s'>\"theme\"</span>, <span class='s'>\"dark\"</span>);\n<span class='k'>const</span> acc = <span class='k'>await</span> enpaf.sensors.<span class='fn'>read</span>(<span class='s'>\"accelerometer\"</span>);\n<span class='k'>await</span> enpaf.permissions.<span class='fn'>request</span>([<span class='s'>\"CAMERA\"</span>]);", "html"],
        [".steps .step:nth-child(1) b", "Разработайте"],
        [".steps .step:nth-child(1) p", "Python-логику и Web UI в одном проекте."],
        [".steps .step:nth-child(3) b", "Проверьте"],
        [".steps .step:nth-child(3) p", "<code>paf run</code> с живым предпросмотром.", "html"],
        [".steps .step:nth-child(5) b", "Соберите"],
        [".steps .step:nth-child(5) p", "<code>paf build apk</code> → установочный APK.", "html"],
        ["#cli .eyebrow", "CLI <code>paf</code>", "html"],
        ["#cli h2", "Один CLI для разработки, проверки и сборки"],
        [".cli-grid .cli-row:nth-child(1) span", "Создать структуру проекта"],
        [".cli-grid .cli-row:nth-child(2) span", "Запустить предпросмотр с hot-reload"],
        [".cli-grid .cli-row:nth-child(3) span", "Передать сборку на устройство по Wi-Fi"],
        [".cli-grid .cli-row:nth-child(4) span", "Собрать установочный APK"],
        [".cli-grid .cli-row:nth-child(5) span", "Проверить JDK, SDK и окружение"],
        [".cli-grid .cli-row:nth-child(6) span", "Посмотреть конфигурацию проекта"],
        [".cli-grid .cli-row:nth-child(7) span", "Обновить PAF"],
        ["#cli > p.center.muted", "Полная справка в <a href='https://github.com/aaalllexxx/enpaf/wiki/CLI-Reference' target='_blank' rel='noopener'>документации CLI →</a>", "html"],
        ["#capabilities .eyebrow", "Доступ к устройству"],
        ["#capabilities h2", "Используйте возможности Android без нативной рутины"],
        ["#capabilities .lead", "Модули доступны из Python через <code>app</code> и из интерфейса через helpers <code>enpaf</code>.", "html"],
        [".chips .chip:nth-child(3)", "Сенсоры"],
        [".chips .chip:nth-child(5)", "Геолокация"],
        [".chips .chip:nth-child(6)", "Камера / медиа"],
        [".chips .chip:nth-child(7)", "Аудио"],
        [".chips .chip:nth-child(8)", "Батарея"],
        [".chips .chip:nth-child(9)", "Уведомления"],
        [".chips .chip:nth-child(10)", "Биометрия"],
        [".chips .chip:nth-child(11)", "Permissions"],
        [".chips .chip:nth-child(12)", "Данные устройства"],
        ["#companion .eyebrow", "Companion app"],
        ["#companion h2", "Быстрая установка тестовых сборок по Wi-Fi"],
        ["#companion .lead", "Откройте QR из <code>paf serve</code>, и Companion загрузит APK на устройство без кабеля и ручной передачи файлов.", "html"],
        [".ticks li:nth-child(1)", "QR-сканер и загрузка по ссылке"],
        [".ticks li:nth-child(2)", "Уведомления, когда сборка обновилась"],
        [".ticks li:nth-child(3)", "Избранные и недавние проекты"],
        [".ticks li:nth-child(4)", "Диагностика устройства и проверка соединения"],
        [".ticks li:nth-child(5)", "Защита приложения биометрией"],
        ["#companion .hero-actions .btn-primary", "Скачать APK"],
        ["#companion .hero-actions .btn-glass", "Подробнее"],
        [".ph-title", "ENPAF Companion"],
        ["#quickstart .eyebrow", "Быстрый старт"],
        ["#quickstart h2", "Первый проект за несколько минут"],
        [".terminal pre.code", "<span class='tok-dim'>$</span> pip install enpaf\n<span class='tok-dim'>$</span> paf create myapp\n<span class='tok-dim'>$</span> cd myapp\n<span class='tok-dim'>$</span> paf run            <span class='c'># предпросмотр на http://127.0.0.1:8080</span>\n<span class='tok-dim'>$</span> paf build apk      <span class='c'># → dist/myapp-1.0.0.apk</span>", "html"],
        ["#quickstart > p.center.muted", "Для сборки APK понадобятся JDK 17–21 и Android SDK. Команда <code>paf doctor</code> проверит окружение и подскажет, что настроить. См. <a href='https://github.com/aaalllexxx/enpaf/wiki/Installation' target='_blank' rel='noopener'>инструкцию по установке →</a>", "html"],
        ["#docs .eyebrow", "Документация"],
        ["#docs h2", "Документация для разработки и релиза"],
        ["#docs .lead", "Wiki покрывает установку, API, bridge, возможности устройства, сборку APK и типовые проблемы."],
        [".docs .doc-card:nth-child(1) h3", "Установка"],
        [".docs .doc-card:nth-child(1) p", "Фреймворк и инструменты сборки."],
        [".docs .doc-card:nth-child(2) h3", "Быстрый старт"],
        [".docs .doc-card:nth-child(2) p", "Минимальный путь от установки до запуска."],
        [".docs .doc-card:nth-child(3) h3", "Python API"],
        [".docs .doc-card:nth-child(3) p", "<code>EnpafApp</code>, routes, handlers, events.", "html"],
        [".docs .doc-card:nth-child(4) h3", "JavaScript Bridge"],
        [".docs .doc-card:nth-child(4) p", "Полный клиентский SDK <code>enpaf.*</code>.", "html"],
        [".docs .doc-card:nth-child(5) h3", "Возможности устройства"],
        [".docs .doc-card:nth-child(5) p", "Сенсоры, NFC, Wi-Fi, BT и другое."],
        [".docs .doc-card:nth-child(6) h3", "Сборка APK"],
        [".docs .doc-card:nth-child(6) p", "Gradle + Chaquopy, подпись, релиз."],
        [".docs .doc-card:nth-child(7) h3", "Архитектура"],
        [".docs .doc-card:nth-child(7) p", "Как работают dev-режим и Android-режим."],
        [".docs .doc-card:nth-child(8) h3", "Решение проблем"],
        [".docs .doc-card:nth-child(8) p", "Ошибки сборки, окружение, OneDrive, JDK."],
        [".cta h2", "Попробуйте собрать первый APK"],
        [".cta .lead", "Установите ENPAF, создайте проект и проверьте, как Python-логика работает вместе с Web UI."],
        [".cta .copy-btn", "Копировать"],
        [".cta .hero-actions .btn-primary", "Открыть GitHub"],
        [".cta .hero-actions .btn-glass", "Открыть PyPI"],
        [".footer-brand .muted.small", "Engine for Native Python App Framework"],
        [".footer-links a:nth-child(2)", "Wiki"],
        [".footer-links a:nth-child(4)", "Релизы"],
        [".footer-links a:nth-child(5)", "Issues"],
        [".footer-links a:nth-child(6)", "Лицензия"],
        [".footer-bottom", "© 2026 ENPAF · PolyForm Noncommercial 1.0.0 — бесплатно для некоммерческого использования", "html"],
        [".visits-label", "Посетителей:"]
      ]
    }
  };

  translations.en = {
    htmlLang: "en",
    title: "ENPAF — Build native Android apps with Python + Web",
    description: "ENPAF is a framework for building real Android APKs with Python and HTML/CSS/JS. Write your UI on the web stack, your logic in Python, ship a native app.",
    ogDescription: "Write your UI in HTML/CSS/JS, your logic in Python, and ship a real Android APK.",
    copy: "Copy",
    copied: "Copied ✓",
    entries: translations.ru.entries.map(function (entry) {
      const el = document.querySelector(entry[0]);
      const mode = entry[2];
      return [entry[0], el ? (mode === "html" ? el.innerHTML : el.textContent) : entry[1], mode];
    })
  };

  function setMeta(selector, value) {
    const el = document.querySelector(selector);
    if (el) el.setAttribute("content", value);
  }

  function applyLanguage(lang) {
    const pack = translations[lang] || translations.ru;
    document.documentElement.lang = pack.htmlLang;
    document.title = pack.title;
    setMeta("meta[name='description']", pack.description);
    setMeta("meta[property='og:description']", pack.ogDescription);
    pack.entries.forEach(function (entry) {
      const el = document.querySelector(entry[0]);
      if (!el) return;
      if (entry[2] === "html") el.innerHTML = entry[1];
      else el.textContent = entry[1];
    });
    document.querySelectorAll("[data-lang-btn]").forEach(function (btn) {
      const isActive = btn.getAttribute("data-lang-btn") === lang;
      btn.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
    try { localStorage.setItem("enpaf-lang", lang); } catch (e) {}
  }

  let initialLang = "ru";
  try {
    const storedLang = localStorage.getItem("enpaf-lang");
    if (storedLang === "ru" || storedLang === "en") initialLang = storedLang;
  } catch (e) {}

  document.querySelectorAll("[data-lang-btn]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      applyLanguage(btn.getAttribute("data-lang-btn"));
    });
  });
  applyLanguage(initialLang);

  // ── Sticky nav condense on scroll ──
  const nav = document.getElementById("nav");
  const onScroll = function () {
    if (window.scrollY > 24) nav.classList.add("scrolled");
    else nav.classList.remove("scrolled");
  };
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  // ── Scroll reveal ──
  const reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add("in"); });
  }

  // ── Copy-to-clipboard ──
  document.querySelectorAll(".code-inline").forEach(function (box) {
    const btn = box.querySelector(".copy-btn");
    if (!btn) return;
    btn.addEventListener("click", function () {
      const text = box.getAttribute("data-copy") || box.querySelector("code").textContent;
      const done = function () {
        const lang = document.documentElement.lang === "en" ? "en" : "ru";
        const old = translations[lang].copy;
        btn.textContent = translations[lang].copied;
        btn.classList.add("ok");
        setTimeout(function () { btn.textContent = old; btn.classList.remove("ok"); }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(fallback);
      } else {
        fallback();
      }
      function fallback() {
        const ta = document.createElement("textarea");
        ta.value = text; document.body.appendChild(ta); ta.select();
        try { document.execCommand("copy"); done(); } catch (e) {}
        document.body.removeChild(ta);
      }
    });
  });

  // ── Visitor counter (server-backed, persisted to guest.stxt) ──
  (function visitorCounter() {
    const box = document.getElementById("visits");
    const out = document.getElementById("visitsCount");
    if (!box || !out) return;

    // Only count a given browser once per session, but always show the total.
    let seen = false;
    try { seen = sessionStorage.getItem("enpaf-visited") === "1"; } catch (e) {}

    fetch("/api/visits" + (seen ? "?peek=1" : ""), { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data || typeof data.count !== "number") return; // static hosting: stay hidden
        try { sessionStorage.setItem("enpaf-visited", "1"); } catch (e) {}
        out.textContent = data.count.toLocaleString(
          document.documentElement.lang === "en" ? "en-US" : "ru-RU"
        );
        box.hidden = false;
      })
      .catch(function () { /* no endpoint (plain static host) — leave hidden */ });
  })();
})();

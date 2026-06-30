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
<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
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
<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
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
        const old = btn.textContent;
        btn.textContent = "Copied ✓";
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
})();

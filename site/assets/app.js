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

  // ── ENPAF brand mark: an 'E' monogram (E = ENPAF) in the gradient ──
  function makeBrandLogo() {
    const id = "lg" + _uid++;
    const d = "M 60 56 Q 60 42 74 42 L 132 42 Q 146 42 146 56 L 146 58 Q 146 72 132 72 " +
      "L 90 72 L 90 85 L 112 85 Q 126 85 126 99 L 126 101 Q 126 115 112 115 L 90 115 " +
      "L 90 132 L 132 132 Q 146 132 146 146 L 146 148 Q 146 162 132 162 L 74 162 Q 60 162 60 148 Z";
    return `
<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
  <defs>${grad(id)}</defs>
  <path fill="url(#${id})" d="${d}"/>
</svg>`;
  }

  // ── Companion mark: gear → C → O (the Companion's app icon); gear spins ──
  function makeGearLogo() {
    const id = "lg" + _uid++;
    let teeth = "";
    for (let i = 0; i < 8; i++) {
      teeth += `<line x1="100" y1="40" x2="100" y2="22" transform="rotate(${i * 45} 100 100)"/>`;
    }
    return `
<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
  <defs>${grad(id)}</defs>
  <g fill="none" stroke="url(#${id})" stroke-width="11" stroke-linecap="round" stroke-linejoin="round">
    <g class="gear-spin"><circle cx="100" cy="100" r="58"/>${teeth}</g>
    <path d="M122.8 74.7 A34 34 0 1 0 122.8 125.3"/>
    <circle cx="100" cy="100" r="13" stroke-width="9"/>
  </g>
</svg>`;
  }

  ["brandMark", "heroLogo", "footMark"].forEach(function (sel) {
    const el = document.getElementById(sel);
    if (el) el.innerHTML = makeBrandLogo();
  });
  const phoneLogoEl = document.getElementById("phoneLogo");
  if (phoneLogoEl) phoneLogoEl.innerHTML = makeGearLogo();

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

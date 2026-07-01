# ENPAF product site

A modern, single-page marketing + documentation site for ENPAF, styled after the
Companion app (blue → pink on deep navy, glassmorphism, animated). It links out
to the GitHub repo, Wiki, PyPI and Releases.

It's a fully static site (HTML/CSS/JS, no build step) served by **Python's
standard-library `http.server` on port 5000** — no nginx, no extra packages.

```
site/
├── index.html          # the page
├── assets/
│   ├── style.css       # theme + animations
│   ├── app.js          # logo injection, scroll-reveal, copy buttons
│   ├── favicon.svg     # ENPAF "E ▶" mark (transparent)
│   └── og.png          # social preview image
├── Dockerfile          # python:3.12-alpine, http.server on :5000
└── docker-compose.yml
```

## Run with Docker

```bash
cd site

# Option A — docker compose
docker compose up -d --build

# Option B — plain docker
docker build -t enpaf-site .
docker run -d --name enpaf-site -p 5000:5000 enpaf-site
```

Then open **http://localhost:5000**.

Stop it:

```bash
docker compose down
# or
docker rm -f enpaf-site
```

## Run without Docker (quick preview)

```bash
cd site
python -m http.server 5000
# → http://localhost:5000
```

## Production (enpaf.labunit.ru) — TLS + security headers

The public site runs this container on `127.0.0.1:5000` behind **nginx**, which
terminates TLS. The **"connection not secure" browser flag / HSTS** is fixed at
the nginx layer, **not** in this repo — you must apply it on the server.

`nginx.conf.example` is a complete drop-in. To apply it:

```bash
# on the server
sudo cp nginx.conf.example /etc/nginx/sites-available/enpaf.labunit.ru
sudo ln -sf /etc/nginx/sites-available/enpaf.labunit.ru \
            /etc/nginx/sites-enabled/enpaf.labunit.ru
sudo nginx -t && sudo systemctl reload nginx
```

If you already have a working TLS server block, just paste the `add_header`
lines from the `HTTPS :443` block (HSTS/CSP/X-Frame-Options/…) into it and
reload. The key one for "use HTTPS only" is:

```nginx
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
```

Verify afterwards:

```bash
curl -sSI https://enpaf.labunit.ru/ | grep -i strict-transport   # -> should print the header
```

## Notes

- No external runtime dependencies — fonts load from Google Fonts (with a system
  fallback), everything else is local, so it works offline too.
- Logos are inline SVG generated in `app.js`: the brand mark is an **"E ▶"** badge
  (E = ENPAF, the arrow = "Python + Web → APK"); the phone mockup shows the
  **Companion** mark (concentric ring → C → O). Animations respect
  `prefers-reduced-motion`.
- Edit copy/links directly in `index.html`; the version badge is in the hero.

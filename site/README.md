# ENPAF product site

A modern, single-page marketing + documentation site for ENPAF, styled after the
Companion app (blue → pink on deep navy, glassmorphism, animated). It links out
to the GitHub repo, Wiki, PyPI and Releases.

It's a fully static site (HTML/CSS/JS, no build step) served by **nginx on port 5000**.

```
site/
├── index.html          # the page
├── assets/
│   ├── style.css       # theme + animations
│   ├── app.js          # logo injection, scroll-reveal, copy buttons
│   ├── favicon.svg     # gear → C → O mark
│   └── og.png          # social preview image
├── Dockerfile          # nginx:alpine, listens on :5000
├── nginx.conf
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

## Notes

- No external runtime dependencies — fonts load from Google Fonts (with a system
  fallback), everything else is local, so it works offline too.
- The logo is an inline SVG (gear → C → O) generated in `app.js`; the gear slowly
  rotates. Animations respect `prefers-reduced-motion`.
- Edit copy/links directly in `index.html`; the version badge is in the hero
  (`v1.1.1`).

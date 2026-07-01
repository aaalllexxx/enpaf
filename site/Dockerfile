# ENPAF product site — static page + visitor counter, served by a small stdlib
# Python server on :5000. No nginx, no third-party packages.
FROM python:3.12-alpine

WORKDIR /site

# Copy only the site itself (not the Docker/compose/readme files).
COPY server.py        ./server.py
COPY index.html       ./index.html
COPY robots.txt       ./robots.txt
COPY sitemap.xml      ./sitemap.xml
COPY site.webmanifest ./site.webmanifest
COPY favicon.ico      ./favicon.ico
COPY guest.stxt       ./guest.stxt
COPY assets/          ./assets/

EXPOSE 5000

# server.py binds 0.0.0.0:5000, serves the site and the /api/visits counter.
# Mount a volume on /site/guest.stxt to persist the count across rebuilds.
CMD ["python", "server.py"]

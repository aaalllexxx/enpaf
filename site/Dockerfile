# ENPAF product site — static page served by Python's stdlib http.server on :5000.
# No nginx, no third-party packages.
FROM python:3.12-alpine

WORKDIR /site

# Copy only the site itself (not the Docker/compose/readme files).
COPY index.html   ./index.html
COPY robots.txt   ./robots.txt
COPY sitemap.xml  ./sitemap.xml
COPY assets/      ./assets/

EXPOSE 5000

# http.server binds 0.0.0.0 and serves the working directory.
CMD ["python", "-m", "http.server", "5000", "--bind", "0.0.0.0"]

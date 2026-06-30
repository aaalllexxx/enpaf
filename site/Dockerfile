# ENPAF product site — static page served by nginx on port 5000.
FROM nginx:1.27-alpine

# Replace the default server with our :5000 config.
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/enpaf.conf

# Copy only the site itself (not the Docker/compose files).
COPY index.html /usr/share/nginx/html/index.html
COPY assets/    /usr/share/nginx/html/assets/

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -qO- http://127.0.0.1:5000/ >/dev/null 2>&1 || exit 1

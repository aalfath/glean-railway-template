# Glean admin dashboard, upstream image pinned by version and digest.
# Our nginx config proxies /api to the backend over Railway's private network.
FROM ghcr.io/leslieleung/glean-admin:0.3.0@sha256:3f93f74c9a4fe5802298751b26376c40ce9d6c174bd6e3e20cd56865669d1bcc
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY 05-glean-railway.sh /docker-entrypoint.d/05-glean-railway.sh
RUN chmod +x /docker-entrypoint.d/05-glean-railway.sh && rm /etc/nginx/conf.d/default.conf
ENV PORT=8080 NGINX_ENTRYPOINT_QUIET_LOGS=1
EXPOSE 8080

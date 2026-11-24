# Glean web app (reader UI), upstream image pinned by version and digest.
# Our nginx config proxies /api and /mcp to the backend over Railway's private network.
FROM ghcr.io/leslieleung/glean-web:0.3.0@sha256:668f741feae8f363df440fd6aff459816bbf4f13baa9428bb83c8aa1e6cb66c1
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY 05-glean-railway.sh /docker-entrypoint.d/05-glean-railway.sh
RUN chmod +x /docker-entrypoint.d/05-glean-railway.sh && rm /etc/nginx/conf.d/default.conf
ENV PORT=8080 NGINX_ENTRYPOINT_QUIET_LOGS=1
EXPOSE 8080

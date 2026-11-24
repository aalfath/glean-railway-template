# Glean API and worker (one image, role chosen by GLEAN_ROLE).
# Built from the pinned upstream release commit instead of the upstream image:
# ghcr.io/leslieleung/glean-backend:0.3.0 is 4.3 GB (CUDA torch), over Railway's
# 4 GB image cap on Free/Trial. This build leaves out torch and
# sentence-transformers (the local embedding provider); everything else uses
# upstream's locked versions from uv.lock.
FROM ghcr.io/astral-sh/uv:0.13.9@sha256:d3b601f0c7b118bc1753febf7c41cc80981df678445e0254284eecf84db79a7d AS uv

FROM python:3.14.10-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS build
# Glean v0.3.0
ARG GLEAN_COMMIT=3a0c39dc3b9d639c0ca34bb417367c4cee95da4f
COPY --from=uv /uv /usr/local/bin/uv
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git init -q . \
 && git remote add origin https://github.com/LeslieLeung/glean.git \
 && git fetch -q --depth 1 origin "$GLEAN_COMMIT" \
 && git checkout -q FETCH_HEAD \
 && test "$(git rev-parse HEAD)" = "$GLEAN_COMMIT"
WORKDIR /src/backend
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_COMPILE_BYTECODE=1
COPY prune-lock.py /tmp/prune-lock.py
# Upstream logs every SQL statement at INFO; Railway caps logs at 500 lines/s.
RUN sed -i 's/logging.getLogger(logger_name).setLevel(logging.INFO)/logging.getLogger(logger_name).setLevel(logging.WARNING if logger_name == "sqlalchemy" else logging.INFO)/' \
      packages/core/glean_core/logging_config.py \
 && grep -q 'WARNING if logger_name == "sqlalchemy"' packages/core/glean_core/logging_config.py
RUN uv export --frozen --all-packages --no-dev --no-emit-workspace --no-hashes \
      | python /tmp/prune-lock.py uv.lock > /tmp/requirements.txt \
 && uv venv /app/.venv \
 && VIRTUAL_ENV=/app/.venv uv pip install --no-deps -r /tmp/requirements.txt \
 && VIRTUAL_ENV=/app/.venv uv pip install --no-deps \
      ./packages/core ./packages/database ./packages/rss ./packages/vector \
      ./apps/api ./apps/worker \
 && ! /app/.venv/bin/python -c "import torch" 2>/dev/null \
 && /app/.venv/bin/python -c "import glean_api.main, glean_worker.main"

FROM python:3.14.10-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f
COPY --from=build /src/backend /app
COPY --from=build /app/.venv /app/.venv
COPY start.sh bootstrap.py serve.py /opt/glean/
RUN chmod +x /opt/glean/start.sh
WORKDIR /app
ENV PATH=/app/.venv/bin:$PATH \
    APP_VERSION=0.3.0 \
    PYTHONUNBUFFERED=1 \
    MALLOC_ARENA_MAX=2
EXPOSE 8000
CMD ["/opt/glean/start.sh"]

FROM node:22-bookworm-slim AS web
WORKDIR /web
COPY web/ ./
RUN npm install && npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV MOKLI_HOST=0.0.0.0
ENV MOKLI_DATA_DIR=/data
COPY pyproject.toml README.md ./
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
COPY rules ./rules
COPY deploy ./deploy
COPY docs ./docs
RUN pip install --no-cache-dir .
COPY --from=web /web/dist ./web/dist
EXPOSE 8787
CMD ["mokli", "serve"]

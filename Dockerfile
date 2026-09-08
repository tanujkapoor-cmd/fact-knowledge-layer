FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FKL_DATABASE_URL=sqlite:////data/fact_knowledge_layer.db
WORKDIR /app
COPY pyproject.toml ./
COPY backend/ backend/
RUN pip install --no-cache-dir .
COPY --from=frontend /app/frontend/dist frontend/dist/
COPY config/ config/
RUN mkdir -p /data
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

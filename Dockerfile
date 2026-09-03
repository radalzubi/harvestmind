FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HARVESTMIND_DATA_ROOT=/var/lib/harvestmind \
    DUCKDB_PATH=/var/lib/harvestmind/root.duckdb

WORKDIR /app
COPY pyproject.toml ./
COPY . ./
RUN pip install --no-cache-dir --upgrade "pip>=26.2" "setuptools>=83" \
    && pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 harvestmind \
    && mkdir -p /var/lib/harvestmind \
    && chown -R harvestmind:harvestmind /var/lib/harvestmind /app
USER harvestmind

# The image binds all interfaces; the app refuses to start permissive.
ENV HARVESTMIND_BIND_HOST=0.0.0.0 \
    HARVESTMIND_ENV=pilot
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

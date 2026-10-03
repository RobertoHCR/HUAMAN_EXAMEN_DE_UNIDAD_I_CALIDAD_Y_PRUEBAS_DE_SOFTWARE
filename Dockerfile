FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATABASE_PATH=/home/data/courtflow.db
WORKDIR /app
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 courtflow && useradd --uid 10001 --gid courtflow --no-create-home courtflow \
    && mkdir -p /home/data && chown -R courtflow:courtflow /home/data
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=courtflow:courtflow app ./app
USER courtflow
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-server-header"]

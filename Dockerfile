FROM python:3.12-slim
# LibreOffice (PDF fedele al Word), ffmpeg (fotogrammi dei video), font metricamente compatibili con Calibri (Carlito)
RUN apt-get update && apt-get install -y --no-install-recommends \
      libreoffice-writer ffmpeg fonts-crosextra-carlito fonts-dejavu-core libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
RUN useradd -m app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app . .
RUN mkdir -p /data && chown app:app /data
USER app
ENV HOME=/home/app APP_DATA_DIR=/data PORT=8000 RETENTION_HOURS=72
VOLUME /data
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request,os;urllib.request.urlopen('http://localhost:'+os.environ.get('PORT','8000')+'/api/health')"
CMD ["sh", "-c", "python -m antincendio_app serve --port ${PORT:-8000}"]

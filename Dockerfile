FROM python:3.11-slim

WORKDIR /app

# Install build deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel setuptools \
 && pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ ./src/
COPY scripts/ ./scripts/

# Install the package
RUN pip install --no-cache-dir -e .

# Run as non-root
RUN useradd -m -u 1000 app && chown -R app:app /app
USER app

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:10000/health').read()" || exit 1

CMD ["uvicorn", "lineagepulse.web:app", "--host", "0.0.0.0", "--port", "10000"]

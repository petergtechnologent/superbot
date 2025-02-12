# Use a lightweight Python base image
FROM python:3.10-slim

WORKDIR /app

# Copy in requirements first, so we can cache them
COPY requirements.txt .

# Install Docker CLI and other needed packages, then remove apt cache
RUN apt-get update \
    && apt-get install -y docker.io \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI application
COPY app/ ./app

# Expose port 8000 (optional, for local debugging)
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

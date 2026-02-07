# ---- Base image (Python 3.11 is safest for torch/faiss) ----
FROM python:3.11-slim

# ---- Environment ----
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---- System deps ----
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Workdir ----
WORKDIR /app

# ---- Install Python deps first (better caching) ----
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---- Copy app ----
COPY . .

# ---- Expose port (Render uses $PORT, Docker uses 8000) ----
EXPOSE 8000

# ---- Start FastAPI ----
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]









FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

COPY . .

# Rendre le script d'entrée exécutable
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

# Utiliser le script d'entrée (migrations + gunicorn)
CMD ["/app/entrypoint.sh"]
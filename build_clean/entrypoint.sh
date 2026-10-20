#!/bin/sh
set -e

echo "🔄 Application des migrations..."
python manage.py migrate --noinput
echo "✅ Migrations appliquées"

echo "📦 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput
echo "✅ Fichiers statiques collectés"

echo "🚀 Démarrage de Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120

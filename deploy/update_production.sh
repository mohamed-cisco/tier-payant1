#!/bin/bash

set -e

APP_DIR="/var/www/tiers_payant"

echo "=== Mise à jour Tiers Payant ==="

cd "$APP_DIR"

# Sans cette variable, check et collectstatic s'exécuteraient sur config.settings
# (DEBUG=True) et valideraient donc la mauvaise configuration.
export DJANGO_SETTINGS_MODULE=config.settings_production

if [ ! -f .env ]; then
    echo "ERREUR : fichier .env absent de $APP_DIR" >&2
    echo "Copiez .env.example vers .env et renseignez les valeurs de production." >&2
    exit 1
fi

echo "=== Activation de l'environnement Python ==="
source venv/bin/activate

echo "=== Installation des dépendances ==="
pip install -r requirements.txt

echo "=== Vérification Django ==="
python manage.py check --deploy

echo "=== Collecte des fichiers statiques ==="
python manage.py collectstatic --noinput

echo "=== Redémarrage de Gunicorn ==="
sudo systemctl restart tiers-payant

echo "=== Mise à jour terminée ==="

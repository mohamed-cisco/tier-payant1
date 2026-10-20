"""Parametres de production du projet Tiers Payant.

A utiliser via DJANGO_SETTINGS_MODULE=config.settings_production.

DEBUG y est force a False et les valeurs sensibles sont obligatoires : le
module echoue au demarrage plutot que de tourner avec une configuration
incomplete. Les variables d'environnement proviennent du service systemd ou
du fichier .env (voir .env.example).

Les en-tetes HTTPS sont desactives par defaut : un intranet sert souvent le
site en HTTP simple. Activez SECURE_SSL_REDIRECT=True des que le site passe
en HTTPS, les cookies securises suivront automatiquement.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

VRAIS = ('1', 'true', 'yes', 'oui', 'on')


def env_bool(nom, defaut=False):
    return os.getenv(nom, str(defaut)).strip().lower() in VRAIS


def env_int(nom, defaut):
    return int(os.getenv(nom, str(defaut)).strip() or defaut)


def env_list(nom, defaut=''):
    return [v.strip() for v in os.getenv(nom, defaut).split(',') if v.strip()]


def exiger(nom):
    valeur = os.getenv(nom, '').strip()
    if not valeur:
        raise ImproperlyConfigured(
            "%s est absente en production. Renseignez-la dans l'environnement "
            "du service systemd ou dans .env." % nom
        )
    return valeur


SECRET_KEY = exiger('DJANGO_SECRET_KEY')

DEBUG = False

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS')
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS est vide : avec DEBUG=False, Django repondrait "
        "400 a toutes les requetes. Listez les noms d'hotes de l'intranet, "
        "separes par des virgules."
    )


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': exiger('DB_NAME'),
        'USER': exiger('DB_USER'),
        'PASSWORD': exiger('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / os.getenv('STATIC_ROOT', 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'ne-pas-repondre@localhost')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
        'OPTIONS': {
            'host': os.getenv('EMAIL_HOST', 'localhost'),
            'port': env_int('EMAIL_PORT', 25),
            'username': os.getenv('EMAIL_HOST_USER', ''),
            'password': os.getenv('EMAIL_HOST_PASSWORD', ''),
            'use_tls': env_bool('EMAIL_USE_TLS', False),
            'use_ssl': env_bool('EMAIL_USE_SSL', False),
        },
    },
}


SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', False)
SECURE_HSTS_SECONDS = env_int('SECURE_HSTS_SECONDS', 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', False)
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', SECURE_SSL_REDIRECT)
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', SECURE_SSL_REDIRECT)

SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'

from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env file (if present) — required for local dev
load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=True)

BASE_DIR = Path(__file__).resolve().parent.parent

# ── SECURITY ─────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY', 'agrifarm-dev-secret-change-in-production')
DEBUG      = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# ── PRODUCTION SECURITY SETTINGS ─────────────────────────────────────────────
if not DEBUG:
    # Prevent clickjacking
    X_FRAME_OPTIONS = 'DENY'

    # Force HTTPS cookies
    SESSION_COOKIE_SECURE   = True
    CSRF_COOKIE_SECURE      = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY    = True

    # HSTS — tell browsers to always use HTTPS (1 year)
    SECURE_HSTS_SECONDS            = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD            = True

    # Prevent browsers from sniffing content type
    SECURE_CONTENT_TYPE_NOSNIFF = True

    # Enable XSS browser filter
    SECURE_BROWSER_XSS_FILTER = True

    # Redirect all HTTP → HTTPS
    # Set to True only if your host does NOT handle SSL at the proxy level.
    # Railway / PythonAnywhere / Heroku handle SSL at their load balancer,
    # so keep this False and let SECURE_PROXY_SSL_HEADER do the job.
    SECURE_SSL_REDIRECT = False

    # Proxy header (needed on Railway / Heroku behind load balancer)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Silence the SSL redirect warning — handled at proxy level
SILENCED_SYSTEM_CHECKS = ['security.W008']

# ── APPS ─────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',       # serve static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'agribazaar.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': ['django.template.context_processors.request']},
}]

WSGI_APPLICATION = 'agribazaar.wsgi.application'

# ── DATABASE ──────────────────────────────────────────────────────────────────
# Default: SQLite (good for development and small deployments)
# Switch to PostgreSQL for production by setting DATABASE_URL env variable
DATABASE_URL = os.environ.get('DATABASE_URL', '')

if DATABASE_URL and DATABASE_URL.startswith('postgres'):
    import urllib.parse as urlparse
    url = urlparse.urlparse(DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql',
            'NAME':     url.path[1:],
            'USER':     url.username,
            'PASSWORD': url.password,
            'HOST':     url.hostname,
            'PORT':     url.port or 5432,
            'CONN_MAX_AGE': 60,   # keep DB connections alive for 60s (performance)
            'OPTIONS': {
                'sslmode': 'require',
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME':   BASE_DIR / 'agribazaar.db',
        }
    }

# ── PASSWORD VALIDATION ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 6}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── LOCALISATION ──────────────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Karachi'
USE_TZ        = True

# ── STATIC & MEDIA ────────────────────────────────────────────────────────────
STATIC_URL   = '/static/'
STATIC_ROOT  = BASE_DIR / 'staticfiles'
MEDIA_URL    = '/media/'
MEDIA_ROOT   = BASE_DIR / 'media'

# WhiteNoise — compress and cache static files in production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── SESSIONS ──────────────────────────────────────────────────────────────────
SESSION_ENGINE     = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_AGE = 86400 * 7   # 7 days

# ── CSRF TRUSTED ORIGINS ──────────────────────────────────────────────────────
# Add your production domain here so Django accepts CSRF from it
_trusted = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if _trusted:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _trusted.split(',')]

# ── CSV DATASET ───────────────────────────────────────────────────────────────
CSV_PATH = BASE_DIR / 'clean_crop_prices.csv'

# ── EMAIL ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = os.environ.get('EMAIL_HOST_USER', 'your-email@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'your-app-password')
DEFAULT_FROM_EMAIL  = f'AgriFarm <{EMAIL_HOST_USER}>'

# For development — print emails to terminal instead:
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── GOOGLE OAUTH ──────────────────────────────────────────────────────────────
GOOGLE_CLIENT_ID     = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI  = os.environ.get('GOOGLE_REDIRECT_URI', 'http://127.0.0.1:8000/auth/google/callback/')

# ── GEMINI AI ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# ── SENDGRID ──────────────────────────────────────────────────────────────────
SENDGRID_API_KEY    = os.environ.get('SENDGRID_API_KEY', '')
SENDGRID_FROM_EMAIL = os.environ.get('SENDGRID_FROM_EMAIL', EMAIL_HOST_USER)
SENDGRID_FROM_NAME  = 'AgriFarm'

# ── LOGGING (production) ──────────────────────────────────────────────────────
if not DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {message}',
                'style': '{',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
        },
        'root': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False,
            },
            'django.request': {
                'handlers': ['console'],
                'level': 'ERROR',
                'propagate': False,
            },
        },
    }

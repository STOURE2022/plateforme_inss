from pathlib import Path
from datetime import timedelta
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-me")

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost").split(",")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_filters",
    "django_celery_beat",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.affiliates",
    "apps.employers",
    "apps.contributions",
    "apps.cards",
    "apps.verification",
    "apps.audit",
    "apps.notifications",
    "apps.core",
    "apps.benefits",
    "apps.claims",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB", default="einss"),
        "USER": config("POSTGRES_USER", default="einss"),
        "PASSWORD": config("POSTGRES_PASSWORD", default="changeme"),
        "HOST": config("POSTGRES_HOST", default="db"),
        "PORT": config("POSTGRES_PORT", default="5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalisation — Portugais par défaut
LANGUAGE_CODE = "pt-br"
LANGUAGES = [
    ("pt-br", "Português (Brasil)"),
    ("fr", "Français"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Africa/Bissau"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = config("STATIC_ROOT", default=str(BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = config("MEDIA_ROOT", default=str(BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/min",
        "user": "100/min",
        "login": "5/min",
        "verify": "30/min",
        "verify_card": "60/minute",
        "verify_card_auth": "300/minute",
    },
}

# JWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# Celery
CELERY_BROKER_URL = config("REDIS_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://redis:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# OpenAPI
SPECTACULAR_SETTINGS = {
    "TITLE": "e-INSS API",
    "DESCRIPTION": """
API REST da plataforma nacional de seguridade social da Guiné-Bissau (INSS).

## Autenticação
Utiliza JWT (Bearer token). Obtenha o token em `/api/v1/auth/login/`.
Para endpoints com MFA, use o fluxo: login → pre_auth_token → `/api/v1/auth/mfa/verify/`.

## Roles
- **CITIZEN** : acesso ao próprio perfil e carta
- **EMPLOYER** : gestão de cotizações
- **AGENT** : gestão completa de afiliados e empregadores
- **PROVIDER** : verificação de cartões
- **ADMIN** : acesso total
    """,
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "CONTACT": {"name": "INSS Guinée-Bissau", "email": "tech@inss.gw"},
    "LICENSE": {"name": "Propriétaire"},
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "auth", "description": "Autenticação e MFA"},
        {"name": "affiliates", "description": "Gestão de afiliados"},
        {"name": "employers", "description": "Gestão de empregadores"},
        {"name": "contributions", "description": "Cotizações"},
        {"name": "cards", "description": "Cartão de seguro de saúde"},
        {"name": "verify", "description": "Verificação de cartões"},
        {"name": "audit", "description": "Auditoria (admin)"},
        {"name": "notifications", "description": "Notificações"},
    ],
}

# Sécurité
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# Portail HTML — URL de login pour LoginRequiredMixin
LOGIN_URL = "/auth/login/"

# Clés RSA pour tokens QR
INSS_PRIVATE_KEY_PATH = config("INSS_PRIVATE_KEY_PATH", default=str(BASE_DIR / "keys" / "inss_private.pem"))
INSS_PUBLIC_KEY_PATH = config("INSS_PUBLIC_KEY_PATH", default=str(BASE_DIR / "keys" / "inss_public.pem"))

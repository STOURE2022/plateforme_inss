from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Servir les fichiers statiques en dev (admin Django, etc.)
STATICFILES_DIRS = []
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# No throttling in dev
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # type: ignore[index]  # noqa: F405

# Simplified passwords for dev
AUTH_PASSWORD_VALIDATORS = []  # type: ignore[assignment]

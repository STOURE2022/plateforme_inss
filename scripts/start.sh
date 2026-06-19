#!/bin/bash
set -e

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Creating superuser if needed..."
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput \
    --email "$DJANGO_SUPERUSER_EMAIL" 2>/dev/null || echo "Superuser already exists."
fi

echo "==> Starting Gunicorn..."
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -

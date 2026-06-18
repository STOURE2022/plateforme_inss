import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("einss")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Beat schedule
app.conf.beat_schedule = {
    # Roda os tokens QR a cada 4 minutos (token válido 5 min)
    # Nota: rotate_card_tokens recebe card_id — o scheduler geral não é aplicável aqui
    # A tarefa expire_cards sim é periódica global
    "expire-cards-daily": {
        "task": "cards.expire_cards",
        "schedule": crontab(hour=0, minute=0),
    },
    # Lot 5 — Notifications
    "check-expiring-cards-daily": {
        "task": "notifications.check_expiring_cards",
        "schedule": crontab(hour=8, minute=0),
    },
    "check-late-contributions-monthly": {
        "task": "notifications.check_late_contributions",
        "schedule": crontab(hour=9, minute=0, day_of_month=1),
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):  # type: ignore[no-untyped-def]
    print(f"Request: {self.request!r}")

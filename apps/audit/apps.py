from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Auditoria"

    def ready(self):
        from apps.audit.signals import _connect_signals
        _connect_signals()

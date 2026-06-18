from django.db import models
from django.conf import settings


class AuditEvent(models.Model):
    # Quem
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        verbose_name="Utilizador",
    )
    user_email = models.CharField(max_length=254, blank=True, verbose_name="Email (snapshot)")
    user_role = models.CharField(max_length=20, blank=True, verbose_name="Função (snapshot)")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Endereço IP")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")

    # O quê
    action = models.CharField(max_length=100, verbose_name="Ação")
    resource_type = models.CharField(max_length=50, blank=True, verbose_name="Tipo de recurso")
    resource_id = models.CharField(max_length=50, blank=True, verbose_name="ID do recurso")
    resource_repr = models.CharField(max_length=200, blank=True, verbose_name="Representação do recurso")

    # Detalhes
    details = models.JSONField(default=dict, blank=True, verbose_name="Detalhes")
    old_values = models.JSONField(null=True, blank=True, verbose_name="Valores anteriores")
    new_values = models.JSONField(null=True, blank=True, verbose_name="Novos valores")

    # Contexto
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Timestamp")

    class Meta:
        verbose_name = "Evento de Auditoria"
        verbose_name_plural = "Eventos de Auditoria"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["action", "timestamp"]),
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["user", "timestamp"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} by {self.user_email} at {self.timestamp}"

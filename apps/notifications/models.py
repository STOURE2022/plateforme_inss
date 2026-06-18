from django.db import models
from django.conf import settings


class NotificationType(models.TextChoices):
    INFO = "INFO", "Informação"
    WARNING = "WARNING", "Aviso"
    SUCCESS = "SUCCESS", "Sucesso"
    ERROR = "ERROR", "Erro"


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Destinatário",
    )
    title = models.CharField(max_length=200, verbose_name="Título")
    message = models.TextField(verbose_name="Mensagem")
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO,
        verbose_name="Tipo",
    )

    # Lien optionnel vers une ressource
    resource_type = models.CharField(max_length=50, blank=True, verbose_name="Tipo de recurso")
    resource_id = models.CharField(max_length=50, blank=True, verbose_name="ID do recurso")
    resource_url = models.CharField(max_length=200, blank=True, verbose_name="URL do recurso")

    is_read = models.BooleanField(default=False, verbose_name="Lida")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Lida em")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criada em")

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.notification_type}] {self.title} → {self.recipient}"

from django.db import models
from django.conf import settings


class VerificationResult(models.TextChoices):
    SUCCESS = "SUCCESS", "Sucesso"
    FAILURE = "FAILURE", "Falha"
    EXPIRED = "EXPIRED", "Expirado"
    REVOKED = "REVOKED", "Revogado"
    INVALID = "INVALID", "Inválido"


class VerificationLog(models.Model):
    # Quem verificou
    verifier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verifications",
        verbose_name="Verificador",
    )
    verifier_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP do verificador",
    )
    verifier_role = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Função no momento da verificação",
    )

    # O que foi verificado
    card = models.ForeignKey(
        "cards.HealthCard",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verification_logs",
        verbose_name="Cartão",
    )
    card_number = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Número do cartão (snapshot)",
    )
    token_jti = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="JTI do token apresentado",
    )

    # Resultado
    result = models.CharField(
        max_length=20,
        choices=VerificationResult.choices,
        verbose_name="Resultado",
    )
    failure_reason = models.TextField(
        blank=True,
        verbose_name="Motivo da falha",
    )

    # Contexto
    verified_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Verificado em",
    )
    response_ms = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Tempo de resposta (ms)",
    )

    class Meta:
        verbose_name = "Log de Verificação"
        verbose_name_plural = "Logs de Verificação"
        ordering = ["-verified_at"]
        indexes = [
            models.Index(fields=["card_number", "verified_at"]),
            models.Index(fields=["verifier", "verified_at"]),
            models.Index(fields=["result", "verified_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.card_number} — {self.result} — {self.verified_at}"

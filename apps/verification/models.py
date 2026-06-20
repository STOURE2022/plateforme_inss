import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


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


class ActType(models.TextChoices):
    CONSULTATION = "CONSULTATION", "Consulta"
    EXAM = "EXAM", "Exame / Diagnóstico"
    HOSPITALIZATION = "HOSPITALIZATION", "Hospitalização"
    MEDICATION = "MEDICATION", "Medicamentos"
    SURGERY = "SURGERY", "Cirurgia"
    OTHER = "OTHER", "Outro"


class ActStatus(models.TextChoices):
    PENDING = "PENDING", "Pendente"
    VALIDATED = "VALIDATED", "Validado"
    REJECTED = "REJECTED", "Rejeitado"


class ProviderMedicalAct(models.Model):
    reference = models.CharField(max_length=30, unique=True, blank=True, verbose_name="Referência")
    card = models.ForeignKey(
        "cards.HealthCard", on_delete=models.PROTECT,
        related_name="medical_acts", verbose_name="Cartão"
    )
    affiliate_name = models.CharField(max_length=200, verbose_name="Nome do titular")
    affiliate_niss = models.CharField(max_length=15, verbose_name="NISS")
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="registered_acts", verbose_name="Prestador"
    )
    act_type = models.CharField(max_length=20, choices=ActType.choices, verbose_name="Tipo de acto")
    act_date = models.DateField(verbose_name="Data do acto")
    estimated_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True, verbose_name="Montante estimado (XOF)"
    )
    validated_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True, verbose_name="Montante validado (XOF)"
    )
    observations = models.TextField(blank=True, verbose_name="Observações")
    status = models.CharField(
        max_length=20, choices=ActStatus.choices,
        default=ActStatus.PENDING, verbose_name="Estado"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reviewed_medical_acts",
        verbose_name="Revisto por"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Revisto em")
    review_notes = models.TextField(blank=True, verbose_name="Notas de revisão")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Acto Médico"
        verbose_name_plural = "Actos Médicos"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["provider", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            year = self.act_date.year if self.act_date else timezone.now().year
            self.reference = f"ACT-{year}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} — {self.affiliate_name} — {self.get_act_type_display()}"


class ProviderProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="provider_profile", verbose_name="Utilizador"
    )
    clinic_name = models.CharField(max_length=200, blank=True, verbose_name="Nome da clínica / estabelecimento")
    specialty = models.CharField(max_length=100, blank=True, verbose_name="Especialidade")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
    address = models.CharField(max_length=300, blank=True, verbose_name="Endereço")
    license_number = models.CharField(max_length=50, blank=True, verbose_name="Nº de licença")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil do Prestador"
        verbose_name_plural = "Perfis dos Prestadores"

    def __str__(self):
        return f"{self.clinic_name or self.user.email}"

    def get_display_name(self):
        return self.clinic_name or self.user.email

from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class CardStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Ativo"
    SUSPENDED = "SUSPENDED", "Suspenso"
    EXPIRED = "EXPIRED", "Expirado"
    CANCELLED = "CANCELLED", "Cancelado"


class HealthCard(models.Model):
    affiliate = models.OneToOneField(
        "affiliates.Affiliate",
        on_delete=models.PROTECT,
        related_name="health_card",
        verbose_name="Afiliado",
    )
    card_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        verbose_name="Número do cartão",
    )
    issued_date = models.DateField(auto_now_add=True, verbose_name="Data de emissão")
    expiry_date = models.DateField(null=True, blank=True, verbose_name="Data de validade")
    status = models.CharField(
        max_length=10,
        choices=CardStatus.choices,
        default=CardStatus.ACTIVE,
        verbose_name="Estado",
    )

    # QR Token JWS
    current_token_jti = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="JTI do token atual",
    )
    token_issued_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Emissão do token",
    )
    token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Expiração do token",
    )

    # PDF
    pdf_file = models.FileField(
        upload_to="cards/pdf/",
        null=True,
        blank=True,
        verbose_name="Ficheiro PDF",
    )
    pdf_generated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="PDF gerado em",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_cards",
        verbose_name="Criado por",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Cartão de Saúde"
        verbose_name_plural = "Cartões de Saúde"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.card_number} — {self.affiliate.full_name}"

    def generate_card_number(self) -> str:
        """Gera o número do cartão no formato INSS-{niss}-{year}."""
        year = timezone.now().year
        niss = self.affiliate.niss
        return f"INSS-{niss}-{year}"

    def is_valid(self) -> bool:
        """Retorna True se o cartão está ATIVO e não expirado."""
        if self.status != CardStatus.ACTIVE:
            return False
        today = timezone.now().date()
        return self.expiry_date is not None and self.expiry_date >= today

    def save(self, *args, **kwargs):
        # Gera card_number se vazio
        if not self.card_number:
            self.card_number = self.generate_card_number()

        # Calcula expiry_date se vazio (issued_date + 365 dias)
        # issued_date é auto_now_add — ao criar, ainda pode ser None antes do primeiro save
        if not self.expiry_date:
            base_date = self.issued_date if self.issued_date else timezone.now().date()
            self.expiry_date = base_date + timedelta(days=365)

        super().save(*args, **kwargs)

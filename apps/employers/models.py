from django.db import models
from django.conf import settings


class EmployerStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Ativo"
    INACTIVE = "INACTIVE", "Inativo"
    SUSPENDED = "SUSPENDED", "Suspenso"


class SectorChoices(models.TextChoices):
    PUBLIC = "PUBLIC", "Público"
    PRIVATE = "PRIVATE", "Privado"
    NGO = "NGO", "ONG"
    OTHER = "OTHER", "Outro"


class Employer(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="employer",
        verbose_name="Utilizador",
    )
    company_name = models.CharField(max_length=200, verbose_name="Nome da empresa")
    nuit = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="NUIT",
        help_text="Número de Identificação Fiscal",
    )
    sector = models.CharField(
        max_length=10,
        choices=SectorChoices.choices,
        verbose_name="Sector",
    )
    address = models.TextField(verbose_name="Endereço")
    phone = models.CharField(max_length=20, verbose_name="Telefone")
    email = models.EmailField(blank=True, verbose_name="Email")
    registration_date = models.DateField(auto_now_add=True, verbose_name="Data de registo")
    status = models.CharField(
        max_length=10,
        choices=EmployerStatus.choices,
        default=EmployerStatus.ACTIVE,
        verbose_name="Estado",
    )
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registered_employers",
        verbose_name="Registado por",
    )

    class Meta:
        verbose_name = "Empregador"
        verbose_name_plural = "Empregadores"
        ordering = ["-registration_date"]

    def __str__(self) -> str:
        return f"{self.company_name} ({self.nuit})"

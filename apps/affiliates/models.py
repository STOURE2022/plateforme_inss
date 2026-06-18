from django.db import models
from django.conf import settings


class AffiliateStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Ativo"
    INACTIVE = "INACTIVE", "Inativo"
    SUSPENDED = "SUSPENDED", "Suspenso"


class GenderChoices(models.TextChoices):
    MALE = "M", "Masculino"
    FEMALE = "F", "Feminino"
    OTHER = "O", "Outro"


class RelationshipChoices(models.TextChoices):
    SPOUSE = "SPOUSE", "Cônjuge"
    CHILD = "CHILD", "Filho/Filha"
    PARENT = "PARENT", "Pai/Mãe"
    OTHER = "OTHER", "Outro"


class Affiliate(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="affiliate",
        verbose_name="Utilizador",
    )
    niss = models.CharField(
        max_length=15,
        unique=True,
        verbose_name="NISS",
        help_text="Número de Identificação de Segurança Social",
    )
    full_name = models.CharField(max_length=200, verbose_name="Nome completo")
    birth_date = models.DateField(verbose_name="Data de nascimento")
    gender = models.CharField(
        max_length=1,
        choices=GenderChoices.choices,
        verbose_name="Género",
    )
    nationality = models.CharField(
        max_length=3,
        default="GW",
        verbose_name="Nacionalidade",
    )
    address = models.TextField(blank=True, verbose_name="Endereço")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
    registration_date = models.DateField(auto_now_add=True, verbose_name="Data de registo")
    status = models.CharField(
        max_length=10,
        choices=AffiliateStatus.choices,
        default=AffiliateStatus.ACTIVE,
        verbose_name="Estado",
    )

    class Meta:
        verbose_name = "Afiliado"
        verbose_name_plural = "Afiliados"
        ordering = ["-registration_date"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.niss})"


class Dependent(models.Model):
    affiliate = models.ForeignKey(
        Affiliate,
        on_delete=models.CASCADE,
        related_name="dependents",
        verbose_name="Afiliado",
    )
    full_name = models.CharField(max_length=200, verbose_name="Nome completo")
    birth_date = models.DateField(verbose_name="Data de nascimento")
    relationship = models.CharField(
        max_length=10,
        choices=RelationshipChoices.choices,
        verbose_name="Grau de parentesco",
    )
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Dependente"
        verbose_name_plural = "Dependentes"
        ordering = ["full_name"]

    def __str__(self) -> str:
        return f"{self.full_name} — {self.get_relationship_display()} de {self.affiliate.full_name}"

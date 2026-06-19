from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class ContributionStatus(models.TextChoices):
    PENDING = "PENDING", "Pendente"
    PAID = "PAID", "Pago"
    LATE = "LATE", "Em atraso"
    CANCELLED = "CANCELLED", "Cancelado"


class Contribution(models.Model):
    affiliate = models.ForeignKey(
        "affiliates.Affiliate",
        on_delete=models.PROTECT,
        related_name="contributions",
        verbose_name="Afiliado",
    )
    employer = models.ForeignKey(
        "employers.Employer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contributions",
        verbose_name="Empregador",
    )
    period_year = models.PositiveIntegerField(verbose_name="Ano do período")
    period_month = models.PositiveIntegerField(
        verbose_name="Mês do período",
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    salary_base = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Salário base",
    )
    employee_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default="0.0400",
        verbose_name="Taxa do trabalhador",
    )
    employer_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default="0.0800",
        verbose_name="Taxa do empregador",
    )
    employee_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Contribuição do trabalhador",
    )
    employer_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Contribuição do empregador",
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Total",
    )
    payment_date = models.DateField(null=True, blank=True, verbose_name="Data de pagamento")
    status = models.CharField(
        max_length=10,
        choices=ContributionStatus.choices,
        default=ContributionStatus.PENDING,
        verbose_name="Estado",
    )
    reference = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        verbose_name="Referência",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_contributions",
        verbose_name="Criado por",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    notes = models.TextField(blank=True, verbose_name="Notas")

    class Meta:
        verbose_name = "Contribuição"
        verbose_name_plural = "Contribuições"
        ordering = ["-period_year", "-period_month"]
        unique_together = [("affiliate", "period_year", "period_month")]

    def __str__(self) -> str:
        return f"{self.reference} — {self.affiliate.full_name} {self.period_year}/{self.period_month:02d}"

    def _generate_reference(self) -> str:
        return f"COTT-{self.period_year}{self.period_month:02d}-{self.affiliate.niss}"

    def save(self, *args, **kwargs) -> None:
        # Recalcular montantes
        self.employee_amount = self.salary_base * self.employee_rate
        self.employer_amount = self.salary_base * self.employer_rate
        self.total_amount = self.employee_amount + self.employer_amount

        # Gerar referência se vazia
        if not self.reference:
            self.reference = self._generate_reference()

        super().save(*args, **kwargs)


class CareerStatementLog(models.Model):
    """Tracks each time a career statement PDF is generated."""

    affiliate = models.ForeignKey(
        "affiliates.Affiliate",
        on_delete=models.PROTECT,
        related_name="career_statement_logs",
        verbose_name="Afiliado",
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="career_statements_generated",
        verbose_name="Gerado por",
    )
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name="Gerado em")
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name="Endereço IP"
    )
    purpose = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Finalidade",
        help_text="e.g., demande de pension, contrôle interne",
    )

    class Meta:
        ordering = ["-generated_at"]
        verbose_name = "Relevé de Carrière"
        verbose_name_plural = "Relevés de Carrière"

    def __str__(self) -> str:
        return f"Relevé {self.affiliate.niss} — {self.generated_at.strftime('%d/%m/%Y %H:%M')}"

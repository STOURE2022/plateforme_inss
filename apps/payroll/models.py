from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum


class DeclarationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Rascunho"
    SUBMITTED = "SUBMITTED", "Submetida"
    VALIDATED = "VALIDATED", "Validada"
    REJECTED = "REJECTED", "Rejeitada"


class PayrollDeclaration(models.Model):
    reference = models.CharField(
        max_length=40,
        unique=True,
        blank=True,
        verbose_name="Referência",
    )
    employer = models.ForeignKey(
        "employers.Employer",
        on_delete=models.PROTECT,
        related_name="payroll_declarations",
        verbose_name="Empregador",
    )
    period_year = models.PositiveIntegerField(verbose_name="Ano do período")
    period_month = models.PositiveIntegerField(
        verbose_name="Mês do período",
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    status = models.CharField(
        max_length=10,
        choices=DeclarationStatus.choices,
        default=DeclarationStatus.DRAFT,
        verbose_name="Estado",
    )

    # Totals (auto-computed from lines)
    total_employees = models.PositiveIntegerField(default=0, verbose_name="Nº trabalhadores")
    total_salary_base = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name="Total salários"
    )
    total_employee_contributions = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name="Total cotizações trabalhador"
    )
    total_employer_contributions = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name="Total cotizações empregador"
    )
    total_contributions = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name="Total geral"
    )

    # Submission
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="Submetida em")

    # Validation
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="validated_declarations",
        verbose_name="Validada por",
    )
    validated_at = models.DateTimeField(null=True, blank=True, verbose_name="Validada em")
    validation_notes = models.TextField(blank=True, verbose_name="Notas de validação")

    # Rejection
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rejected_declarations",
        verbose_name="Rejeitada por",
    )
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name="Rejeitada em")
    rejection_reason = models.TextField(blank=True, verbose_name="Motivo de rejeição")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_declarations",
        verbose_name="Criada por",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criada em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizada em")

    class Meta:
        verbose_name = "Declaração de Massa Salarial"
        verbose_name_plural = "Declarações de Massa Salarial"
        unique_together = [("employer", "period_year", "period_month")]
        ordering = ["-period_year", "-period_month"]

    def __str__(self) -> str:
        return f"{self.reference} — {self.get_status_display()}"

    def _generate_reference(self) -> str:
        return f"DECL-{self.period_year}{self.period_month:02d}-{self.employer.nuit}"

    def save(self, *args, **kwargs) -> None:
        if not self.reference:
            self.reference = self._generate_reference()
        super().save(*args, **kwargs)

    def recompute_totals(self) -> None:
        """Recompute aggregated totals from lines. Call after adding/removing lines."""
        lines = self.lines.all()
        agg = lines.aggregate(
            s_salary=Sum("salary_base"),
            s_employee=Sum("employee_amount"),
            s_employer=Sum("employer_amount"),
            s_total=Sum("total_amount"),
        )
        self.total_employees = lines.count()
        self.total_salary_base = agg["s_salary"] or Decimal("0")
        self.total_employee_contributions = agg["s_employee"] or Decimal("0")
        self.total_employer_contributions = agg["s_employer"] or Decimal("0")
        self.total_contributions = agg["s_total"] or Decimal("0")
        self.save(
            update_fields=[
                "total_employees",
                "total_salary_base",
                "total_employee_contributions",
                "total_employer_contributions",
                "total_contributions",
                "updated_at",
            ]
        )

    def generate_contributions(self, agent_user) -> int:
        """Called on VALIDATED. Creates one Contribution per line if not already existing."""
        from apps.contributions.models import Contribution

        created = 0
        for line in self.lines.all():
            obj, was_created = Contribution.objects.get_or_create(
                affiliate=line.affiliate,
                period_year=self.period_year,
                period_month=self.period_month,
                defaults={
                    "employer": self.employer,
                    "salary_base": line.salary_base,
                    "employee_rate": line.employee_rate,
                    "employer_rate": line.employer_rate,
                    "status": "PENDING",
                    "created_by": agent_user,
                    "notes": f"Gerado automaticamente via declaração {self.reference}",
                },
            )
            if was_created:
                line.contribution = obj
                line.save(update_fields=["contribution"])
                created += 1
        return created

    def get_period_display(self) -> str:
        from calendar import month_name
        months_pt = [
            "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
        ]
        return f"{months_pt[self.period_month]} {self.period_year}"


class PayrollDeclarationLine(models.Model):
    declaration = models.ForeignKey(
        PayrollDeclaration,
        on_delete=models.CASCADE,
        related_name="lines",
        verbose_name="Declaração",
    )
    affiliate = models.ForeignKey(
        "affiliates.Affiliate",
        on_delete=models.PROTECT,
        related_name="declaration_lines",
        verbose_name="Afiliado",
    )

    salary_base = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Salário base"
    )
    employee_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.0400"),
        verbose_name="Taxa trabalhador",
    )
    employer_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.0800"),
        verbose_name="Taxa empregador",
    )

    # Auto-calculated
    employee_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Cota trabalhador"
    )
    employer_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Cota empregador"
    )
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Total"
    )

    # Link to created Contribution (set after validation)
    contribution = models.OneToOneField(
        "contributions.Contribution",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="declaration_line",
        verbose_name="Contribuição gerada",
    )

    notes = models.CharField(max_length=200, blank=True, verbose_name="Notas")

    class Meta:
        verbose_name = "Linha de Declaração"
        verbose_name_plural = "Linhas de Declaração"
        unique_together = [("declaration", "affiliate")]
        ordering = ["affiliate__full_name"]

    def __str__(self) -> str:
        return f"{self.declaration.reference} — {self.affiliate.full_name}"

    def save(self, *args, **kwargs) -> None:
        self.employee_amount = self.salary_base * self.employee_rate
        self.employer_amount = self.salary_base * self.employer_rate
        self.total_amount = self.employee_amount + self.employer_amount
        super().save(*args, **kwargs)

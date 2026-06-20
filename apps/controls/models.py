from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum


class ControlType(models.TextChoices):
    ROUTINE = "ROUTINE", "Contrôle de Routine"
    TARGETED = "TARGETED", "Contrôle Ciblé"
    COMPLAINT = "COMPLAINT", "Déclenché par Réclamation"
    CROSS_CHECK = "CROSS_CHECK", "Recoupement Fiscal"


class ControlStatus(models.TextChoices):
    PLANNED = "PLANNED", "Planificado"
    IN_PROGRESS = "IN_PROGRESS", "Em Curso"
    PV_DRAFTED = "PV_DRAFTED", "PV Redigido"
    NOTIFIED = "NOTIFIED", "Notificado"
    DISPUTED = "DISPUTED", "Contestado"
    SETTLED = "SETTLED", "Regularizado"
    CLOSED = "CLOSED", "Encerrado"


VALID_TRANSITIONS = {
    ControlStatus.PLANNED: [ControlStatus.IN_PROGRESS],
    ControlStatus.IN_PROGRESS: [ControlStatus.PV_DRAFTED, ControlStatus.CLOSED],
    ControlStatus.PV_DRAFTED: [ControlStatus.NOTIFIED],
    ControlStatus.NOTIFIED: [ControlStatus.SETTLED, ControlStatus.DISPUTED],
    ControlStatus.DISPUTED: [ControlStatus.SETTLED, ControlStatus.CLOSED],
    ControlStatus.SETTLED: [ControlStatus.CLOSED],
    ControlStatus.CLOSED: [],
}


class EmployerControl(models.Model):
    reference = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        verbose_name="Referência",
    )

    employer = models.ForeignKey(
        "employers.Employer",
        on_delete=models.PROTECT,
        related_name="controls",
        verbose_name="Empregador",
    )
    control_type = models.CharField(
        max_length=20,
        choices=ControlType.choices,
        default=ControlType.ROUTINE,
        verbose_name="Tipo de Controlo",
    )
    status = models.CharField(
        max_length=20,
        choices=ControlStatus.choices,
        default=ControlStatus.PLANNED,
        verbose_name="Estado",
    )

    # Period under review
    period_from = models.DateField(verbose_name="Período de (início)")
    period_to = models.DateField(verbose_name="Período até (fim)")

    # Assignment
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_controls",
        verbose_name="Agente Responsável",
    )

    # Optional link to a claim that triggered this control
    triggered_by_claim = models.ForeignKey(
        "claims.Claim",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="triggered_controls",
        verbose_name="Reclamação que gerou este controlo",
    )

    # Findings
    findings_summary = models.TextField(
        blank=True,
        verbose_name="Síntese das constatações",
    )

    # PV (Procès-Verbal)
    pv_reference = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Referência do PV",
    )
    pv_date = models.DateField(null=True, blank=True, verbose_name="Data do PV")
    pv_notes = models.TextField(blank=True, verbose_name="Notas do PV")

    # Notification to employer
    notified_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Notificado em"
    )
    notification_deadline = models.DateField(
        null=True,
        blank=True,
        verbose_name="Prazo de resposta do empregador",
    )

    # Financial summary (auto-computed from assessments)
    total_assessed = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Total Avaliado",
    )
    total_penalties = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Total Penalidades",
    )
    total_due = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Total a Pagar",
    )
    total_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Total Pago",
    )
    total_remaining = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Montante Restante",
    )

    # Dispute
    dispute_reason = models.TextField(blank=True, verbose_name="Motivo da contestação")
    dispute_filed_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Contestação apresentada em"
    )

    # Closure
    closed_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Encerrado em"
    )
    closure_notes = models.TextField(blank=True, verbose_name="Notas de encerramento")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_controls",
        verbose_name="Criado por",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Controlo de Empregador"
        verbose_name_plural = "Controlos de Empregadores"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.reference} — {self.employer.company_name} ({self.get_status_display()})"

    def _generate_reference(self) -> str:
        year = date.today().year
        last = EmployerControl.objects.filter(
            reference__startswith=f"CTRL-{year}-"
        ).count()
        return f"CTRL-{year}-{last + 1:05d}"

    def save(self, *args, **kwargs) -> None:
        if not self.reference:
            self.reference = self._generate_reference()
        if not self.pv_reference and self.reference:
            self.pv_reference = f"PV-{self.reference}"
        super().save(*args, **kwargs)

    def can_transition_to(self, new_status: str) -> bool:
        """Returns True if the status transition is valid."""
        allowed = VALID_TRANSITIONS.get(self.status, [])
        return new_status in allowed

    def recompute_totals(self) -> None:
        """Recompute financial totals from assessments and confirmed payments."""
        assessments = self.assessments.all()
        agg_a = assessments.aggregate(
            s_assessed=Sum("assessed_amount"),
            s_penalties=Sum("penalty_amount"),
        )
        self.total_assessed = agg_a["s_assessed"] or Decimal("0")
        self.total_penalties = agg_a["s_penalties"] or Decimal("0")
        self.total_due = self.total_assessed + self.total_penalties

        confirmed_payments = self.payments.filter(status=ControlPayment.PaymentStatus.CONFIRMED)
        agg_p = confirmed_payments.aggregate(s=Sum("amount"))
        self.total_paid = agg_p["s"] or Decimal("0")
        self.total_remaining = max(self.total_due - self.total_paid, Decimal("0"))

        self.save(
            update_fields=[
                "total_assessed",
                "total_penalties",
                "total_due",
                "total_paid",
                "total_remaining",
                "updated_at",
            ]
        )

    @property
    def is_deadline_overdue(self) -> bool:
        if self.notification_deadline and self.status == ControlStatus.NOTIFIED:
            return date.today() > self.notification_deadline
        return False

    @property
    def days_open(self) -> int:
        end = self.closed_at.date() if self.closed_at else date.today()
        return (end - self.created_at.date()).days


class ControlAssessment(models.Model):
    """One redressement line per period/month with a discrepancy."""

    control = models.ForeignKey(
        EmployerControl,
        on_delete=models.CASCADE,
        related_name="assessments",
        verbose_name="Controlo",
    )

    period_year = models.PositiveIntegerField(verbose_name="Ano")
    period_month = models.PositiveIntegerField(
        verbose_name="Mês",
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )

    # Declared vs actual
    declared_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Salário Declarado",
    )
    actual_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Salário Real",
    )
    salary_difference = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Diferença Salarial",
    )  # auto

    # Amounts
    assessed_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Montante Avaliado (12%)",
    )
    penalty_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0.1000"),
        verbose_name="Taxa de penalidade",
    )
    penalty_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Penalidade",
    )  # auto
    total_line = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Total Linha",
    )  # auto

    notes = models.TextField(blank=True, verbose_name="Notas")

    class Meta:
        verbose_name = "Linha de Redressamento"
        verbose_name_plural = "Linhas de Redressamento"
        unique_together = [("control", "period_year", "period_month")]
        ordering = ["period_year", "period_month"]

    def __str__(self) -> str:
        return f"{self.control.reference} — {self.period_month:02d}/{self.period_year}"

    def save(self, *args, **kwargs) -> None:
        self.salary_difference = self.actual_salary - self.declared_salary
        self.assessed_amount = self.salary_difference * Decimal("0.12")
        self.penalty_amount = self.assessed_amount * self.penalty_rate
        self.total_line = self.assessed_amount + self.penalty_amount
        super().save(*args, **kwargs)


class ControlDocument(models.Model):
    class DocType(models.TextChoices):
        PV = "PV", "Procès-Verbal"
        EMPLOYER_RESPONSE = "EMPLOYER_RESPONSE", "Resposta do Empregador"
        PROOF_PAYMENT = "PROOF_PAYMENT", "Comprovativo de Pagamento"
        SUPPORTING = "SUPPORTING", "Documento de Suporte"
        OTHER = "OTHER", "Outro"

    control = models.ForeignKey(
        EmployerControl,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="Controlo",
    )
    doc_type = models.CharField(
        max_length=25,
        choices=DocType.choices,
        verbose_name="Tipo de documento",
    )
    name = models.CharField(max_length=200, verbose_name="Nome")
    file = models.FileField(
        upload_to="controls/documents/%Y/%m/",
        verbose_name="Ficheiro",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="Carregado por",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Carregado em")
    notes = models.CharField(max_length=300, blank=True, verbose_name="Notas")

    class Meta:
        verbose_name = "Documento de Controlo"
        verbose_name_plural = "Documentos de Controlo"
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"{self.name} — {self.control.reference}"


class ControlStatusHistory(models.Model):
    """Immutable status change log."""

    control = models.ForeignKey(
        EmployerControl,
        on_delete=models.CASCADE,
        related_name="history",
        verbose_name="Controlo",
    )
    old_status = models.CharField(
        max_length=20, blank=True, verbose_name="Estado anterior"
    )
    new_status = models.CharField(max_length=20, verbose_name="Novo estado")
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="Alterado por",
    )
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="Alterado em")
    comment = models.TextField(blank=True, verbose_name="Comentário")

    class Meta:
        verbose_name = "Histórico de Estado de Controlo"
        verbose_name_plural = "Histórico de Estados de Controlo"
        ordering = ["changed_at"]

    def __str__(self) -> str:
        return f"{self.control.reference}: {self.old_status} → {self.new_status}"


class ControlPayment(models.Model):
    """Payment received towards assessed amount."""

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        CONFIRMED = "CONFIRMED", "Confirmado"
        REJECTED = "REJECTED", "Rejeitado"

    control = models.ForeignKey(
        EmployerControl,
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="Controlo",
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Montante"
    )
    payment_date = models.DateField(verbose_name="Data de pagamento")
    payment_reference = models.CharField(
        max_length=100, blank=True, verbose_name="Referência de pagamento"
    )
    status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name="Estado",
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="Registado por",
    )
    recorded_at = models.DateTimeField(auto_now_add=True, verbose_name="Registado em")
    notes = models.TextField(blank=True, verbose_name="Notas")

    class Meta:
        verbose_name = "Pagamento de Redressamento"
        verbose_name_plural = "Pagamentos de Redressamento"
        ordering = ["-payment_date"]

    def __str__(self) -> str:
        return f"{self.control.reference} — {self.amount} ({self.get_status_display()})"

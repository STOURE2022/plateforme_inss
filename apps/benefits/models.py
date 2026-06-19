from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg, Count


class BenefitCategory(models.TextChoices):
    RETIREMENT = "RETIREMENT", "Pensão de Reforma"
    DISABILITY = "DISABILITY", "Pensão de Invalidez"
    SURVIVOR = "SURVIVOR", "Pensão de Sobrevivência"
    FAMILY = "FAMILY", "Abono de Família"
    SICKNESS = "SICKNESS", "Subsídio de Doença"
    WORK_ACCIDENT = "WORK_ACCIDENT", "Acidente de Trabalho"
    DEATH = "DEATH", "Subsídio de Morte"


class CalculationMethod(models.TextChoices):
    FIXED = "FIXED", "Montante fixo"
    PERCENTAGE = "PERCENTAGE", "Percentagem do salário"
    FORMULA = "FORMULA", "Fórmula personalizada"


class BenefitType(models.Model):
    category = models.CharField(
        max_length=20,
        choices=BenefitCategory.choices,
        verbose_name="Categoria",
    )
    name = models.CharField(max_length=200, verbose_name="Nome")
    description = models.TextField(blank=True, verbose_name="Descrição")
    min_contribution_months = models.PositiveIntegerField(
        default=0,
        verbose_name="Meses mínimos de contribuição",
    )
    calculation_method = models.CharField(
        max_length=20,
        choices=CalculationMethod.choices,
        default=CalculationMethod.FIXED,
        verbose_name="Método de cálculo",
    )
    fixed_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Montante fixo (XOF)",
    )
    percentage_of_salary = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Percentagem do salário (%)",
    )
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Tipo de Prestação"
        verbose_name_plural = "Tipos de Prestações"
        ordering = ["category", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_category_display()})"


class BenefitRequestStatus(models.TextChoices):
    DRAFT = "DRAFT", "Rascunho"
    SUBMITTED = "SUBMITTED", "Submetida"
    UNDER_REVIEW = "UNDER_REVIEW", "Em revisão"
    ADDITIONAL_DOCS = "ADDITIONAL_DOCS", "Documentos adicionais"
    APPROVED = "APPROVED", "Aprovada"
    REJECTED = "REJECTED", "Rejeitada"
    PAYING = "PAYING", "Em pagamento"
    CLOSED = "CLOSED", "Encerrada"


# Valid transitions: from_status -> [allowed to_statuses]
VALID_TRANSITIONS = {
    BenefitRequestStatus.DRAFT: [BenefitRequestStatus.SUBMITTED],
    BenefitRequestStatus.SUBMITTED: [BenefitRequestStatus.UNDER_REVIEW, BenefitRequestStatus.REJECTED],
    BenefitRequestStatus.UNDER_REVIEW: [
        BenefitRequestStatus.APPROVED,
        BenefitRequestStatus.REJECTED,
        BenefitRequestStatus.ADDITIONAL_DOCS,
    ],
    BenefitRequestStatus.ADDITIONAL_DOCS: [BenefitRequestStatus.UNDER_REVIEW, BenefitRequestStatus.REJECTED],
    BenefitRequestStatus.APPROVED: [BenefitRequestStatus.PAYING, BenefitRequestStatus.CLOSED],
    BenefitRequestStatus.PAYING: [BenefitRequestStatus.CLOSED],
    BenefitRequestStatus.REJECTED: [],
    BenefitRequestStatus.CLOSED: [],
}


class BenefitRequest(models.Model):
    reference = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        verbose_name="Referência",
    )
    affiliate = models.ForeignKey(
        "affiliates.Affiliate",
        on_delete=models.PROTECT,
        related_name="benefit_requests",
        verbose_name="Afiliado",
    )
    benefit_type = models.ForeignKey(
        BenefitType,
        on_delete=models.PROTECT,
        related_name="requests",
        verbose_name="Tipo de prestação",
    )

    # Snapshot of applicant at submission time
    applicant_name = models.CharField(max_length=200, verbose_name="Nome do requerente")
    applicant_niss = models.CharField(max_length=15, verbose_name="NISS do requerente")
    applicant_birth_date = models.DateField(verbose_name="Data de nascimento do requerente")

    # Request details
    status = models.CharField(
        max_length=20,
        choices=BenefitRequestStatus.choices,
        default=BenefitRequestStatus.DRAFT,
        verbose_name="Estado",
    )
    justification = models.TextField(verbose_name="Justificação")
    requested_start_date = models.DateField(verbose_name="Data de início pretendida")

    # Computed eligibility
    contribution_months_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Meses de contribuição",
    )
    average_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Salário médio",
    )
    is_eligible = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="Elegível",
    )

    # Processing timestamps
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="Submetida em")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_benefit_requests",
        verbose_name="Revisado por",
    )
    review_started_at = models.DateTimeField(null=True, blank=True, verbose_name="Revisão iniciada em")
    decided_at = models.DateTimeField(null=True, blank=True, verbose_name="Decisão em")

    # Decision
    decision_notes = models.TextField(blank=True, verbose_name="Notas de decisão")
    rejection_reason = models.CharField(max_length=200, blank=True, verbose_name="Motivo de rejeição")
    approved_monthly_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Montante mensal aprovado",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_benefit_requests",
        verbose_name="Criado por",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Solicitação de Prestação"
        verbose_name_plural = "Solicitações de Prestações"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.reference} — {self.applicant_name} ({self.get_status_display()})"

    def _generate_reference(self) -> str:
        year = timezone.now().year
        count = BenefitRequest.objects.filter(
            created_at__year=year
        ).count() + 1
        return f"PREST-{year}-{count:05d}"

    def save(self, *args, **kwargs) -> None:
        if not self.reference:
            self.reference = self._generate_reference()
        super().save(*args, **kwargs)

    def compute_eligibility(self) -> None:
        """
        Counts paid contributions for this affiliate, computes average salary
        over the last 36 months of paid contributions, and checks eligibility.
        """
        from apps.contributions.models import Contribution, ContributionStatus

        paid_contributions = Contribution.objects.filter(
            affiliate=self.affiliate,
            status=ContributionStatus.PAID,
        ).order_by("-period_year", "-period_month")

        count = paid_contributions.count()
        self.contribution_months_count = count

        # Average salary over last 36 paid months
        last_36 = paid_contributions[:36]
        if last_36.exists():
            avg = last_36.aggregate(avg=Avg("salary_base"))["avg"] or 0
            self.average_salary = avg
        else:
            self.average_salary = 0

        # Check eligibility
        self.is_eligible = count >= self.benefit_type.min_contribution_months

        # Compute approved monthly amount
        if self.is_eligible:
            method = self.benefit_type.calculation_method
            if method == CalculationMethod.FIXED and self.benefit_type.fixed_amount is not None:
                self.approved_monthly_amount = self.benefit_type.fixed_amount
            elif method == CalculationMethod.PERCENTAGE and self.benefit_type.percentage_of_salary is not None:
                self.approved_monthly_amount = (
                    self.average_salary * self.benefit_type.percentage_of_salary / 100
                )

        self.save(update_fields=[
            "contribution_months_count",
            "average_salary",
            "is_eligible",
            "approved_monthly_amount",
            "updated_at",
        ])

    def can_transition_to(self, new_status: str) -> bool:
        """Returns True if the status transition is valid."""
        allowed = VALID_TRANSITIONS.get(self.status, [])
        return new_status in allowed


class DocumentType(models.TextChoices):
    ID_CARD = "ID_CARD", "Bilhete de Identidade"
    BIRTH_CERT = "BIRTH_CERT", "Certidão de Nascimento"
    MEDICAL_CERT = "MEDICAL_CERT", "Atestado Médico"
    EMPLOYER_CERT = "EMPLOYER_CERT", "Declaração do Empregador"
    BANK_STATEMENT = "BANK_STATEMENT", "Extrato Bancário"
    OTHER = "OTHER", "Outro"


class BenefitDocument(models.Model):
    request = models.ForeignKey(
        BenefitRequest,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="Solicitação",
    )
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        verbose_name="Tipo de documento",
    )
    name = models.CharField(max_length=200, verbose_name="Nome")
    file = models.FileField(
        upload_to="benefits/documents/%Y/%m/",
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
        verbose_name = "Documento de Prestação"
        verbose_name_plural = "Documentos de Prestações"
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"{self.get_document_type_display()} — {self.request.reference}"


class PaymentStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Agendado"
    PAID = "PAID", "Pago"
    FAILED = "FAILED", "Falhou"
    CANCELLED = "CANCELLED", "Cancelado"


class BenefitPayment(models.Model):
    request = models.ForeignKey(
        BenefitRequest,
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="Solicitação",
    )
    period_year = models.PositiveIntegerField(verbose_name="Ano do período")
    period_month = models.PositiveIntegerField(verbose_name="Mês do período")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Montante",
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.SCHEDULED,
        verbose_name="Estado",
    )
    scheduled_date = models.DateField(verbose_name="Data agendada")
    paid_date = models.DateField(null=True, blank=True, verbose_name="Data de pagamento")
    payment_reference = models.CharField(max_length=100, blank=True, verbose_name="Referência de pagamento")
    notes = models.TextField(blank=True, verbose_name="Notas")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Pagamento de Prestação"
        verbose_name_plural = "Pagamentos de Prestações"
        ordering = ["-period_year", "-period_month"]
        unique_together = [("request", "period_year", "period_month")]

    def __str__(self) -> str:
        return f"{self.request.reference} — {self.period_year}/{self.period_month:02d} ({self.get_status_display()})"


class BenefitStatusHistory(models.Model):
    request = models.ForeignKey(
        BenefitRequest,
        on_delete=models.CASCADE,
        related_name="history",
        verbose_name="Solicitação",
    )
    old_status = models.CharField(max_length=20, blank=True, verbose_name="Estado anterior")
    new_status = models.CharField(max_length=20, verbose_name="Novo estado")
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="Alterado por",
    )
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="Alterado em")
    comment = models.TextField(blank=True, verbose_name="Comentário")

    class Meta:
        verbose_name = "Histórico de Estado"
        verbose_name_plural = "Histórico de Estados"
        ordering = ["-changed_at"]

    def __str__(self) -> str:
        return f"{self.request.reference}: {self.old_status} → {self.new_status}"

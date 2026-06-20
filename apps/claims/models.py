from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class ReclamationType(models.TextChoices):
    CONTRIBUTION_ERROR = "CONTRIBUTION_ERROR", "Erro em Cotização"
    BENEFIT_DECISION = "BENEFIT_DECISION", "Contestação de Prestação"
    CARD_ISSUE = "CARD_ISSUE", "Problema com Cartão"
    PENALTY_DISPUTE = "PENALTY_DISPUTE", "Contestação de Penalidade"
    DATA_ERROR = "DATA_ERROR", "Erro de Dados Pessoais"
    TECHNICAL = "TECHNICAL", "Problema Técnico"
    OTHER = "OTHER", "Outro"


class ClaimStatus(models.TextChoices):
    OPEN = "OPEN", "Aberta"
    UNDER_REVIEW = "UNDER_REVIEW", "Em Análise"
    ADDITIONAL_INFO = "ADDITIONAL_INFO", "Info Adicional Solicitada"
    RESOLVED = "RESOLVED", "Resolvida"
    REJECTED = "REJECTED", "Rejeitada"
    ESCALATED = "ESCALATED", "Escalada"


class ClaimPriority(models.TextChoices):
    LOW = "LOW", "Baixa"
    NORMAL = "NORMAL", "Normal"
    HIGH = "HIGH", "Alta"
    URGENT = "URGENT", "Urgente"


VALID_TRANSITIONS = {
    ClaimStatus.OPEN: [ClaimStatus.UNDER_REVIEW],
    ClaimStatus.UNDER_REVIEW: [
        ClaimStatus.RESOLVED,
        ClaimStatus.REJECTED,
        ClaimStatus.ADDITIONAL_INFO,
        ClaimStatus.ESCALATED,
    ],
    ClaimStatus.ADDITIONAL_INFO: [ClaimStatus.UNDER_REVIEW],
    ClaimStatus.ESCALATED: [
        ClaimStatus.UNDER_REVIEW,
        ClaimStatus.RESOLVED,
        ClaimStatus.REJECTED,
    ],
    ClaimStatus.RESOLVED: [],
    ClaimStatus.REJECTED: [],
}


class Claim(models.Model):
    reference = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        verbose_name="Referência",
    )

    # Who filed it
    filed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="filed_claims",
        verbose_name="Submetida por",
    )
    affiliate = models.ForeignKey(
        "affiliates.Affiliate",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="claims",
        verbose_name="Afiliado",
    )
    employer = models.ForeignKey(
        "employers.Employer",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="claims",
        verbose_name="Empregador",
    )

    # What it's about
    claim_type = models.CharField(
        max_length=30,
        choices=ReclamationType.choices,
        verbose_name="Tipo de Reclamação",
    )
    subject = models.CharField(max_length=300, verbose_name="Assunto")
    description = models.TextField(verbose_name="Descrição")
    priority = models.CharField(
        max_length=10,
        choices=ClaimPriority.choices,
        default=ClaimPriority.NORMAL,
        verbose_name="Prioridade",
    )

    # Optional link to related object
    related_resource_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Tipo de recurso relacionado",
    )
    related_resource_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="ID do recurso relacionado",
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=ClaimStatus.choices,
        default=ClaimStatus.OPEN,
        verbose_name="Estado",
    )

    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_claims",
        verbose_name="Atribuída a",
    )

    # Dates
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Submetida em")
    review_started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Revisão iniciada em",
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Resolvida em",
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Prazo (SLA)",
    )

    # Resolution
    resolution_notes = models.TextField(blank=True, verbose_name="Notas de resolução")
    rejection_reason = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Motivo de rejeição",
    )

    # Satisfaction (citizen rates resolution)
    satisfaction_rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Avaliação de satisfação (1-5)",
    )
    satisfaction_comment = models.TextField(
        blank=True,
        verbose_name="Comentário de satisfação",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Reclamação"
        verbose_name_plural = "Reclamações"
        ordering = ["-submitted_at"]

    def __str__(self) -> str:
        return f"{self.reference} — {self.subject[:50]} ({self.get_status_display()})"

    def _generate_reference(self) -> str:
        year = timezone.now().year
        count = Claim.objects.filter(submitted_at__year=year).count() + 1
        return f"REC-{year}-{count:05d}"

    def save(self, *args, **kwargs) -> None:
        if not self.reference:
            self.reference = self._generate_reference()
        # Auto-set SLA due_date on first save
        if not self.due_date and not self.pk:
            self.due_date = date.today() + timedelta(days=15)
        super().save(*args, **kwargs)

    def can_transition_to(self, new_status: str) -> bool:
        """Returns True if the status transition is valid."""
        allowed = VALID_TRANSITIONS.get(self.status, [])
        return new_status in allowed

    @property
    def is_overdue(self) -> bool:
        if self.due_date and self.status not in (ClaimStatus.RESOLVED, ClaimStatus.REJECTED):
            return date.today() > self.due_date
        return False

    @property
    def days_open(self) -> int:
        end = self.resolved_at.date() if self.resolved_at else date.today()
        return (end - self.submitted_at.date()).days


class ClaimMessage(models.Model):
    """Threaded messages on a claim (like a ticket system)."""

    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Reclamação",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="Autor",
    )
    body = models.TextField(verbose_name="Mensagem")
    is_internal = models.BooleanField(
        default=False,
        verbose_name="Nota interna (não visível ao cidadão)",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Mensagem de Reclamação"
        verbose_name_plural = "Mensagens de Reclamações"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Mensagem de {self.author.email} em {self.claim.reference}"


class ClaimDocument(models.Model):
    """File attachments on a claim."""

    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="Reclamação",
    )
    name = models.CharField(max_length=200, verbose_name="Nome")
    file = models.FileField(
        upload_to="claims/documents/%Y/%m/",
        verbose_name="Ficheiro",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="Carregado por",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Carregado em")

    class Meta:
        verbose_name = "Documento de Reclamação"
        verbose_name_plural = "Documentos de Reclamações"
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"{self.name} — {self.claim.reference}"


class ClaimStatusHistory(models.Model):
    """Immutable status change log."""

    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name="history",
        verbose_name="Reclamação",
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
        verbose_name = "Histórico de Estado de Reclamação"
        verbose_name_plural = "Histórico de Estados de Reclamações"
        ordering = ["changed_at"]

    def __str__(self) -> str:
        return f"{self.claim.reference}: {self.old_status} → {self.new_status}"

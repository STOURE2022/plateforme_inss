from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    BenefitType,
    BenefitRequest,
    BenefitDocument,
    BenefitPayment,
    BenefitStatusHistory,
    BenefitRequestStatus,
)


@admin.register(BenefitType)
class BenefitTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "calculation_method", "min_contribution_months", "is_active", "created_at"]
    list_filter = ["category", "is_active", "calculation_method"]
    search_fields = ["name", "description"]
    list_editable = ["is_active"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = [
        (None, {
            "fields": ["category", "name", "description", "is_active"],
        }),
        (_("Elegibilidade"), {
            "fields": ["min_contribution_months"],
        }),
        (_("Cálculo"), {
            "fields": ["calculation_method", "fixed_amount", "percentage_of_salary"],
        }),
        (_("Auditoria"), {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]


class BenefitDocumentInline(admin.TabularInline):
    model = BenefitDocument
    extra = 0
    readonly_fields = ["uploaded_at", "uploaded_by"]
    fields = ["document_type", "name", "file", "notes", "uploaded_by", "uploaded_at"]


class BenefitPaymentInline(admin.TabularInline):
    model = BenefitPayment
    extra = 0
    readonly_fields = ["created_at"]
    fields = ["period_year", "period_month", "amount", "status", "scheduled_date", "paid_date", "payment_reference", "notes"]


class BenefitStatusHistoryInline(admin.TabularInline):
    model = BenefitStatusHistory
    extra = 0
    readonly_fields = ["old_status", "new_status", "changed_by", "changed_at", "comment"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(BenefitRequest)
class BenefitRequestAdmin(admin.ModelAdmin):
    list_display = [
        "reference",
        "applicant_name",
        "applicant_niss",
        "benefit_type",
        "status_badge",
        "submitted_at",
        "reviewed_by",
    ]
    list_filter = ["status", "benefit_type__category", "benefit_type"]
    search_fields = ["reference", "applicant_niss", "applicant_name"]
    readonly_fields = [
        "reference",
        "contribution_months_count",
        "average_salary",
        "is_eligible",
        "submitted_at",
        "review_started_at",
        "decided_at",
        "created_at",
        "updated_at",
    ]
    inlines = [BenefitDocumentInline, BenefitPaymentInline, BenefitStatusHistoryInline]
    fieldsets = [
        (_("Identificação"), {
            "fields": ["reference", "affiliate", "benefit_type", "status"],
        }),
        (_("Requerente (snapshot)"), {
            "fields": ["applicant_name", "applicant_niss", "applicant_birth_date"],
        }),
        (_("Detalhes da Solicitação"), {
            "fields": ["justification", "requested_start_date"],
        }),
        (_("Elegibilidade Calculada"), {
            "fields": ["contribution_months_count", "average_salary", "is_eligible"],
        }),
        (_("Processamento"), {
            "fields": ["submitted_at", "reviewed_by", "review_started_at", "decided_at"],
        }),
        (_("Decisão"), {
            "fields": ["decision_notes", "rejection_reason", "approved_monthly_amount"],
        }),
        (_("Auditoria"), {
            "fields": ["created_by", "created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]
    actions = ["mark_under_review", "mark_approved", "mark_rejected"]

    @admin.display(description="Estado")
    def status_badge(self, obj):
        colors = {
            BenefitRequestStatus.DRAFT: "#94a3b8",
            BenefitRequestStatus.SUBMITTED: "#3b82f6",
            BenefitRequestStatus.UNDER_REVIEW: "#8b5cf6",
            BenefitRequestStatus.ADDITIONAL_DOCS: "#f59e0b",
            BenefitRequestStatus.APPROVED: "#10b981",
            BenefitRequestStatus.REJECTED: "#ef4444",
            BenefitRequestStatus.PAYING: "#06b6d4",
            BenefitRequestStatus.CLOSED: "#6b7280",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.action(description=_("Marcar em revisão"))
    def mark_under_review(self, request, queryset):
        updated = 0
        for obj in queryset.filter(status=BenefitRequestStatus.SUBMITTED):
            from django.utils import timezone
            obj.status = BenefitRequestStatus.UNDER_REVIEW
            obj.reviewed_by = request.user
            obj.review_started_at = timezone.now()
            obj.save(update_fields=["status", "reviewed_by", "review_started_at", "updated_at"])
            BenefitStatusHistory.objects.create(
                request=obj,
                old_status=BenefitRequestStatus.SUBMITTED,
                new_status=BenefitRequestStatus.UNDER_REVIEW,
                changed_by=request.user,
                comment="Ação em massa pelo administrador.",
            )
            updated += 1
        self.message_user(request, _(f"{updated} solicitação(ões) marcada(s) em revisão."))

    @admin.action(description=_("Aprovar"))
    def mark_approved(self, request, queryset):
        updated = 0
        for obj in queryset.filter(status=BenefitRequestStatus.UNDER_REVIEW):
            from django.utils import timezone
            old_status = obj.status
            obj.status = BenefitRequestStatus.APPROVED
            obj.decided_at = timezone.now()
            obj.compute_eligibility()
            obj.save(update_fields=["status", "decided_at", "updated_at"])
            BenefitStatusHistory.objects.create(
                request=obj,
                old_status=old_status,
                new_status=BenefitRequestStatus.APPROVED,
                changed_by=request.user,
                comment="Aprovada pelo administrador.",
            )
            updated += 1
        self.message_user(request, _(f"{updated} solicitação(ões) aprovada(s)."))

    @admin.action(description=_("Rejeitar"))
    def mark_rejected(self, request, queryset):
        updated = 0
        for obj in queryset.filter(status__in=[
            BenefitRequestStatus.SUBMITTED,
            BenefitRequestStatus.UNDER_REVIEW,
            BenefitRequestStatus.ADDITIONAL_DOCS,
        ]):
            from django.utils import timezone
            old_status = obj.status
            obj.status = BenefitRequestStatus.REJECTED
            obj.decided_at = timezone.now()
            obj.save(update_fields=["status", "decided_at", "updated_at"])
            BenefitStatusHistory.objects.create(
                request=obj,
                old_status=old_status,
                new_status=BenefitRequestStatus.REJECTED,
                changed_by=request.user,
                comment="Rejeitada pelo administrador.",
            )
            updated += 1
        self.message_user(request, _(f"{updated} solicitação(ões) rejeitada(s)."))

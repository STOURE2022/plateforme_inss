from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .models import (
    Claim,
    ClaimMessage,
    ClaimDocument,
    ClaimStatusHistory,
    ClaimStatus,
    ClaimPriority,
)


class ClaimMessageInline(admin.TabularInline):
    model = ClaimMessage
    extra = 0
    readonly_fields = ["author", "created_at", "is_internal"]
    fields = ["author", "body", "is_internal", "created_at"]

    def has_add_permission(self, request, obj=None):
        return False


class ClaimDocumentInline(admin.TabularInline):
    model = ClaimDocument
    extra = 0
    readonly_fields = ["uploaded_by", "uploaded_at"]
    fields = ["name", "file", "uploaded_by", "uploaded_at"]


class ClaimStatusHistoryInline(admin.TabularInline):
    model = ClaimStatusHistory
    extra = 0
    readonly_fields = ["old_status", "new_status", "changed_by", "changed_at", "comment"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = [
        "reference",
        "claim_type",
        "subject_truncated",
        "filed_by",
        "status_badge",
        "priority_badge",
        "submitted_at",
        "due_date",
        "overdue_flag",
        "assigned_to",
    ]
    list_filter = ["status", "claim_type", "priority"]
    search_fields = ["reference", "subject", "filed_by__email"]
    readonly_fields = [
        "reference",
        "submitted_at",
        "review_started_at",
        "resolved_at",
        "created_at",
        "updated_at",
    ]
    inlines = [ClaimMessageInline, ClaimDocumentInline, ClaimStatusHistoryInline]
    fieldsets = [
        (_("Identificação"), {
            "fields": ["reference", "status", "priority", "assigned_to"],
        }),
        (_("Requerente"), {
            "fields": ["filed_by", "affiliate", "employer"],
        }),
        (_("Reclamação"), {
            "fields": ["claim_type", "subject", "description"],
        }),
        (_("Recurso relacionado"), {
            "fields": ["related_resource_type", "related_resource_id"],
            "classes": ["collapse"],
        }),
        (_("Prazos"), {
            "fields": ["submitted_at", "review_started_at", "resolved_at", "due_date"],
        }),
        (_("Resolução"), {
            "fields": ["resolution_notes", "rejection_reason"],
        }),
        (_("Satisfação"), {
            "fields": ["satisfaction_rating", "satisfaction_comment"],
            "classes": ["collapse"],
        }),
        (_("Auditoria"), {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]
    actions = ["action_take_charge", "action_resolve", "action_reject"]

    @admin.display(description="Assunto")
    def subject_truncated(self, obj):
        return obj.subject[:60] + "…" if len(obj.subject) > 60 else obj.subject

    @admin.display(description="Estado")
    def status_badge(self, obj):
        colors = {
            ClaimStatus.OPEN: "#3b82f6",
            ClaimStatus.UNDER_REVIEW: "#8b5cf6",
            ClaimStatus.ADDITIONAL_INFO: "#f59e0b",
            ClaimStatus.RESOLVED: "#10b981",
            ClaimStatus.REJECTED: "#ef4444",
            ClaimStatus.ESCALATED: "#f97316",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description="Prioridade")
    def priority_badge(self, obj):
        colors = {
            ClaimPriority.LOW: "#94a3b8",
            ClaimPriority.NORMAL: "#3b82f6",
            ClaimPriority.HIGH: "#f59e0b",
            ClaimPriority.URGENT: "#ef4444",
        }
        color = colors.get(obj.priority, "#6b7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">{}</span>',
            color,
            obj.get_priority_display(),
        )

    @admin.display(description="Prazo", boolean=False)
    def overdue_flag(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color:#ef4444;font-weight:700">ATRASADA</span>')
        return "—"

    @admin.action(description=_("Prendre en charge (OPEN → UNDER_REVIEW)"))
    def action_take_charge(self, request, queryset):
        updated = 0
        for obj in queryset.filter(status=ClaimStatus.OPEN):
            old_status = obj.status
            obj.status = ClaimStatus.UNDER_REVIEW
            obj.assigned_to = request.user
            obj.review_started_at = timezone.now()
            obj.save(update_fields=["status", "assigned_to", "review_started_at", "updated_at"])
            ClaimStatusHistory.objects.create(
                claim=obj,
                old_status=old_status,
                new_status=ClaimStatus.UNDER_REVIEW,
                changed_by=request.user,
                comment="Tomado a cargo pelo administrador.",
            )
            updated += 1
        self.message_user(request, _(f"{updated} reclamação(ões) tomada(s) a cargo."))

    @admin.action(description=_("Resolver"))
    def action_resolve(self, request, queryset):
        updated = 0
        for obj in queryset.filter(status__in=[ClaimStatus.UNDER_REVIEW, ClaimStatus.ESCALATED]):
            old_status = obj.status
            obj.status = ClaimStatus.RESOLVED
            obj.resolved_at = timezone.now()
            obj.save(update_fields=["status", "resolved_at", "updated_at"])
            ClaimStatusHistory.objects.create(
                claim=obj,
                old_status=old_status,
                new_status=ClaimStatus.RESOLVED,
                changed_by=request.user,
                comment="Resolvida pelo administrador.",
            )
            updated += 1
        self.message_user(request, _(f"{updated} reclamação(ões) resolvida(s)."))

    @admin.action(description=_("Rejeitar"))
    def action_reject(self, request, queryset):
        updated = 0
        for obj in queryset.filter(
            status__in=[ClaimStatus.OPEN, ClaimStatus.UNDER_REVIEW, ClaimStatus.ESCALATED]
        ):
            old_status = obj.status
            obj.status = ClaimStatus.REJECTED
            obj.resolved_at = timezone.now()
            obj.save(update_fields=["status", "resolved_at", "updated_at"])
            ClaimStatusHistory.objects.create(
                claim=obj,
                old_status=old_status,
                new_status=ClaimStatus.REJECTED,
                changed_by=request.user,
                comment="Rejeitada pelo administrador.",
            )
            updated += 1
        self.message_user(request, _(f"{updated} reclamação(ões) rejeitada(s)."))

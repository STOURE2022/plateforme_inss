from django.contrib import admin
from django.utils.html import format_html

from .models import (
    ControlAssessment,
    ControlDocument,
    ControlPayment,
    ControlStatus,
    ControlStatusHistory,
    EmployerControl,
)


class ControlAssessmentInline(admin.TabularInline):
    model = ControlAssessment
    extra = 0
    readonly_fields = ("salary_difference", "assessed_amount", "penalty_amount", "total_line")
    fields = (
        "period_year",
        "period_month",
        "declared_salary",
        "actual_salary",
        "salary_difference",
        "assessed_amount",
        "penalty_rate",
        "penalty_amount",
        "total_line",
        "notes",
    )


class ControlDocumentInline(admin.TabularInline):
    model = ControlDocument
    extra = 0
    readonly_fields = ("uploaded_at",)
    fields = ("doc_type", "name", "file", "notes", "uploaded_by", "uploaded_at")


class ControlPaymentInline(admin.TabularInline):
    model = ControlPayment
    extra = 0
    readonly_fields = ("recorded_at",)
    fields = ("amount", "payment_date", "payment_reference", "status", "notes", "recorded_by", "recorded_at")


class ControlStatusHistoryInline(admin.TabularInline):
    model = ControlStatusHistory
    extra = 0
    readonly_fields = ("old_status", "new_status", "changed_by", "changed_at", "comment")
    fields = ("old_status", "new_status", "changed_by", "changed_at", "comment")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


STATUS_COLORS = {
    ControlStatus.PLANNED: "#6366f1",
    ControlStatus.IN_PROGRESS: "#f59e0b",
    ControlStatus.PV_DRAFTED: "#8b5cf6",
    ControlStatus.NOTIFIED: "#3b82f6",
    ControlStatus.DISPUTED: "#ef4444",
    ControlStatus.SETTLED: "#10b981",
    ControlStatus.CLOSED: "#6b7280",
}


@admin.register(EmployerControl)
class EmployerControlAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "employer",
        "control_type",
        "colored_status",
        "period_from",
        "period_to",
        "total_due",
        "total_remaining",
        "assigned_agent",
    )
    list_filter = ("status", "control_type", "period_from")
    search_fields = ("reference", "employer__company_name", "employer__nuit")
    readonly_fields = (
        "reference",
        "pv_reference",
        "total_assessed",
        "total_penalties",
        "total_due",
        "total_paid",
        "total_remaining",
        "created_at",
        "updated_at",
    )
    inlines = [
        ControlAssessmentInline,
        ControlDocumentInline,
        ControlPaymentInline,
        ControlStatusHistoryInline,
    ]
    fieldsets = (
        (
            "Identificação",
            {
                "fields": (
                    "reference",
                    "employer",
                    "control_type",
                    "status",
                    "assigned_agent",
                    "triggered_by_claim",
                )
            },
        ),
        (
            "Período auditado",
            {"fields": ("period_from", "period_to")},
        ),
        (
            "Constatações",
            {"fields": ("findings_summary",)},
        ),
        (
            "Procès-Verbal",
            {"fields": ("pv_reference", "pv_date", "pv_notes")},
        ),
        (
            "Notificação",
            {"fields": ("notified_at", "notification_deadline")},
        ),
        (
            "Resumo financeiro",
            {
                "fields": (
                    "total_assessed",
                    "total_penalties",
                    "total_due",
                    "total_paid",
                    "total_remaining",
                )
            },
        ),
        (
            "Contestação",
            {"fields": ("dispute_reason", "dispute_filed_at"), "classes": ("collapse",)},
        ),
        (
            "Encerramento",
            {"fields": ("closed_at", "closure_notes"), "classes": ("collapse",)},
        ),
        (
            "Auditoria",
            {"fields": ("created_by", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
    actions = ["action_iniciar_controlo", "action_redigir_pv", "action_notificar_empregador"]

    def colored_status(self, obj):
        color = STATUS_COLORS.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{}; color:white; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:600;">{}</span>',
            color,
            obj.get_status_display(),
        )

    colored_status.short_description = "Estado"

    @admin.action(description="Iniciar controlo (PLANNED → IN_PROGRESS)")
    def action_iniciar_controlo(self, request, queryset):
        updated = 0
        for ctrl in queryset.filter(status=ControlStatus.PLANNED):
            old = ctrl.status
            ctrl.status = ControlStatus.IN_PROGRESS
            ctrl.save(update_fields=["status", "updated_at"])
            ControlStatusHistory.objects.create(
                control=ctrl,
                old_status=old,
                new_status=ControlStatus.IN_PROGRESS,
                changed_by=request.user,
                comment="Iniciado via admin.",
            )
            updated += 1
        self.message_user(request, f"{updated} controlo(s) iniciado(s).")

    @admin.action(description="Redigir PV (IN_PROGRESS → PV_DRAFTED)")
    def action_redigir_pv(self, request, queryset):
        import datetime

        updated = 0
        for ctrl in queryset.filter(status=ControlStatus.IN_PROGRESS):
            old = ctrl.status
            ctrl.status = ControlStatus.PV_DRAFTED
            if not ctrl.pv_date:
                ctrl.pv_date = datetime.date.today()
            ctrl.save(update_fields=["status", "pv_date", "updated_at"])
            ControlStatusHistory.objects.create(
                control=ctrl,
                old_status=old,
                new_status=ControlStatus.PV_DRAFTED,
                changed_by=request.user,
                comment="PV redigido via admin.",
            )
            updated += 1
        self.message_user(request, f"{updated} PV(s) redigido(s).")

    @admin.action(description="Notificar empregador (PV_DRAFTED → NOTIFIED)")
    def action_notificar_empregador(self, request, queryset):
        import datetime

        from django.utils import timezone

        updated = 0
        for ctrl in queryset.filter(status=ControlStatus.PV_DRAFTED):
            old = ctrl.status
            ctrl.status = ControlStatus.NOTIFIED
            ctrl.notified_at = timezone.now()
            if ctrl.pv_date:
                ctrl.notification_deadline = ctrl.pv_date + datetime.timedelta(days=30)
            ctrl.save(update_fields=["status", "notified_at", "notification_deadline", "updated_at"])
            ControlStatusHistory.objects.create(
                control=ctrl,
                old_status=old,
                new_status=ControlStatus.NOTIFIED,
                changed_by=request.user,
                comment="Empregador notificado via admin.",
            )
            updated += 1
        self.message_user(request, f"{updated} empregador(es) notificado(s).")

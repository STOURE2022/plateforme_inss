from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import DeclarationStatus, PayrollDeclaration, PayrollDeclarationLine


class PayrollDeclarationLineInline(admin.TabularInline):
    model = PayrollDeclarationLine
    extra = 0
    fields = (
        "affiliate",
        "salary_base",
        "employee_rate",
        "employer_rate",
        "employee_amount",
        "employer_amount",
        "total_amount",
        "contribution",
        "notes",
    )
    readonly_fields = ("employee_amount", "employer_amount", "total_amount", "contribution")
    autocomplete_fields = ["affiliate"]


@admin.register(PayrollDeclaration)
class PayrollDeclarationAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "employer",
        "period_display",
        "status_badge",
        "total_employees",
        "total_contributions_display",
        "submitted_at",
        "validated_by",
    )
    list_filter = ("status", "period_year", "period_month")
    search_fields = ("reference", "employer__company_name", "employer__nuit")
    readonly_fields = (
        "reference",
        "total_employees",
        "total_salary_base",
        "total_employee_contributions",
        "total_employer_contributions",
        "total_contributions",
        "submitted_at",
        "validated_at",
        "rejected_at",
        "created_at",
        "updated_at",
    )
    inlines = [PayrollDeclarationLineInline]
    actions = ["action_validate", "action_reject"]

    fieldsets = (
        (
            "Identificação",
            {
                "fields": (
                    "reference",
                    "employer",
                    "period_year",
                    "period_month",
                    "status",
                    "created_by",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            "Totais",
            {
                "fields": (
                    "total_employees",
                    "total_salary_base",
                    "total_employee_contributions",
                    "total_employer_contributions",
                    "total_contributions",
                )
            },
        ),
        (
            "Submissão",
            {"fields": ("submitted_at",)},
        ),
        (
            "Validação",
            {"fields": ("validated_by", "validated_at", "validation_notes")},
        ),
        (
            "Rejeição",
            {"fields": ("rejected_by", "rejected_at", "rejection_reason")},
        ),
    )

    def period_display(self, obj):
        return obj.get_period_display()

    period_display.short_description = "Período"

    def status_badge(self, obj):
        colors = {
            DeclarationStatus.DRAFT: "#6B7280",
            DeclarationStatus.SUBMITTED: "#D97706",
            DeclarationStatus.VALIDATED: "#059669",
            DeclarationStatus.REJECTED: "#DC2626",
        }
        color = colors.get(obj.status, "#6B7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:9999px;font-size:11px;font-weight:600;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Estado"

    def total_contributions_display(self, obj):
        return f"{obj.total_contributions:,.0f} XOF"

    total_contributions_display.short_description = "Total XOF"

    @admin.action(description="Validar declarações selecionadas")
    def action_validate(self, request, queryset):
        count = 0
        for decl in queryset.filter(status=DeclarationStatus.SUBMITTED):
            decl.status = DeclarationStatus.VALIDATED
            decl.validated_by = request.user
            decl.validated_at = timezone.now()
            decl.save(update_fields=["status", "validated_by", "validated_at", "updated_at"])
            decl.generate_contributions(request.user)
            count += 1
        self.message_user(request, f"{count} declaração(ões) validada(s) com sucesso.")

    @admin.action(description="Rejeitar declarações selecionadas")
    def action_reject(self, request, queryset):
        count = 0
        for decl in queryset.filter(status=DeclarationStatus.SUBMITTED):
            decl.status = DeclarationStatus.REJECTED
            decl.rejected_by = request.user
            decl.rejected_at = timezone.now()
            decl.rejection_reason = "Rejeitada pelo administrador (ação em massa)."
            decl.save(
                update_fields=["status", "rejected_by", "rejected_at", "rejection_reason", "updated_at"]
            )
            count += 1
        self.message_user(request, f"{count} declaração(ões) rejeitada(s).")

from django.contrib import admin
from .models import Contribution


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = [
        "reference",
        "affiliate",
        "employer",
        "period_year",
        "period_month",
        "total_amount",
        "status",
        "payment_date",
        "created_at",
    ]
    list_filter = ["status", "period_year", "period_month"]
    search_fields = ["reference", "affiliate__niss", "affiliate__full_name", "employer__company_name"]
    readonly_fields = ["reference", "employee_amount", "employer_amount", "total_amount", "created_at", "created_by"]
    ordering = ["-period_year", "-period_month"]
    date_hierarchy = "created_at"
    raw_id_fields = ["affiliate", "employer"]

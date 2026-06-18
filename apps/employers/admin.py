from django.contrib import admin
from .models import Employer


@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display = ["company_name", "nuit", "sector", "status", "registration_date", "registered_by"]
    list_filter = ["status", "sector"]
    search_fields = ["company_name", "nuit", "user__email", "phone", "email"]
    readonly_fields = ["registration_date"]
    ordering = ["-registration_date"]
    date_hierarchy = "registration_date"
    raw_id_fields = ["user", "registered_by"]

from django.contrib import admin
from .models import Affiliate, Dependent


class DependentInline(admin.TabularInline):
    model = Dependent
    extra = 0
    fields = ["full_name", "birth_date", "relationship", "is_active"]


@admin.register(Affiliate)
class AffiliateAdmin(admin.ModelAdmin):
    list_display = ["niss", "full_name", "gender", "nationality", "status", "registration_date"]
    list_filter = ["status", "gender", "nationality"]
    search_fields = ["niss", "full_name", "user__email", "phone"]
    readonly_fields = ["registration_date"]
    inlines = [DependentInline]
    ordering = ["-registration_date"]
    date_hierarchy = "registration_date"


@admin.register(Dependent)
class DependentAdmin(admin.ModelAdmin):
    list_display = ["full_name", "affiliate", "relationship", "birth_date", "is_active"]
    list_filter = ["relationship", "is_active"]
    search_fields = ["full_name", "affiliate__full_name", "affiliate__niss"]
    ordering = ["affiliate__full_name", "full_name"]

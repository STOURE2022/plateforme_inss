from django.contrib import admin
from apps.audit.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "action", "user_email", "resource_type", "resource_repr", "ip_address"]
    list_filter = ["action", "resource_type", "timestamp"]
    search_fields = ["action", "user_email", "resource_repr", "ip_address"]
    ordering = ["-timestamp"]
    readonly_fields = [
        "user",
        "user_email",
        "user_role",
        "ip_address",
        "user_agent",
        "action",
        "resource_type",
        "resource_id",
        "resource_repr",
        "details",
        "old_values",
        "new_values",
        "timestamp",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

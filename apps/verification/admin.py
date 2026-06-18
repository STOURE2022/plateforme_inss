from django.contrib import admin
from .models import VerificationLog


@admin.register(VerificationLog)
class VerificationLogAdmin(admin.ModelAdmin):
    list_display = ["card_number", "result", "verifier_ip", "verified_at", "response_ms"]
    list_filter = ["result"]
    search_fields = ["card_number", "verifier_ip"]
    ordering = ["-verified_at"]

    readonly_fields = [
        "verifier",
        "verifier_ip",
        "verifier_role",
        "card",
        "card_number",
        "token_jti",
        "result",
        "failure_reason",
        "verified_at",
        "response_ms",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

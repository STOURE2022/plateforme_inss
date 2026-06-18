from django.contrib import admin
from django.contrib import messages
from apps.cards.models import HealthCard


@admin.register(HealthCard)
class HealthCardAdmin(admin.ModelAdmin):
    list_display = [
        "card_number",
        "affiliate",
        "status",
        "issued_date",
        "expiry_date",
        "pdf_generated_at",
        "created_at",
    ]
    list_filter = ["status", "issued_date", "expiry_date"]
    search_fields = ["card_number", "affiliate__full_name", "affiliate__niss"]
    readonly_fields = [
        "card_number",
        "issued_date",
        "current_token_jti",
        "token_issued_at",
        "token_expires_at",
        "pdf_generated_at",
        "created_at",
        "updated_at",
    ]
    raw_id_fields = ["affiliate", "created_by"]
    actions = ["action_generate_pdf", "action_regenerate_token"]

    @admin.action(description="Gerar PDF do cartão")
    def action_generate_pdf(self, request, queryset):
        from apps.cards.tasks import generate_card_pdf_task

        count = 0
        for card in queryset:
            generate_card_pdf_task.delay(card.pk)
            count += 1
        self.message_user(
            request,
            f"Geração de PDF iniciada para {count} cartão(ões).",
            messages.SUCCESS,
        )

    @admin.action(description="Regenerar token QR")
    def action_regenerate_token(self, request, queryset):
        from apps.cards.services.qr_service import QRTokenService

        service = QRTokenService()
        count = 0
        for card in queryset:
            service.generate_token(card)
            count += 1
        self.message_user(
            request,
            f"Token QR regenerado para {count} cartão(ões).",
            messages.SUCCESS,
        )

from rest_framework import serializers
from apps.cards.models import HealthCard


class HealthCardSerializer(serializers.ModelSerializer):
    affiliate_name = serializers.CharField(source="affiliate.full_name", read_only=True)
    affiliate_niss = serializers.CharField(source="affiliate.niss", read_only=True)
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = HealthCard
        fields = [
            "id",
            "affiliate",
            "affiliate_name",
            "affiliate_niss",
            "card_number",
            "issued_date",
            "expiry_date",
            "status",
            "current_token_jti",
            "token_issued_at",
            "token_expires_at",
            "pdf_generated_at",
            "created_by",
            "created_at",
            "updated_at",
            "is_valid",
        ]
        read_only_fields = [
            "id",
            "card_number",
            "issued_date",
            "current_token_jti",
            "token_issued_at",
            "token_expires_at",
            "pdf_generated_at",
            "created_by",
            "created_at",
            "updated_at",
            "is_valid",
        ]

    def get_is_valid(self, obj) -> bool:
        return obj.is_valid()


class HealthCardCreateSerializer(serializers.ModelSerializer):
    """Serializer de criação: apenas o afiliado é obrigatório."""

    class Meta:
        model = HealthCard
        fields = ["affiliate", "expiry_date", "status"]

    def validate_affiliate(self, value):
        """Verifica que o afiliado não possui já um cartão ativo."""
        if HealthCard.objects.filter(affiliate=value).exists():
            raise serializers.ValidationError(
                "Este afiliado já possui um cartão de saúde."
            )
        return value

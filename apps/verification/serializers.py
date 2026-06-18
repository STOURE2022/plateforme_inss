from rest_framework import serializers
from .models import VerificationLog


class VerifyRequestSerializer(serializers.Serializer):
    """Valida o corpo da requisição POST /api/v1/verify/."""
    token = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            "required": "O campo 'token' é obrigatório.",
            "blank": "O campo 'token' não pode estar vazio.",
        },
    )


class VerifySuccessSerializer(serializers.Serializer):
    """Resposta de verificação bem-sucedida."""
    valid = serializers.BooleanField()
    card_number = serializers.CharField()
    status = serializers.CharField()
    affiliate_name = serializers.CharField()
    expiry_date = serializers.DateField()
    verified_at = serializers.DateTimeField()


class VerifyFailureSerializer(serializers.Serializer):
    """Resposta de verificação falhada."""
    valid = serializers.BooleanField()
    error = serializers.CharField()
    error_code = serializers.CharField()


class VerificationLogSerializer(serializers.ModelSerializer):
    """Serializer completo para leitura dos logs de verificação."""
    verifier_email = serializers.SerializerMethodField()

    class Meta:
        model = VerificationLog
        fields = [
            "id",
            "verifier",
            "verifier_email",
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
        read_only_fields = fields

    def get_verifier_email(self, obj) -> str | None:
        if obj.verifier:
            return obj.verifier.email
        return None

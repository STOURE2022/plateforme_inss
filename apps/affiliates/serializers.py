from rest_framework import serializers
from .models import Affiliate, Dependent


class DependentSerializer(serializers.ModelSerializer):
    relationship_display = serializers.CharField(source="get_relationship_display", read_only=True)

    class Meta:
        model = Dependent
        fields = [
            "id",
            "affiliate",
            "full_name",
            "birth_date",
            "relationship",
            "relationship_display",
            "is_active",
        ]
        read_only_fields = ["id", "affiliate"]


class AffiliateSerializer(serializers.ModelSerializer):
    """Serializer de leitura com dados completos."""

    gender_display = serializers.CharField(source="get_gender_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    dependents = DependentSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Affiliate
        fields = [
            "id",
            "user",
            "user_email",
            "niss",
            "full_name",
            "birth_date",
            "gender",
            "gender_display",
            "nationality",
            "address",
            "phone",
            "registration_date",
            "status",
            "status_display",
            "dependents",
        ]
        read_only_fields = ["id", "registration_date", "user_email"]


class AffiliateCreateSerializer(serializers.ModelSerializer):
    """Serializer de criação e atualização de afiliados."""

    class Meta:
        model = Affiliate
        fields = [
            "id",
            "user",
            "niss",
            "full_name",
            "birth_date",
            "gender",
            "nationality",
            "address",
            "phone",
            "status",
        ]
        read_only_fields = ["id"]

    def validate_user(self, value):
        from apps.accounts.models import UserRole
        if value.role != UserRole.CITIZEN:
            raise serializers.ValidationError(
                "O utilizador deve ter a função de Cidadão para ser afiliado."
            )
        if hasattr(value, "affiliate") and (
            self.instance is None or self.instance.user_id != value.id
        ):
            raise serializers.ValidationError(
                "Este utilizador já possui um perfil de afiliado."
            )
        return value

    def validate_niss(self, value):
        qs = Affiliate.objects.filter(niss=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Este NISS já está registado.")
        return value

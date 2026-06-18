from rest_framework import serializers
from .models import Employer


class EmployerSerializer(serializers.ModelSerializer):
    """Serializer de leitura."""

    sector_display = serializers.CharField(source="get_sector_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    registered_by_email = serializers.EmailField(source="registered_by.email", read_only=True)

    class Meta:
        model = Employer
        fields = [
            "id",
            "user",
            "user_email",
            "company_name",
            "nuit",
            "sector",
            "sector_display",
            "address",
            "phone",
            "email",
            "registration_date",
            "status",
            "status_display",
            "registered_by",
            "registered_by_email",
        ]
        read_only_fields = ["id", "registration_date", "registered_by", "registered_by_email"]


class EmployerCreateSerializer(serializers.ModelSerializer):
    """Serializer de criação e atualização de empregadores."""

    class Meta:
        model = Employer
        fields = [
            "id",
            "user",
            "company_name",
            "nuit",
            "sector",
            "address",
            "phone",
            "email",
            "status",
        ]
        read_only_fields = ["id"]

    def validate_user(self, value):
        from apps.accounts.models import UserRole
        if value.role != UserRole.EMPLOYER:
            raise serializers.ValidationError(
                "O utilizador deve ter a função de Empregador."
            )
        if hasattr(value, "employer") and (
            self.instance is None or self.instance.user_id != value.id
        ):
            raise serializers.ValidationError(
                "Este utilizador já possui um perfil de empregador."
            )
        return value

    def validate_nuit(self, value):
        qs = Employer.objects.filter(nuit=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Este NUIT já está registado.")
        return value

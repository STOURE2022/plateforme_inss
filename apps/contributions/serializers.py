from rest_framework import serializers
from .models import Contribution


class ContributionSerializer(serializers.ModelSerializer):
    """Serializer de leitura."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    affiliate_name = serializers.CharField(source="affiliate.full_name", read_only=True)
    affiliate_niss = serializers.CharField(source="affiliate.niss", read_only=True)
    employer_name = serializers.CharField(source="employer.company_name", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = Contribution
        fields = [
            "id",
            "affiliate",
            "affiliate_name",
            "affiliate_niss",
            "employer",
            "employer_name",
            "period_year",
            "period_month",
            "salary_base",
            "employee_rate",
            "employer_rate",
            "employee_amount",
            "employer_amount",
            "total_amount",
            "payment_date",
            "status",
            "status_display",
            "reference",
            "created_by",
            "created_by_email",
            "created_at",
            "notes",
        ]
        read_only_fields = [
            "id",
            "employee_amount",
            "employer_amount",
            "total_amount",
            "reference",
            "created_by",
            "created_at",
        ]


class ContributionCreateSerializer(serializers.ModelSerializer):
    """Serializer de criação e atualização de contribuições."""

    class Meta:
        model = Contribution
        fields = [
            "id",
            "affiliate",
            "employer",
            "period_year",
            "period_month",
            "salary_base",
            "employee_rate",
            "employer_rate",
            "payment_date",
            "status",
            "notes",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        period_year = attrs.get("period_year", getattr(self.instance, "period_year", None))
        period_month = attrs.get("period_month", getattr(self.instance, "period_month", None))
        affiliate = attrs.get("affiliate", getattr(self.instance, "affiliate", None))

        if period_month is not None and not (1 <= period_month <= 12):
            raise serializers.ValidationError(
                {"period_month": "O mês deve estar entre 1 e 12."}
            )

        if period_year and period_month and affiliate:
            qs = Contribution.objects.filter(
                affiliate=affiliate,
                period_year=period_year,
                period_month=period_month,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "Já existe uma contribuição para este afiliado neste período."
                )

        return attrs

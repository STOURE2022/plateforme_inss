import django_filters
from .models import VerificationLog, VerificationResult


class VerificationLogFilter(django_filters.FilterSet):
    """Filtros para o ViewSet de logs de verificação."""
    card_number = django_filters.CharFilter(
        field_name="card_number",
        lookup_expr="icontains",
        label="Número do cartão",
    )
    result = django_filters.ChoiceFilter(
        choices=VerificationResult.choices,
        label="Resultado",
    )
    verifier_ip = django_filters.CharFilter(
        field_name="verifier_ip",
        lookup_expr="exact",
        label="IP do verificador",
    )
    date_from = django_filters.DateTimeFilter(
        field_name="verified_at",
        lookup_expr="gte",
        label="Data de início",
    )
    date_to = django_filters.DateTimeFilter(
        field_name="verified_at",
        lookup_expr="lte",
        label="Data de fim",
    )

    class Meta:
        model = VerificationLog
        fields = ["card_number", "result", "verifier_ip", "date_from", "date_to"]

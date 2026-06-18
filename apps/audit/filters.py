import django_filters
from apps.audit.models import AuditEvent


class AuditEventFilter(django_filters.FilterSet):
    action = django_filters.CharFilter(lookup_expr="icontains")
    resource_type = django_filters.CharFilter(lookup_expr="iexact")
    user_email = django_filters.CharFilter(lookup_expr="icontains")
    date_from = django_filters.DateTimeFilter(field_name="timestamp", lookup_expr="gte")
    date_to = django_filters.DateTimeFilter(field_name="timestamp", lookup_expr="lte")

    class Meta:
        model = AuditEvent
        fields = ["action", "resource_type", "user_email", "date_from", "date_to"]

import django_filters
from .models import Contribution, ContributionStatus


class ContributionFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=ContributionStatus.choices)
    affiliate = django_filters.NumberFilter(field_name="affiliate__id")
    employer = django_filters.NumberFilter(field_name="employer__id")
    year = django_filters.NumberFilter(field_name="period_year")
    month = django_filters.NumberFilter(field_name="period_month")
    affiliate_niss = django_filters.CharFilter(field_name="affiliate__niss", lookup_expr="icontains")
    reference = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Contribution
        fields = ["status", "affiliate", "employer", "year", "month", "affiliate_niss", "reference"]

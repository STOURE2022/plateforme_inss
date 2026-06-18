import django_filters
from .models import Affiliate, AffiliateStatus, GenderChoices


class AffiliateFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=AffiliateStatus.choices)
    gender = django_filters.ChoiceFilter(choices=GenderChoices.choices)
    nationality = django_filters.CharFilter(lookup_expr="iexact")
    full_name = django_filters.CharFilter(lookup_expr="icontains")
    niss = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Affiliate
        fields = ["status", "gender", "nationality", "full_name", "niss"]

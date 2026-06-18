import django_filters
from .models import Employer, EmployerStatus, SectorChoices


class EmployerFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=EmployerStatus.choices)
    sector = django_filters.ChoiceFilter(choices=SectorChoices.choices)
    company_name = django_filters.CharFilter(lookup_expr="icontains")
    nuit = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Employer
        fields = ["status", "sector", "company_name", "nuit"]

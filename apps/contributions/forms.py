from django import forms
from .models import Contribution


class ContributionCreateForm(forms.ModelForm):
    """Formulário de criação de contribuição."""

    class Meta:
        model = Contribution
        fields = ["affiliate", "employer", "period_year", "period_month", "salary_base", "notes"]
        widgets = {
            "affiliate": forms.Select(attrs={"class": "w-full border rounded px-3 py-2 text-sm"}),
            "employer": forms.Select(attrs={"class": "w-full border rounded px-3 py-2 text-sm"}),
            "period_year": forms.NumberInput(attrs={
                "class": "w-full border rounded px-3 py-2 text-sm",
                "min": 2000,
                "max": 2100,
            }),
            "period_month": forms.NumberInput(attrs={
                "class": "w-full border rounded px-3 py-2 text-sm",
                "min": 1,
                "max": 12,
            }),
            "salary_base": forms.NumberInput(attrs={
                "class": "w-full border rounded px-3 py-2 text-sm",
                "step": "0.01",
                "hx-post": "/portal/employer/contributions/calculate/",
                "hx-trigger": "change",
                "hx-target": "#calculation-result",
                "hx-include": "closest form",
                "hx-swap": "innerHTML",
            }),
            "notes": forms.Textarea(attrs={"class": "w-full border rounded px-3 py-2 text-sm", "rows": 2}),
        }

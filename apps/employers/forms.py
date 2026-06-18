from django import forms
from .models import Employer


class EmployerCreateForm(forms.ModelForm):
    """Formulário para criação de empregador."""

    class Meta:
        model = Employer
        fields = ["company_name", "nuit", "sector", "address", "phone", "email"]
        widgets = {
            "company_name": forms.TextInput(attrs={"class": "w-full border rounded px-3 py-2 text-sm"}),
            "nuit": forms.TextInput(attrs={"class": "w-full border rounded px-3 py-2 text-sm", "placeholder": "000000000"}),
            "sector": forms.Select(attrs={"class": "w-full border rounded px-3 py-2 text-sm"}),
            "address": forms.Textarea(attrs={"class": "w-full border rounded px-3 py-2 text-sm", "rows": 3}),
            "phone": forms.TextInput(attrs={"class": "w-full border rounded px-3 py-2 text-sm", "placeholder": "+245 XXX XXXX"}),
            "email": forms.EmailInput(attrs={"class": "w-full border rounded px-3 py-2 text-sm"}),
        }

from django import forms
from .models import Affiliate


class AffiliateCreateForm(forms.ModelForm):
    """Formulário para criação de afiliado + conta de utilizador associada."""

    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "w-full border rounded px-3 py-2 text-sm", "placeholder": "email@exemplo.com"}),
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"class": "w-full border rounded px-3 py-2 text-sm"}),
        min_length=10,
    )
    password_confirm = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(attrs={"class": "w-full border rounded px-3 py-2 text-sm"}),
    )

    class Meta:
        model = Affiliate
        fields = ["full_name", "birth_date", "gender", "nationality", "address", "phone"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "w-full border rounded px-3 py-2 text-sm"}),
            "birth_date": forms.DateInput(attrs={"class": "w-full border rounded px-3 py-2 text-sm", "type": "date"}),
            "gender": forms.Select(attrs={"class": "w-full border rounded px-3 py-2 text-sm"}),
            "nationality": forms.TextInput(attrs={"class": "w-full border rounded px-3 py-2 text-sm"}),
            "address": forms.Textarea(attrs={"class": "w-full border rounded px-3 py-2 text-sm", "rows": 3}),
            "phone": forms.TextInput(attrs={"class": "w-full border rounded px-3 py-2 text-sm", "placeholder": "+245 XXX XXXX"}),
        }

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password")
        p2 = cleaned.get("password_confirm")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("As senhas não coincidem.")
        return cleaned

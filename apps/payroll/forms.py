from django import forms

MONTH_NAMES_PT = [
    (1, "Janeiro"),
    (2, "Fevereiro"),
    (3, "Março"),
    (4, "Abril"),
    (5, "Maio"),
    (6, "Junho"),
    (7, "Julho"),
    (8, "Agosto"),
    (9, "Setembro"),
    (10, "Outubro"),
    (11, "Novembro"),
    (12, "Dezembro"),
]


class DeclarationCreateForm(forms.Form):
    period_year = forms.IntegerField(
        min_value=2000,
        max_value=2100,
        label="Ano",
        widget=forms.NumberInput(
            attrs={"class": "w-full border border-slate-300 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"}
        ),
    )
    period_month = forms.ChoiceField(
        choices=MONTH_NAMES_PT,
        label="Mês",
        widget=forms.Select(
            attrs={"class": "w-full border border-slate-300 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"}
        ),
    )


class AddDeclarationLineForm(forms.Form):
    niss = forms.CharField(
        max_length=15,
        label="NISS do trabalhador",
        widget=forms.TextInput(
            attrs={
                "class": "w-full border border-slate-300 rounded-xl px-3 py-2 text-sm",
                "placeholder": "Ex: 123456789012",
                "hx-get": "",  # set dynamically in template
                "hx-trigger": "keyup changed delay:400ms",
                "hx-target": "#niss-lookup-result",
                "autocomplete": "off",
            }
        ),
    )
    salary_base = forms.DecimalField(
        min_value=0,
        decimal_places=2,
        label="Salário base (XOF)",
        widget=forms.NumberInput(
            attrs={
                "class": "w-full border border-slate-300 rounded-xl px-3 py-2 text-sm",
                "placeholder": "0.00",
                "step": "0.01",
            }
        ),
    )
    notes = forms.CharField(
        max_length=200,
        required=False,
        label="Notas (opcional)",
        widget=forms.TextInput(
            attrs={
                "class": "w-full border border-slate-300 rounded-xl px-3 py-2 text-sm",
                "placeholder": "Observações...",
            }
        ),
    )


class AgentRejectForm(forms.Form):
    rejection_reason = forms.CharField(
        label="Motivo de rejeição",
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "w-full border border-slate-300 rounded-xl px-3 py-2 text-sm",
                "rows": 4,
                "placeholder": "Descreva o motivo da rejeição...",
            }
        ),
    )


class AgentValidateForm(forms.Form):
    validation_notes = forms.CharField(
        label="Notas de validação (opcional)",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "w-full border border-slate-300 rounded-xl px-3 py-2 text-sm",
                "rows": 3,
                "placeholder": "Observações sobre a validação...",
            }
        ),
    )

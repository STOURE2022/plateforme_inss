from datetime import date

from django import forms

from .models import (
    ControlAssessment,
    ControlDocument,
    ControlPayment,
    ControlStatus,
    ControlType,
    EmployerControl,
    VALID_TRANSITIONS,
)


class ControlCreateForm(forms.ModelForm):
    class Meta:
        model = EmployerControl
        fields = [
            "employer",
            "control_type",
            "period_from",
            "period_to",
            "assigned_agent",
            "findings_summary",
            "triggered_by_claim",
        ]
        widgets = {
            "employer": forms.Select(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                }
            ),
            "control_type": forms.Select(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                }
            ),
            "period_from": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                }
            ),
            "period_to": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                }
            ),
            "assigned_agent": forms.Select(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                }
            ),
            "findings_summary": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                    "placeholder": "Síntese inicial das constatações (opcional)...",
                }
            ),
            "triggered_by_claim": forms.Select(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                }
            ),
        }

    def clean(self):
        cleaned = super().clean()
        period_from = cleaned.get("period_from")
        period_to = cleaned.get("period_to")
        if period_from and period_to and period_to < period_from:
            raise forms.ValidationError(
                "A data de fim do período deve ser posterior à data de início."
            )
        return cleaned


class ControlAssessmentForm(forms.ModelForm):
    class Meta:
        model = ControlAssessment
        fields = [
            "period_year",
            "period_month",
            "declared_salary",
            "actual_salary",
            "penalty_rate",
            "notes",
        ]
        widgets = {
            "period_year": forms.NumberInput(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": str(date.today().year),
                    "min": "2000",
                    "max": "2099",
                }
            ),
            "period_month": forms.NumberInput(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": "1-12",
                    "min": "1",
                    "max": "12",
                }
            ),
            "declared_salary": forms.NumberInput(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "actual_salary": forms.NumberInput(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "penalty_rate": forms.NumberInput(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "step": "0.0001",
                    "min": "0",
                    "max": "1",
                }
            ),
            "notes": forms.TextInput(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": "Notas (opcional)",
                }
            ),
        }


class ControlStatusActionForm(forms.Form):
    new_status = forms.ChoiceField(
        choices=[],
        label="Novo Estado",
        widget=forms.Select(
            attrs={
                "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
            }
        ),
    )
    comment = forms.CharField(
        required=False,
        label="Comentário",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "Comentário para o histórico...",
            }
        ),
    )
    pv_date = forms.DateField(
        required=False,
        label="Data do PV",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
            }
        ),
    )
    notification_deadline = forms.DateField(
        required=False,
        label="Prazo de resposta do empregador",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
            }
        ),
    )
    dispute_reason = forms.CharField(
        required=False,
        label="Motivo da contestação",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "Descreva o motivo da contestação...",
            }
        ),
    )
    closure_notes = forms.CharField(
        required=False,
        label="Notas de encerramento",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                "placeholder": "Notas de encerramento (opcional)...",
            }
        ),
    )

    def __init__(self, current_status, *args, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = VALID_TRANSITIONS.get(current_status, [])
        status_display = dict(ControlStatus.choices)
        self.fields["new_status"].choices = [
            (s, status_display.get(s, s)) for s in allowed
        ]


class ControlPaymentForm(forms.ModelForm):
    class Meta:
        model = ControlPayment
        fields = ["amount", "payment_date", "payment_reference", "notes"]
        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "0.00",
                }
            ),
            "payment_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                }
            ),
            "payment_reference": forms.TextInput(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": "Referência de transferência bancária (opcional)",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "rows": 2,
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": "Notas (opcional)",
                }
            ),
        }


class ControlDocumentForm(forms.ModelForm):
    class Meta:
        model = ControlDocument
        fields = ["doc_type", "name", "file", "notes"]
        widgets = {
            "doc_type": forms.Select(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": "Nome descritivo do documento",
                }
            ),
            "notes": forms.TextInput(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500",
                    "placeholder": "Notas (opcional)",
                }
            ),
        }

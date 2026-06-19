from django import forms
from .models import BenefitRequest, BenefitDocument, BenefitRequestStatus


class BenefitRequestCreateForm(forms.ModelForm):
    """Form for citizens to create a new benefit request."""

    class Meta:
        model = BenefitRequest
        fields = ["benefit_type", "justification", "requested_start_date"]
        widgets = {
            "benefit_type": forms.Select(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                    "id": "id_benefit_type",
                }
            ),
            "justification": forms.Textarea(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                    "rows": 5,
                    "placeholder": "Descreva o motivo da sua solicitação...",
                }
            ),
            "requested_start_date": forms.DateInput(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                    "type": "date",
                }
            ),
        }
        labels = {
            "benefit_type": "Tipo de Prestação",
            "justification": "Justificação",
            "requested_start_date": "Data de Início Pretendida",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import BenefitType
        self.fields["benefit_type"].queryset = BenefitType.objects.filter(is_active=True).order_by("category", "name")


class BenefitDocumentUploadForm(forms.ModelForm):
    """Form for uploading a document to an existing benefit request."""

    class Meta:
        model = BenefitDocument
        fields = ["document_type", "name", "file", "notes"]
        widgets = {
            "document_type": forms.Select(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                    "placeholder": "Nome do documento",
                }
            ),
            "file": forms.FileInput(
                attrs={
                    "class": "block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100",
                }
            ),
            "notes": forms.TextInput(
                attrs={
                    "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                    "placeholder": "Notas opcionais",
                }
            ),
        }
        labels = {
            "document_type": "Tipo de Documento",
            "name": "Nome",
            "file": "Ficheiro",
            "notes": "Notas",
        }


class AgentReviewForm(forms.Form):
    """Form for agents to change the status of a benefit request."""

    ACTION_CHOICES = [
        ("start_review", "Iniciar Revisão"),
        ("approve", "Aprovar"),
        ("reject", "Rejeitar"),
        ("request_additional_docs", "Solicitar Documentos Adicionais"),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        label="Ação",
        widget=forms.Select(
            attrs={
                "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                "id": "id_action",
            }
        ),
    )
    decision_notes = forms.CharField(
        required=False,
        label="Notas de decisão",
        widget=forms.Textarea(
            attrs={
                "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                "rows": 4,
                "placeholder": "Notas sobre a decisão...",
            }
        ),
    )
    rejection_reason = forms.CharField(
        required=False,
        label="Motivo de rejeição",
        widget=forms.TextInput(
            attrs={
                "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                "placeholder": "Motivo obrigatório em caso de rejeição",
            }
        ),
    )
    approved_monthly_amount = forms.DecimalField(
        required=False,
        label="Montante mensal aprovado (XOF)",
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                "placeholder": "Deixe em branco para calcular automaticamente",
                "step": "0.01",
            }
        ),
    )
    comment = forms.CharField(
        required=False,
        label="Comentário para o histórico",
        widget=forms.TextInput(
            attrs={
                "class": "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                "placeholder": "Comentário opcional",
            }
        ),
    )

    def clean(self):
        cleaned = super().clean()
        action = cleaned.get("action")
        if action == "reject" and not cleaned.get("rejection_reason"):
            self.add_error("rejection_reason", "O motivo de rejeição é obrigatório.")
        return cleaned

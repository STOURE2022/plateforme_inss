from django import forms

from .models import Claim, ClaimDocument, ReclamationType, ClaimPriority

INPUT_CLASS = "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
TEXTAREA_CLASS = "w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
FILE_CLASS = "block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"


class ClaimCreateForm(forms.ModelForm):
    """Form for citizens/employers to file a new claim."""

    file = forms.FileField(
        required=False,
        label="Documento anexo (opcional)",
        widget=forms.FileInput(attrs={"class": FILE_CLASS}),
    )
    file_name = forms.CharField(
        required=False,
        label="Nome do documento",
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Nome do documento (se anexar ficheiro)",
        }),
    )

    class Meta:
        model = Claim
        fields = ["claim_type", "subject", "description"]
        widgets = {
            "claim_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "subject": forms.TextInput(attrs={
                "class": INPUT_CLASS,
                "placeholder": "Resumo breve da reclamação",
            }),
            "description": forms.Textarea(attrs={
                "class": TEXTAREA_CLASS,
                "rows": 6,
                "placeholder": "Descreva detalhadamente a sua reclamação...",
            }),
        }
        labels = {
            "claim_type": "Tipo de Reclamação",
            "subject": "Assunto",
            "description": "Descrição",
        }


class ClaimMessageForm(forms.Form):
    """Form for adding a message to a claim thread."""

    body = forms.CharField(
        label="Mensagem",
        widget=forms.Textarea(attrs={
            "class": TEXTAREA_CLASS,
            "rows": 4,
            "placeholder": "Escreva a sua mensagem...",
        }),
    )
    is_internal = forms.BooleanField(
        required=False,
        label="Nota interna (não visível ao cidadão)",
    )
    file = forms.FileField(
        required=False,
        label="Anexo (opcional)",
        widget=forms.FileInput(attrs={"class": FILE_CLASS}),
    )
    file_name = forms.CharField(
        required=False,
        label="Nome do documento",
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Nome do documento",
        }),
    )


class AgentClaimActionForm(forms.Form):
    """Form for agents to take action on a claim."""

    ACTION_CHOICES = [
        ("take_charge", "Tomar a cargo"),
        ("resolve", "Resolver"),
        ("reject", "Rejeitar"),
        ("request_info", "Solicitar informação adicional"),
        ("escalate", "Escalar"),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        label="Ação",
        widget=forms.Select(attrs={"class": INPUT_CLASS, "id": "id_action"}),
    )
    resolution_notes = forms.CharField(
        required=False,
        label="Notas de resolução",
        widget=forms.Textarea(attrs={
            "class": TEXTAREA_CLASS,
            "rows": 4,
            "placeholder": "Notas sobre a resolução...",
        }),
    )
    rejection_reason = forms.CharField(
        required=False,
        label="Motivo de rejeição",
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Motivo obrigatório em caso de rejeição",
        }),
    )
    comment = forms.CharField(
        required=False,
        label="Comentário para o histórico",
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASS,
            "placeholder": "Comentário opcional",
        }),
    )
    priority = forms.ChoiceField(
        choices=[("", "—")] + list(ClaimPriority.choices),
        required=False,
        label="Alterar prioridade",
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )

    def clean(self):
        cleaned = super().clean()
        action = cleaned.get("action")
        if action == "reject" and not cleaned.get("rejection_reason"):
            self.add_error("rejection_reason", "O motivo de rejeição é obrigatório.")
        if action == "resolve" and not cleaned.get("resolution_notes"):
            self.add_error("resolution_notes", "As notas de resolução são obrigatórias.")
        return cleaned

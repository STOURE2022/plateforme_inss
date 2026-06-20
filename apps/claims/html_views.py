from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView
from django.utils import timezone

from apps.accounts.mixins import CitizenRequiredMixin, AgentRequiredMixin
from apps.accounts.models import UserRole
from apps.notifications.services import NotificationService
from apps.notifications.models import NotificationType

from .models import (
    Claim,
    ClaimMessage,
    ClaimDocument,
    ClaimStatusHistory,
    ClaimStatus,
    ClaimPriority,
    VALID_TRANSITIONS,
)
from .forms import ClaimCreateForm, ClaimMessageForm, AgentClaimActionForm


# ---------------------------------------------------------------------------
# Citizen Portal Views
# ---------------------------------------------------------------------------

class CitizenClaimListView(CitizenRequiredMixin, TemplateView):
    template_name = "portal/citizen/claims/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = Claim.objects.filter(
            filed_by=self.request.user
        ).order_by("-submitted_at")

        status_filter = self.request.GET.get("status", "")
        if status_filter:
            qs = qs.filter(status=status_filter)

        ctx["claims"] = qs
        ctx["status_choices"] = ClaimStatus.choices
        ctx["selected_status"] = status_filter
        return ctx


class CitizenClaimDetailView(CitizenRequiredMixin, TemplateView):
    template_name = "portal/citizen/claims/detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        claim = get_object_or_404(
            Claim.objects.select_related(
                "filed_by", "affiliate", "employer", "assigned_to"
            ).prefetch_related("messages__author", "documents", "history__changed_by"),
            pk=kwargs["pk"],
            filed_by=self.request.user,
        )
        ctx["claim"] = claim
        ctx["messages_list"] = claim.messages.filter(is_internal=False).order_by("created_at")
        ctx["documents"] = claim.documents.all()
        ctx["history"] = claim.history.all()
        ctx["message_form"] = ClaimMessageForm()
        ctx["can_message"] = claim.status not in (ClaimStatus.RESOLVED, ClaimStatus.REJECTED)
        ctx["can_rate"] = (
            claim.status == ClaimStatus.RESOLVED
            and claim.satisfaction_rating is None
        )
        return ctx


class CitizenClaimCreateView(CitizenRequiredMixin, View):
    template_name = "portal/citizen/claims/create.html"

    def get(self, request, *args, **kwargs):
        form = ClaimCreateForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = ClaimCreateForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        affiliate = None
        try:
            affiliate = request.user.affiliate
        except Exception:
            pass

        claim = form.save(commit=False)
        claim.filed_by = request.user
        claim.affiliate = affiliate
        claim.status = ClaimStatus.OPEN
        claim.save()

        ClaimStatusHistory.objects.create(
            claim=claim,
            old_status="",
            new_status=ClaimStatus.OPEN,
            changed_by=request.user,
            comment="Reclamação submetida pelo cidadão.",
        )

        # Handle optional file attachment
        file = request.FILES.get("file")
        file_name = form.cleaned_data.get("file_name", "").strip()
        if file:
            ClaimDocument.objects.create(
                claim=claim,
                name=file_name or file.name,
                file=file,
                uploaded_by=request.user,
            )

        messages.success(
            request,
            f"Reclamação {claim.reference} submetida com sucesso. Será contactado em breve."
        )
        return redirect("citizen_claims:citizen_claim_detail", pk=claim.pk)


class CitizenClaimMessageView(CitizenRequiredMixin, View):
    """POST-only: citizen adds a message to their claim thread."""

    def post(self, request, pk, *args, **kwargs):
        claim = get_object_or_404(Claim, pk=pk, filed_by=request.user)

        if claim.status in (ClaimStatus.RESOLVED, ClaimStatus.REJECTED):
            messages.error(request, "Não é possível adicionar mensagens a reclamações encerradas.")
            return redirect("citizen_claims:citizen_claim_detail", pk=pk)

        form = ClaimMessageForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, "Erro ao enviar mensagem.")
            return redirect("citizen_claims:citizen_claim_detail", pk=pk)

        body = form.cleaned_data["body"].strip()
        if not body:
            messages.error(request, "A mensagem não pode estar vazia.")
            return redirect("citizen_claims:citizen_claim_detail", pk=pk)

        ClaimMessage.objects.create(
            claim=claim,
            author=request.user,
            body=body,
            is_internal=False,
        )

        # Handle file attachment
        file = request.FILES.get("file")
        file_name = form.cleaned_data.get("file_name", "").strip()
        if file:
            ClaimDocument.objects.create(
                claim=claim,
                name=file_name or file.name,
                file=file,
                uploaded_by=request.user,
            )

        # Auto-transition ADDITIONAL_INFO → UNDER_REVIEW
        if claim.status == ClaimStatus.ADDITIONAL_INFO:
            old_status = claim.status
            claim.status = ClaimStatus.UNDER_REVIEW
            claim.save(update_fields=["status", "updated_at"])
            ClaimStatusHistory.objects.create(
                claim=claim,
                old_status=old_status,
                new_status=ClaimStatus.UNDER_REVIEW,
                changed_by=request.user,
                comment="Cidadão forneceu informação adicional.",
            )
            messages.success(request, "Informação adicional enviada. A sua reclamação voltou a estar em análise.")
        else:
            messages.success(request, "Mensagem enviada com sucesso.")

        return redirect("citizen_claims:citizen_claim_detail", pk=pk)


class CitizenClaimRateView(CitizenRequiredMixin, View):
    """POST-only: citizen rates satisfaction on a resolved claim (1–5 stars)."""

    def post(self, request, pk, *args, **kwargs):
        claim = get_object_or_404(Claim, pk=pk, filed_by=request.user)

        if claim.status != ClaimStatus.RESOLVED:
            messages.error(request, "Só é possível avaliar reclamações resolvidas.")
            return redirect("citizen_claims:citizen_claim_detail", pk=pk)

        if claim.satisfaction_rating is not None:
            messages.error(request, "Já avaliou esta reclamação.")
            return redirect("citizen_claims:citizen_claim_detail", pk=pk)

        try:
            rating = int(request.POST.get("satisfaction_rating", 0))
            if not (1 <= rating <= 5):
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, "A avaliação deve ser entre 1 e 5 estrelas.")
            return redirect("citizen_claims:citizen_claim_detail", pk=pk)

        claim.satisfaction_rating = rating
        claim.satisfaction_comment = request.POST.get("satisfaction_comment", "")
        claim.save(update_fields=["satisfaction_rating", "satisfaction_comment", "updated_at"])

        messages.success(request, "Obrigado pela sua avaliação!")
        return redirect("citizen_claims:citizen_claim_detail", pk=pk)


# ---------------------------------------------------------------------------
# Agent Portal Views
# ---------------------------------------------------------------------------

class AgentClaimListView(AgentRequiredMixin, TemplateView):
    template_name = "portal/agent/claims/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.db.models import Q, Count

        qs = Claim.objects.select_related(
            "filed_by", "affiliate", "employer", "assigned_to"
        ).order_by("-submitted_at")

        # Filters
        status_filter = self.request.GET.get("status", "")
        type_filter = self.request.GET.get("claim_type", "")
        priority_filter = self.request.GET.get("priority", "")
        assigned_filter = self.request.GET.get("assigned", "")
        search_query = self.request.GET.get("q", "")
        date_from = self.request.GET.get("date_from", "")
        date_to = self.request.GET.get("date_to", "")

        if status_filter:
            qs = qs.filter(status=status_filter)
        if type_filter:
            qs = qs.filter(claim_type=type_filter)
        if priority_filter:
            qs = qs.filter(priority=priority_filter)
        if assigned_filter == "me":
            qs = qs.filter(assigned_to=self.request.user)
        elif assigned_filter == "unassigned":
            qs = qs.filter(assigned_to__isnull=True)
        if search_query:
            qs = qs.filter(
                Q(reference__icontains=search_query)
                | Q(subject__icontains=search_query)
                | Q(filed_by__email__icontains=search_query)
            )
        if date_from:
            qs = qs.filter(submitted_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(submitted_at__date__lte=date_to)

        # Status counts
        from .models import ReclamationType
        status_counts = {
            item["status"]: item["count"]
            for item in Claim.objects.values("status").annotate(count=Count("id"))
        }

        ctx["claims"] = qs
        ctx["status_choices"] = ClaimStatus.choices
        ctx["type_choices"] = ReclamationType.choices
        ctx["priority_choices"] = ClaimPriority.choices
        ctx["selected_status"] = status_filter
        ctx["selected_type"] = type_filter
        ctx["selected_priority"] = priority_filter
        ctx["assigned_filter"] = assigned_filter
        ctx["search_query"] = search_query
        ctx["date_from"] = date_from
        ctx["date_to"] = date_to
        ctx["status_counts"] = status_counts
        ctx["total_count"] = Claim.objects.count()
        ctx["open_count"] = Claim.objects.filter(status=ClaimStatus.OPEN).count()
        ctx["urgent_count"] = Claim.objects.filter(
            priority=ClaimPriority.URGENT,
            status__in=[ClaimStatus.OPEN, ClaimStatus.UNDER_REVIEW, ClaimStatus.ESCALATED]
        ).count()
        return ctx


class AgentClaimDetailView(AgentRequiredMixin, TemplateView):
    template_name = "portal/agent/claims/detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.accounts.models import User

        claim = get_object_or_404(
            Claim.objects.select_related(
                "filed_by", "affiliate", "employer", "assigned_to"
            ).prefetch_related("messages__author", "documents", "history__changed_by"),
            pk=kwargs["pk"],
        )

        ctx["claim"] = claim
        ctx["messages_list"] = claim.messages.all().order_by("created_at")
        ctx["documents"] = claim.documents.all()
        ctx["history"] = claim.history.all()
        ctx["message_form"] = ClaimMessageForm()
        ctx["action_form"] = AgentClaimActionForm()

        # Available transitions
        allowed = VALID_TRANSITIONS.get(claim.status, [])
        ctx["can_take_charge"] = ClaimStatus.UNDER_REVIEW in allowed and claim.status == ClaimStatus.OPEN
        ctx["can_resolve"] = ClaimStatus.RESOLVED in allowed
        ctx["can_reject"] = ClaimStatus.REJECTED in allowed
        ctx["can_request_info"] = ClaimStatus.ADDITIONAL_INFO in allowed
        ctx["can_escalate"] = ClaimStatus.ESCALATED in allowed

        # Agent list for assignment
        ctx["agents"] = User.objects.filter(role__in=["AGENT", "ADMIN"]).order_by("email")
        ctx["priority_choices"] = ClaimPriority.choices
        return ctx


class AgentClaimActionView(AgentRequiredMixin, View):
    """POST: agent takes a status-changing action on a claim."""

    def post(self, request, pk, *args, **kwargs):
        claim = get_object_or_404(Claim, pk=pk)
        form = AgentClaimActionForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Formulário inválido. Verifique os campos.")
            return redirect("agent_claims:agent_claim_detail", pk=pk)

        action = form.cleaned_data["action"]
        resolution_notes = form.cleaned_data.get("resolution_notes", "")
        rejection_reason = form.cleaned_data.get("rejection_reason", "")
        comment = form.cleaned_data.get("comment", "")
        priority = form.cleaned_data.get("priority", "")

        # Map action to target status
        action_map = {
            "take_charge": ClaimStatus.UNDER_REVIEW,
            "resolve": ClaimStatus.RESOLVED,
            "reject": ClaimStatus.REJECTED,
            "request_info": ClaimStatus.ADDITIONAL_INFO,
            "escalate": ClaimStatus.ESCALATED,
        }

        new_status = action_map.get(action)
        if not new_status:
            messages.error(request, "Ação inválida.")
            return redirect("agent_claims:agent_claim_detail", pk=pk)

        if not claim.can_transition_to(new_status):
            messages.error(
                request,
                f"Transição inválida: {claim.get_status_display()} → {dict(ClaimStatus.choices).get(new_status, new_status)}"
            )
            return redirect("agent_claims:agent_claim_detail", pk=pk)

        old_status = claim.status
        claim.status = new_status

        if new_status == ClaimStatus.UNDER_REVIEW and old_status == ClaimStatus.OPEN:
            claim.assigned_to = request.user
            claim.review_started_at = timezone.now()
        if new_status in (ClaimStatus.RESOLVED, ClaimStatus.REJECTED):
            claim.resolved_at = timezone.now()
        if new_status == ClaimStatus.RESOLVED:
            claim.resolution_notes = resolution_notes
        if new_status == ClaimStatus.REJECTED:
            claim.rejection_reason = rejection_reason

        # Update priority if changed
        if priority and priority != claim.priority:
            claim.priority = priority

        claim.save()

        ClaimStatusHistory.objects.create(
            claim=claim,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user,
            comment=comment or f"Ação: {action}",
        )

        # Notify filer
        self._notify_filer(claim, new_status)

        messages.success(
            request,
            f"Reclamação {claim.reference} atualizada: {claim.get_status_display()}"
        )
        return redirect("agent_claims:agent_claim_detail", pk=pk)

    def _notify_filer(self, claim, new_status):
        status_messages = {
            ClaimStatus.UNDER_REVIEW: (
                "Reclamação em análise",
                f"A sua reclamação {claim.reference} está a ser analisada por um agente INSS.",
                NotificationType.INFO,
            ),
            ClaimStatus.RESOLVED: (
                "Reclamação resolvida",
                f"A sua reclamação {claim.reference} foi resolvida. {claim.resolution_notes}",
                NotificationType.SUCCESS,
            ),
            ClaimStatus.REJECTED: (
                "Reclamação rejeitada",
                f"A sua reclamação {claim.reference} foi rejeitada. Motivo: {claim.rejection_reason}",
                NotificationType.ERROR,
            ),
            ClaimStatus.ADDITIONAL_INFO: (
                "Informação adicional solicitada",
                f"O agente INSS solicita informação adicional para a sua reclamação {claim.reference}.",
                NotificationType.WARNING,
            ),
            ClaimStatus.ESCALATED: (
                "Reclamação escalada",
                f"A sua reclamação {claim.reference} foi escalada para supervisão.",
                NotificationType.INFO,
            ),
        }
        if new_status in status_messages:
            title, message, notif_type = status_messages[new_status]
            NotificationService.notify(
                recipient=claim.filed_by,
                title=title,
                message=message,
                notification_type=notif_type,
                resource=claim,
                resource_url=f"/portal/citizen/claims/{claim.pk}/",
            )


class AgentClaimMessageView(AgentRequiredMixin, View):
    """POST: agent adds a message (public or internal) to a claim thread."""

    def post(self, request, pk, *args, **kwargs):
        claim = get_object_or_404(Claim, pk=pk)
        form = ClaimMessageForm(request.POST, request.FILES)

        if not form.is_valid():
            messages.error(request, "Erro ao enviar mensagem.")
            return redirect("agent_claims:agent_claim_detail", pk=pk)

        body = form.cleaned_data["body"].strip()
        is_internal = form.cleaned_data.get("is_internal", False)

        if not body:
            messages.error(request, "A mensagem não pode estar vazia.")
            return redirect("agent_claims:agent_claim_detail", pk=pk)

        ClaimMessage.objects.create(
            claim=claim,
            author=request.user,
            body=body,
            is_internal=is_internal,
        )

        # Handle file attachment
        file = request.FILES.get("file")
        file_name = form.cleaned_data.get("file_name", "").strip()
        if file:
            ClaimDocument.objects.create(
                claim=claim,
                name=file_name or file.name,
                file=file,
                uploaded_by=request.user,
            )

        # Notify filer if public message
        if not is_internal:
            NotificationService.notify(
                recipient=claim.filed_by,
                title="Nova mensagem na reclamação",
                message=f"O agente INSS adicionou uma mensagem à sua reclamação {claim.reference}.",
                notification_type=NotificationType.INFO,
                resource=claim,
                resource_url=f"/portal/citizen/claims/{claim.pk}/",
            )

        note_type = "interna" if is_internal else "pública"
        messages.success(request, f"Mensagem {note_type} adicionada com sucesso.")
        return redirect("agent_claims:agent_claim_detail", pk=pk)

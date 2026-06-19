from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView, CreateView

from apps.accounts.mixins import CitizenRequiredMixin, AgentRequiredMixin
from apps.notifications.services import NotificationService
from apps.notifications.models import NotificationType

from .models import (
    BenefitRequest,
    BenefitRequestStatus,
    BenefitStatusHistory,
    BenefitType,
)
from .forms import BenefitRequestCreateForm, BenefitDocumentUploadForm, AgentReviewForm


# ---------------------------------------------------------------------------
# Citizen Portal Views
# ---------------------------------------------------------------------------

class CitizenBenefitListView(CitizenRequiredMixin, TemplateView):
    template_name = "portal/citizen/benefits/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            affiliate = self.request.user.affiliate
        except Exception:
            ctx["benefit_requests"] = []
            return ctx

        qs = BenefitRequest.objects.filter(
            affiliate=affiliate
        ).select_related("benefit_type").order_by("-created_at")

        # Status filter
        status_filter = self.request.GET.get("status", "")
        if status_filter:
            qs = qs.filter(status=status_filter)

        ctx["benefit_requests"] = qs
        ctx["status_choices"] = BenefitRequestStatus.choices
        ctx["selected_status"] = status_filter
        ctx["affiliate"] = affiliate
        return ctx


class CitizenBenefitDetailView(CitizenRequiredMixin, TemplateView):
    template_name = "portal/citizen/benefits/detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            affiliate = self.request.user.affiliate
        except Exception:
            ctx["request_obj"] = None
            return ctx

        request_obj = get_object_or_404(
            BenefitRequest,
            pk=kwargs["pk"],
            affiliate=affiliate,
        )

        ctx["request_obj"] = request_obj
        ctx["documents"] = request_obj.documents.all()
        ctx["payments"] = request_obj.payments.all()
        ctx["history"] = request_obj.history.all()
        ctx["upload_form"] = BenefitDocumentUploadForm()

        # Only allow doc upload in certain statuses
        ctx["can_upload_docs"] = request_obj.status in (
            BenefitRequestStatus.DRAFT,
            BenefitRequestStatus.SUBMITTED,
            BenefitRequestStatus.ADDITIONAL_DOCS,
        )
        ctx["can_submit"] = request_obj.status == BenefitRequestStatus.DRAFT
        return ctx


class CitizenBenefitCreateView(CitizenRequiredMixin, View):
    template_name = "portal/citizen/benefits/create.html"

    def get(self, request, *args, **kwargs):
        form = BenefitRequestCreateForm()
        benefit_types = BenefitType.objects.filter(is_active=True).order_by("category", "name")
        return self._render(request, form, benefit_types)

    def post(self, request, *args, **kwargs):
        form = BenefitRequestCreateForm(request.POST)
        benefit_types = BenefitType.objects.filter(is_active=True).order_by("category", "name")

        if not form.is_valid():
            return self._render(request, form, benefit_types)

        try:
            affiliate = request.user.affiliate
        except Exception:
            messages.error(request, "Precisa de um perfil de afiliado para solicitar uma prestação.")
            return redirect("citizen-dashboard")

        benefit_request = form.save(commit=False)
        benefit_request.affiliate = affiliate
        benefit_request.applicant_name = affiliate.full_name
        benefit_request.applicant_niss = affiliate.niss
        benefit_request.applicant_birth_date = affiliate.birth_date
        benefit_request.status = BenefitRequestStatus.DRAFT
        benefit_request.created_by = request.user
        benefit_request.save()

        BenefitStatusHistory.objects.create(
            request=benefit_request,
            old_status="",
            new_status=BenefitRequestStatus.DRAFT,
            changed_by=request.user,
            comment="Solicitação criada.",
        )

        messages.success(
            request,
            f"Solicitação {benefit_request.reference} criada com sucesso. Pode agora submeter."
        )
        return redirect("citizen_benefits:citizen_benefit_detail", pk=benefit_request.pk)

    def _render(self, request, form, benefit_types):
        from django.shortcuts import render
        return render(request, self.template_name, {
            "form": form,
            "benefit_types": benefit_types,
        })


class CitizenBenefitSubmitView(CitizenRequiredMixin, View):
    """POST-only view to submit a DRAFT request."""

    def post(self, request, pk, *args, **kwargs):
        try:
            affiliate = request.user.affiliate
        except Exception:
            messages.error(request, "Perfil de afiliado não encontrado.")
            return redirect("citizen_benefits:citizen_benefit_list")

        benefit_request = get_object_or_404(BenefitRequest, pk=pk, affiliate=affiliate)

        if benefit_request.status != BenefitRequestStatus.DRAFT:
            messages.error(request, "Só é possível submeter solicitações em rascunho.")
            return redirect("citizen_benefits:citizen_benefit_detail", pk=pk)

        from django.utils import timezone
        old_status = benefit_request.status
        benefit_request.status = BenefitRequestStatus.SUBMITTED
        benefit_request.submitted_at = timezone.now()
        benefit_request.save(update_fields=["status", "submitted_at", "updated_at"])

        benefit_request.compute_eligibility()

        BenefitStatusHistory.objects.create(
            request=benefit_request,
            old_status=old_status,
            new_status=BenefitRequestStatus.SUBMITTED,
            changed_by=request.user,
            comment="Submetida pelo requerente.",
        )

        NotificationService.notify(
            recipient=request.user,
            title="Solicitação submetida",
            message=f"A solicitação {benefit_request.reference} foi submetida com sucesso.",
            notification_type=NotificationType.SUCCESS,
            resource=benefit_request,
            resource_url=f"/portal/citizen/benefits/{benefit_request.pk}/",
        )

        messages.success(request, f"Solicitação {benefit_request.reference} submetida com sucesso.")
        return redirect("citizen_benefits:citizen_benefit_detail", pk=pk)


class CitizenBenefitDocumentUploadView(CitizenRequiredMixin, View):
    """Upload documents to an existing benefit request."""

    def post(self, request, pk, *args, **kwargs):
        try:
            affiliate = request.user.affiliate
        except Exception:
            messages.error(request, "Perfil de afiliado não encontrado.")
            return redirect("citizen_benefits:citizen_benefit_list")

        benefit_request = get_object_or_404(BenefitRequest, pk=pk, affiliate=affiliate)

        if benefit_request.status not in (
            BenefitRequestStatus.DRAFT,
            BenefitRequestStatus.SUBMITTED,
            BenefitRequestStatus.ADDITIONAL_DOCS,
        ):
            messages.error(request, "Não é possível carregar documentos neste estado.")
            return redirect("citizen_benefits:citizen_benefit_detail", pk=pk)

        form = BenefitDocumentUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, "Erro ao carregar documento. Verifique os campos.")
            return redirect("citizen_benefits:citizen_benefit_detail", pk=pk)

        doc = form.save(commit=False)
        doc.request = benefit_request
        doc.uploaded_by = request.user
        doc.save()

        messages.success(request, f"Documento '{doc.name}' carregado com sucesso.")
        return redirect("citizen_benefits:citizen_benefit_detail", pk=pk)


# ---------------------------------------------------------------------------
# Agent Portal Views
# ---------------------------------------------------------------------------

class AgentBenefitListView(AgentRequiredMixin, TemplateView):
    template_name = "portal/agent/benefits/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        qs = BenefitRequest.objects.select_related(
            "affiliate", "benefit_type", "reviewed_by"
        ).order_by("-created_at")

        # Filters
        status_filter = self.request.GET.get("status", "")
        category_filter = self.request.GET.get("category", "")
        search_query = self.request.GET.get("q", "")
        date_from = self.request.GET.get("date_from", "")
        date_to = self.request.GET.get("date_to", "")

        if status_filter:
            qs = qs.filter(status=status_filter)
        if category_filter:
            qs = qs.filter(benefit_type__category=category_filter)
        if search_query:
            from django.db.models import Q
            qs = qs.filter(
                Q(applicant_name__icontains=search_query)
                | Q(applicant_niss__icontains=search_query)
                | Q(reference__icontains=search_query)
            )
        if date_from:
            qs = qs.filter(submitted_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(submitted_at__date__lte=date_to)

        # Status counts
        from django.db.models import Count
        status_counts = {
            item["status"]: item["count"]
            for item in BenefitRequest.objects.values("status").annotate(count=Count("id"))
        }

        from .models import BenefitCategory
        ctx["benefit_requests"] = qs
        ctx["status_choices"] = BenefitRequestStatus.choices
        ctx["category_choices"] = BenefitCategory.choices
        ctx["selected_status"] = status_filter
        ctx["selected_category"] = category_filter
        ctx["search_query"] = search_query
        ctx["date_from"] = date_from
        ctx["date_to"] = date_to
        ctx["status_counts"] = status_counts
        ctx["total_count"] = BenefitRequest.objects.count()
        ctx["pending_count"] = BenefitRequest.objects.filter(
            status__in=[BenefitRequestStatus.SUBMITTED, BenefitRequestStatus.UNDER_REVIEW]
        ).count()
        return ctx


class AgentBenefitDetailView(AgentRequiredMixin, TemplateView):
    template_name = "portal/agent/benefits/detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        request_obj = get_object_or_404(
            BenefitRequest.objects.select_related(
                "affiliate", "benefit_type", "reviewed_by", "created_by"
            ).prefetch_related("documents", "payments", "history__changed_by"),
            pk=kwargs["pk"],
        )

        ctx["request_obj"] = request_obj
        ctx["documents"] = request_obj.documents.all()
        ctx["payments"] = request_obj.payments.all()
        ctx["history"] = request_obj.history.all()

        # Determine available actions
        ctx["can_start_review"] = request_obj.status == BenefitRequestStatus.SUBMITTED
        ctx["can_approve"] = request_obj.status in (
            BenefitRequestStatus.UNDER_REVIEW,
            BenefitRequestStatus.ADDITIONAL_DOCS,
        )
        ctx["can_reject"] = request_obj.status in (
            BenefitRequestStatus.SUBMITTED,
            BenefitRequestStatus.UNDER_REVIEW,
            BenefitRequestStatus.ADDITIONAL_DOCS,
        )
        ctx["can_request_docs"] = request_obj.status == BenefitRequestStatus.UNDER_REVIEW
        return ctx


class AgentBenefitReviewView(AgentRequiredMixin, View):
    template_name = "portal/agent/benefits/review.html"

    def get(self, request, pk, *args, **kwargs):
        from django.shortcuts import render
        request_obj = get_object_or_404(BenefitRequest, pk=pk)
        form = AgentReviewForm()
        return render(request, self.template_name, {
            "request_obj": request_obj,
            "form": form,
        })

    def post(self, request, pk, *args, **kwargs):
        from django.shortcuts import render
        from django.utils import timezone

        request_obj = get_object_or_404(BenefitRequest, pk=pk)
        form = AgentReviewForm(request.POST)

        if not form.is_valid():
            return render(request, self.template_name, {
                "request_obj": request_obj,
                "form": form,
            })

        action = form.cleaned_data["action"]
        decision_notes = form.cleaned_data.get("decision_notes", "")
        rejection_reason = form.cleaned_data.get("rejection_reason", "")
        approved_monthly_amount = form.cleaned_data.get("approved_monthly_amount")
        comment = form.cleaned_data.get("comment", "")

        old_status = request_obj.status

        if action == "start_review":
            if request_obj.status != BenefitRequestStatus.SUBMITTED:
                messages.error(request, "Não é possível iniciar revisão neste estado.")
                return redirect("agent_benefits:agent_benefit_detail", pk=pk)

            request_obj.status = BenefitRequestStatus.UNDER_REVIEW
            request_obj.reviewed_by = request.user
            request_obj.review_started_at = timezone.now()
            request_obj.save(update_fields=["status", "reviewed_by", "review_started_at", "updated_at"])
            new_status = BenefitRequestStatus.UNDER_REVIEW
            comment = comment or f"Revisão iniciada por {request.user.email}."

            NotificationService.notify(
                recipient=request_obj.affiliate.user,
                title="Solicitação em revisão",
                message=f"A sua solicitação {request_obj.reference} está em revisão.",
                notification_type=NotificationType.INFO,
                resource=request_obj,
                resource_url=f"/portal/citizen/benefits/{request_obj.pk}/",
            )

        elif action == "approve":
            if request_obj.status not in (BenefitRequestStatus.UNDER_REVIEW, BenefitRequestStatus.ADDITIONAL_DOCS):
                messages.error(request, "Não é possível aprovar neste estado.")
                return redirect("agent_benefits:agent_benefit_detail", pk=pk)

            request_obj.status = BenefitRequestStatus.APPROVED
            request_obj.decided_at = timezone.now()
            request_obj.decision_notes = decision_notes

            if approved_monthly_amount is not None:
                request_obj.approved_monthly_amount = approved_monthly_amount
            else:
                request_obj.compute_eligibility()

            request_obj.save(update_fields=["status", "decided_at", "decision_notes", "approved_monthly_amount", "updated_at"])
            new_status = BenefitRequestStatus.APPROVED
            comment = comment or decision_notes or "Aprovada."

            NotificationService.notify(
                recipient=request_obj.affiliate.user,
                title="Solicitação aprovada",
                message=(
                    f"A sua solicitação {request_obj.reference} foi aprovada. "
                    f"Montante: {request_obj.approved_monthly_amount} XOF/mês."
                ),
                notification_type=NotificationType.SUCCESS,
                resource=request_obj,
                resource_url=f"/portal/citizen/benefits/{request_obj.pk}/",
            )

        elif action == "reject":
            if request_obj.status not in (
                BenefitRequestStatus.SUBMITTED,
                BenefitRequestStatus.UNDER_REVIEW,
                BenefitRequestStatus.ADDITIONAL_DOCS,
            ):
                messages.error(request, "Não é possível rejeitar neste estado.")
                return redirect("agent_benefits:agent_benefit_detail", pk=pk)

            request_obj.status = BenefitRequestStatus.REJECTED
            request_obj.decided_at = timezone.now()
            request_obj.decision_notes = decision_notes
            request_obj.rejection_reason = rejection_reason
            request_obj.save(update_fields=["status", "decided_at", "decision_notes", "rejection_reason", "updated_at"])
            new_status = BenefitRequestStatus.REJECTED
            comment = comment or f"Rejeitada: {rejection_reason}"

            NotificationService.notify(
                recipient=request_obj.affiliate.user,
                title="Solicitação rejeitada",
                message=(
                    f"A sua solicitação {request_obj.reference} foi rejeitada. "
                    f"Motivo: {rejection_reason}."
                ),
                notification_type=NotificationType.ERROR,
                resource=request_obj,
                resource_url=f"/portal/citizen/benefits/{request_obj.pk}/",
            )

        elif action == "request_additional_docs":
            if request_obj.status != BenefitRequestStatus.UNDER_REVIEW:
                messages.error(request, "Não é possível solicitar documentos adicionais neste estado.")
                return redirect("agent_benefits:agent_benefit_detail", pk=pk)

            request_obj.status = BenefitRequestStatus.ADDITIONAL_DOCS
            request_obj.save(update_fields=["status", "updated_at"])
            new_status = BenefitRequestStatus.ADDITIONAL_DOCS
            comment = comment or "Documentos adicionais solicitados."

            NotificationService.notify(
                recipient=request_obj.affiliate.user,
                title="Documentos adicionais necessários",
                message=(
                    f"São necessários documentos adicionais para a solicitação {request_obj.reference}. "
                    f"Por favor, carregue os documentos solicitados."
                ),
                notification_type=NotificationType.WARNING,
                resource=request_obj,
                resource_url=f"/portal/citizen/benefits/{request_obj.pk}/documents/",
            )
        else:
            messages.error(request, "Ação inválida.")
            return redirect("agent_benefits:agent_benefit_detail", pk=pk)

        BenefitStatusHistory.objects.create(
            request=request_obj,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user,
            comment=comment,
        )

        messages.success(request, f"Estado da solicitação {request_obj.reference} atualizado com sucesso.")
        return redirect("agent_benefits:agent_benefit_detail", pk=pk)

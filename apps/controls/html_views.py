import datetime

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.mixins import AgentRequiredMixin
from apps.notifications.models import NotificationType
from apps.notifications.services import NotificationService

from .forms import (
    ControlAssessmentForm,
    ControlCreateForm,
    ControlDocumentForm,
    ControlPaymentForm,
    ControlStatusActionForm,
)
from .models import (
    ControlPayment,
    ControlStatus,
    ControlStatusHistory,
    EmployerControl,
    VALID_TRANSITIONS,
)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

class ControlListView(AgentRequiredMixin, TemplateView):
    template_name = "portal/agent/controls/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.db.models import Count, Q

        qs = EmployerControl.objects.select_related(
            "employer", "assigned_agent"
        ).order_by("-created_at")

        # Filters
        status_filter = self.request.GET.get("status", "")
        type_filter = self.request.GET.get("control_type", "")
        search_query = self.request.GET.get("q", "")
        assigned_filter = self.request.GET.get("assigned", "")

        if status_filter:
            qs = qs.filter(status=status_filter)
        if type_filter:
            qs = qs.filter(control_type=type_filter)
        if assigned_filter == "me":
            qs = qs.filter(assigned_agent=self.request.user)
        if search_query:
            qs = qs.filter(
                Q(reference__icontains=search_query)
                | Q(employer__company_name__icontains=search_query)
                | Q(employer__nuit__icontains=search_query)
            )

        # Status counts
        status_counts = {
            item["status"]: item["count"]
            for item in EmployerControl.objects.values("status").annotate(count=Count("id"))
        }

        today = datetime.date.today()

        ctx["controls"] = qs
        ctx["status_choices"] = ControlStatus.choices
        ctx["type_choices"] = [
            ("ROUTINE", "Contrôle de Routine"),
            ("TARGETED", "Contrôle Ciblé"),
            ("COMPLAINT", "Déclenché par Réclamation"),
            ("CROSS_CHECK", "Recoupement Fiscal"),
        ]
        ctx["selected_status"] = status_filter
        ctx["selected_type"] = type_filter
        ctx["search_query"] = search_query
        ctx["assigned_filter"] = assigned_filter
        ctx["status_counts"] = status_counts
        ctx["today"] = today
        ctx["total_count"] = EmployerControl.objects.count()
        ctx["active_count"] = EmployerControl.objects.filter(
            status__in=[
                ControlStatus.PLANNED,
                ControlStatus.IN_PROGRESS,
                ControlStatus.PV_DRAFTED,
                ControlStatus.NOTIFIED,
                ControlStatus.DISPUTED,
            ]
        ).count()
        return ctx


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

class ControlCreateView(AgentRequiredMixin, View):
    template_name = "portal/agent/controls/create.html"

    def get(self, request, *args, **kwargs):
        from apps.accounts.models import User

        form = ControlCreateForm(initial={"assigned_agent": request.user})
        form.fields["assigned_agent"].queryset = User.objects.filter(
            role__in=["AGENT", "ADMIN"]
        ).order_by("email")
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        from apps.accounts.models import User

        form = ControlCreateForm(request.POST)
        form.fields["assigned_agent"].queryset = User.objects.filter(
            role__in=["AGENT", "ADMIN"]
        ).order_by("email")

        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        ctrl = form.save(commit=False)
        ctrl.created_by = request.user
        ctrl.status = ControlStatus.PLANNED
        ctrl.save()

        ControlStatusHistory.objects.create(
            control=ctrl,
            old_status="",
            new_status=ControlStatus.PLANNED,
            changed_by=request.user,
            comment="Controlo criado.",
        )

        messages.success(
            request,
            f"Controlo {ctrl.reference} criado com sucesso.",
        )
        return redirect("agent-control-detail", pk=ctrl.pk)


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

class ControlDetailView(AgentRequiredMixin, TemplateView):
    template_name = "portal/agent/controls/detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctrl = get_object_or_404(
            EmployerControl.objects.select_related(
                "employer", "assigned_agent", "created_by", "triggered_by_claim"
            ).prefetch_related(
                "assessments",
                "documents__uploaded_by",
                "payments__recorded_by",
                "history__changed_by",
            ),
            pk=kwargs["pk"],
        )
        ctx["control"] = ctrl
        ctx["assessments"] = ctrl.assessments.all()
        ctx["documents"] = ctrl.documents.all()
        ctx["payments"] = ctrl.payments.all()
        ctx["history"] = ctrl.history.all()

        ctx["assessment_form"] = ControlAssessmentForm()
        ctx["payment_form"] = ControlPaymentForm(
            initial={"payment_date": datetime.date.today()}
        )
        ctx["document_form"] = ControlDocumentForm()

        allowed = VALID_TRANSITIONS.get(ctrl.status, [])
        ctx["allowed_transitions"] = allowed
        ctx["action_form"] = ControlStatusActionForm(current_status=ctrl.status)

        ctx["can_add_assessment"] = ctrl.status in (
            ControlStatus.IN_PROGRESS,
            ControlStatus.PV_DRAFTED,
        )
        ctx["can_add_payment"] = ctrl.status in (
            ControlStatus.NOTIFIED,
            ControlStatus.DISPUTED,
            ControlStatus.SETTLED,
        )
        ctx["today"] = datetime.date.today()
        return ctx


# ---------------------------------------------------------------------------
# Assessment add / remove (HTMX)
# ---------------------------------------------------------------------------

class ControlAddAssessmentView(AgentRequiredMixin, View):
    """POST: add an assessment line and recompute totals."""

    def post(self, request, pk, *args, **kwargs):
        ctrl = get_object_or_404(EmployerControl, pk=pk)

        if ctrl.status not in (ControlStatus.IN_PROGRESS, ControlStatus.PV_DRAFTED):
            messages.error(
                request,
                "Só é possível adicionar linhas de redressamento com o controlo Em Curso ou PV Redigido.",
            )
            return redirect("agent-control-detail", pk=pk)

        form = ControlAssessmentForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Formulário de avaliação inválido. Verifique os campos.")
            return redirect("agent-control-detail", pk=pk)

        assessment = form.save(commit=False)
        assessment.control = ctrl
        try:
            assessment.save()
        except Exception:
            messages.error(
                request,
                f"Já existe uma linha para {assessment.period_month:02d}/{assessment.period_year}.",
            )
            return redirect("agent-control-detail", pk=pk)

        ctrl.recompute_totals()

        if request.headers.get("HX-Request"):
            assessments = ctrl.assessments.all()
            return render(
                request,
                "portal/agent/controls/partials/assessments_table.html",
                {"control": ctrl, "assessments": assessments},
            )

        messages.success(
            request,
            f"Linha {assessment.period_month:02d}/{assessment.period_year} adicionada.",
        )
        return redirect("agent-control-detail", pk=pk)


class ControlRemoveAssessmentView(AgentRequiredMixin, View):
    """POST: remove an assessment line and recompute totals."""

    def post(self, request, pk, apk, *args, **kwargs):
        ctrl = get_object_or_404(EmployerControl, pk=pk)

        if ctrl.status not in (ControlStatus.IN_PROGRESS, ControlStatus.PV_DRAFTED):
            messages.error(request, "Não é possível remover linhas neste estado.")
            return redirect("agent-control-detail", pk=pk)

        from .models import ControlAssessment

        assessment = get_object_or_404(ControlAssessment, pk=apk, control=ctrl)
        label = f"{assessment.period_month:02d}/{assessment.period_year}"
        assessment.delete()
        ctrl.recompute_totals()

        if request.headers.get("HX-Request"):
            assessments = ctrl.assessments.all()
            return render(
                request,
                "portal/agent/controls/partials/assessments_table.html",
                {"control": ctrl, "assessments": assessments},
            )

        messages.success(request, f"Linha {label} removida.")
        return redirect("agent-control-detail", pk=pk)


# ---------------------------------------------------------------------------
# Status Action
# ---------------------------------------------------------------------------

class ControlStatusActionView(AgentRequiredMixin, View):
    """POST: change status, log history, send notification if NOTIFIED."""

    def post(self, request, pk, *args, **kwargs):
        ctrl = get_object_or_404(EmployerControl, pk=pk)
        form = ControlStatusActionForm(ctrl.status, request.POST)

        if not form.is_valid():
            messages.error(request, "Formulário de ação inválido.")
            return redirect("agent-control-detail", pk=pk)

        new_status = form.cleaned_data["new_status"]
        comment = form.cleaned_data.get("comment", "")
        pv_date = form.cleaned_data.get("pv_date")
        notification_deadline = form.cleaned_data.get("notification_deadline")
        dispute_reason = form.cleaned_data.get("dispute_reason", "")
        closure_notes = form.cleaned_data.get("closure_notes", "")

        if not ctrl.can_transition_to(new_status):
            messages.error(
                request,
                f"Transição inválida: {ctrl.get_status_display()} → {dict(ControlStatus.choices).get(new_status, new_status)}",
            )
            return redirect("agent-control-detail", pk=pk)

        old_status = ctrl.status
        ctrl.status = new_status

        # Status-specific side effects
        if new_status == ControlStatus.PV_DRAFTED:
            if pv_date:
                ctrl.pv_date = pv_date
            elif not ctrl.pv_date:
                ctrl.pv_date = datetime.date.today()

        elif new_status == ControlStatus.NOTIFIED:
            ctrl.notified_at = timezone.now()
            ref_date = ctrl.pv_date or datetime.date.today()
            ctrl.notification_deadline = (
                notification_deadline or ref_date + datetime.timedelta(days=30)
            )

        elif new_status == ControlStatus.DISPUTED:
            ctrl.dispute_filed_at = timezone.now()
            if dispute_reason:
                ctrl.dispute_reason = dispute_reason

        elif new_status == ControlStatus.CLOSED:
            ctrl.closed_at = timezone.now()
            if closure_notes:
                ctrl.closure_notes = closure_notes

        ctrl.save()

        ControlStatusHistory.objects.create(
            control=ctrl,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user,
            comment=comment or f"Transição: {old_status} → {new_status}",
        )

        # Notify employer at NOTIFIED status
        if new_status == ControlStatus.NOTIFIED:
            self._notify_employer(ctrl)

        messages.success(
            request,
            f"Controlo {ctrl.reference} atualizado: {ctrl.get_status_display()}",
        )
        return redirect("agent-control-detail", pk=pk)

    def _notify_employer(self, ctrl: EmployerControl) -> None:
        try:
            recipient = ctrl.employer.user
            NotificationService.notify(
                recipient=recipient,
                title="Notificação de Redressamento INSS",
                message=(
                    f"O INSS notificou a empresa {ctrl.employer.company_name} de um redressamento "
                    f"de {ctrl.total_due:,.2f} XOF. Ref: {ctrl.reference}. "
                    f"Prazo de resposta: {ctrl.notification_deadline}."
                ),
                notification_type=NotificationType.WARNING,
                resource=ctrl,
                resource_url=f"/portal/agent/controls/{ctrl.pk}/",
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

class ControlAddPaymentView(AgentRequiredMixin, View):
    """POST: add a payment record and recompute totals."""

    def post(self, request, pk, *args, **kwargs):
        ctrl = get_object_or_404(EmployerControl, pk=pk)
        form = ControlPaymentForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Formulário de pagamento inválido.")
            return redirect("agent-control-detail", pk=pk)

        payment = form.save(commit=False)
        payment.control = ctrl
        payment.recorded_by = request.user
        payment.status = ControlPayment.PaymentStatus.CONFIRMED
        payment.save()

        ctrl.recompute_totals()

        messages.success(
            request,
            f"Pagamento de {payment.amount:,.2f} XOF registado com sucesso.",
        )
        return redirect("agent-control-detail", pk=pk)


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

class ControlAddDocumentView(AgentRequiredMixin, View):
    """POST: upload a document."""

    def post(self, request, pk, *args, **kwargs):
        ctrl = get_object_or_404(EmployerControl, pk=pk)
        form = ControlDocumentForm(request.POST, request.FILES)

        if not form.is_valid():
            messages.error(request, "Formulário de documento inválido.")
            return redirect("agent-control-detail", pk=pk)

        doc = form.save(commit=False)
        doc.control = ctrl
        doc.uploaded_by = request.user
        doc.save()

        messages.success(request, f"Documento '{doc.name}' carregado com sucesso.")
        return redirect("agent-control-detail", pk=pk)


# ---------------------------------------------------------------------------
# PV PDF (WeasyPrint)
# ---------------------------------------------------------------------------

class ControlPVView(AgentRequiredMixin, View):
    """GET: generate a PDF procès-verbal for the control."""

    def get(self, request, pk, *args, **kwargs):
        ctrl = get_object_or_404(
            EmployerControl.objects.select_related(
                "employer", "assigned_agent"
            ).prefetch_related("assessments"),
            pk=pk,
        )

        from django.template.loader import render_to_string

        html_string = render_to_string(
            "portal/agent/controls/pv_pdf.html",
            {"control": ctrl, "assessments": ctrl.assessments.all()},
            request=request,
        )

        try:
            import weasyprint

            pdf = weasyprint.HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf()
            response = HttpResponse(pdf, content_type="application/pdf")
            response["Content-Disposition"] = (
                f'inline; filename="{ctrl.pv_reference}.pdf"'
            )
            return response
        except ImportError:
            # WeasyPrint not installed: return HTML fallback
            return HttpResponse(html_string, content_type="text/html")

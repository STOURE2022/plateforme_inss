from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.mixins import AgentRequiredMixin, EmployerRequiredMixin
from apps.affiliates.models import Affiliate
from apps.employers.models import Employer

from .forms import AddDeclarationLineForm, AgentRejectForm, AgentValidateForm, DeclarationCreateForm
from .models import DeclarationStatus, PayrollDeclaration, PayrollDeclarationLine


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_employer_or_404(request):
    try:
        return request.user.employer
    except Employer.DoesNotExist:
        return None


# ---------------------------------------------------------------------------
# Employer: Affiliate NISS lookup (HTMX)
# ---------------------------------------------------------------------------

class AffiliateLookupView(EmployerRequiredMixin, View):
    """GET /portal/employer/declarations/lookup/?niss=X — returns HTML fragment."""

    def get(self, request):
        niss = request.GET.get("niss", "").strip()
        if len(niss) >= 5:
            try:
                affiliate = Affiliate.objects.get(niss=niss, status="ACTIVE")
                return HttpResponse(
                    f'<span class="text-green-600 text-sm font-medium">&#10003; {affiliate.full_name}</span>'
                )
            except Affiliate.DoesNotExist:
                return HttpResponse(
                    '<span class="text-red-500 text-sm">NISS não encontrado ou inativo</span>'
                )
        return HttpResponse("")


# ---------------------------------------------------------------------------
# Employer: Declaration List
# ---------------------------------------------------------------------------

class EmployerDeclarationListView(EmployerRequiredMixin, TemplateView):
    template_name = "portal/employer/declarations/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        employer = _get_employer_or_404(self.request)
        if not employer:
            ctx["employer"] = None
            ctx["declarations"] = []
            return ctx

        ctx["employer"] = employer
        status_filter = self.request.GET.get("status", "")
        qs = employer.payroll_declarations.all()
        if status_filter:
            qs = qs.filter(status=status_filter)
        ctx["declarations"] = qs
        ctx["status_filter"] = status_filter
        ctx["DeclarationStatus"] = DeclarationStatus
        return ctx


# ---------------------------------------------------------------------------
# Employer: Declaration Create
# ---------------------------------------------------------------------------

class EmployerDeclarationCreateView(EmployerRequiredMixin, View):
    template_name = "portal/employer/declarations/create.html"

    def get(self, request):
        employer = _get_employer_or_404(request)
        if not employer:
            messages.error(request, "Perfil de empregador não encontrado.")
            return redirect("employer-dashboard")
        form = DeclarationCreateForm(initial={"period_year": timezone.now().year, "period_month": timezone.now().month})
        return render(request, self.template_name, {"form": form, "employer": employer})

    def post(self, request):
        employer = _get_employer_or_404(request)
        if not employer:
            messages.error(request, "Perfil de empregador não encontrado.")
            return redirect("employer-dashboard")

        form = DeclarationCreateForm(request.POST)
        if form.is_valid():
            year = form.cleaned_data["period_year"]
            month = int(form.cleaned_data["period_month"])

            # Check for duplicate
            if PayrollDeclaration.objects.filter(
                employer=employer, period_year=year, period_month=month
            ).exists():
                form.add_error(
                    None,
                    f"Já existe uma declaração para {month:02d}/{year}. Não é possível criar uma segunda.",
                )
                return render(request, self.template_name, {"form": form, "employer": employer})

            decl = PayrollDeclaration.objects.create(
                employer=employer,
                period_year=year,
                period_month=month,
                created_by=request.user,
            )
            messages.success(request, f"Declaração {decl.reference} criada com sucesso.")
            return redirect("employer-declaration-detail", pk=decl.pk)

        return render(request, self.template_name, {"form": form, "employer": employer})


# ---------------------------------------------------------------------------
# Employer: Declaration Detail
# ---------------------------------------------------------------------------

class EmployerDeclarationDetailView(EmployerRequiredMixin, View):
    template_name = "portal/employer/declarations/detail.html"

    def get(self, request, pk):
        employer = _get_employer_or_404(request)
        if not employer:
            messages.error(request, "Perfil de empregador não encontrado.")
            return redirect("employer-dashboard")

        declaration = get_object_or_404(
            PayrollDeclaration, pk=pk, employer=employer
        )
        add_line_form = AddDeclarationLineForm()
        return render(
            request,
            self.template_name,
            {
                "declaration": declaration,
                "employer": employer,
                "add_line_form": add_line_form,
                "lines": declaration.lines.select_related("affiliate").all(),
                "DeclarationStatus": DeclarationStatus,
            },
        )


# ---------------------------------------------------------------------------
# Employer: Add Line (HTMX-aware)
# ---------------------------------------------------------------------------

class EmployerDeclarationAddLineView(EmployerRequiredMixin, View):
    """POST only — add one employee line to a DRAFT declaration."""

    def post(self, request, pk):
        employer = _get_employer_or_404(request)
        if not employer:
            return HttpResponse("Empregador não encontrado.", status=403)

        declaration = get_object_or_404(PayrollDeclaration, pk=pk, employer=employer)

        if declaration.status != DeclarationStatus.DRAFT:
            if request.headers.get("HX-Request"):
                return HttpResponse(
                    '<p class="text-red-500 text-sm">Declaração não está em rascunho.</p>',
                    status=400,
                )
            messages.error(request, "Não é possível adicionar linhas — declaração não está em rascunho.")
            return redirect("employer-declaration-detail", pk=pk)

        form = AddDeclarationLineForm(request.POST)
        if form.is_valid():
            niss = form.cleaned_data["niss"].strip()
            salary_base = form.cleaned_data["salary_base"]
            notes = form.cleaned_data.get("notes", "")

            try:
                affiliate = Affiliate.objects.get(niss=niss, status="ACTIVE")
            except Affiliate.DoesNotExist:
                if request.headers.get("HX-Request"):
                    return HttpResponse(
                        '<p class="text-red-500 text-sm font-medium">NISS não encontrado ou afiliado inativo.</p>',
                        status=400,
                    )
                messages.error(request, "NISS não encontrado ou afiliado inativo.")
                return redirect("employer-declaration-detail", pk=pk)

            if PayrollDeclarationLine.objects.filter(
                declaration=declaration, affiliate=affiliate
            ).exists():
                if request.headers.get("HX-Request"):
                    return HttpResponse(
                        f'<p class="text-amber-600 text-sm font-medium">{affiliate.full_name} já foi adicionado a esta declaração.</p>',
                        status=400,
                    )
                messages.warning(request, f"{affiliate.full_name} já foi adicionado a esta declaração.")
                return redirect("employer-declaration-detail", pk=pk)

            PayrollDeclarationLine.objects.create(
                declaration=declaration,
                affiliate=affiliate,
                salary_base=salary_base,
                notes=notes,
            )
            declaration.recompute_totals()

            if request.headers.get("HX-Request"):
                lines = declaration.lines.select_related("affiliate").all()
                return render(
                    request,
                    "portal/employer/declarations/partials/lines_table.html",
                    {
                        "declaration": declaration,
                        "lines": lines,
                        "DeclarationStatus": DeclarationStatus,
                    },
                )

            messages.success(request, f"{affiliate.full_name} adicionado com sucesso.")
            return redirect("employer-declaration-detail", pk=pk)

        # Form invalid
        if request.headers.get("HX-Request"):
            errors = "; ".join(
                f"{f}: {', '.join(errs)}" for f, errs in form.errors.items()
            )
            return HttpResponse(
                f'<p class="text-red-500 text-sm font-medium">Erro: {errors}</p>',
                status=400,
            )

        messages.error(request, "Formulário inválido. Verifique os dados.")
        return redirect("employer-declaration-detail", pk=pk)


# ---------------------------------------------------------------------------
# Employer: Remove Line
# ---------------------------------------------------------------------------

class EmployerDeclarationRemoveLineView(EmployerRequiredMixin, View):
    """POST only — remove a line from DRAFT declaration."""

    def post(self, request, pk, line_pk):
        employer = _get_employer_or_404(request)
        if not employer:
            messages.error(request, "Perfil de empregador não encontrado.")
            return redirect("employer-dashboard")

        declaration = get_object_or_404(PayrollDeclaration, pk=pk, employer=employer)

        if declaration.status != DeclarationStatus.DRAFT:
            messages.error(request, "Não é possível remover linhas — declaração não está em rascunho.")
            return redirect("employer-declaration-detail", pk=pk)

        line = get_object_or_404(PayrollDeclarationLine, pk=line_pk, declaration=declaration)
        name = line.affiliate.full_name
        line.delete()
        declaration.recompute_totals()

        if request.headers.get("HX-Request"):
            lines = declaration.lines.select_related("affiliate").all()
            return render(
                request,
                "portal/employer/declarations/partials/lines_table.html",
                {
                    "declaration": declaration,
                    "lines": lines,
                    "DeclarationStatus": DeclarationStatus,
                },
            )

        messages.success(request, f"{name} removido da declaração.")
        return redirect("employer-declaration-detail", pk=pk)


# ---------------------------------------------------------------------------
# Employer: Submit Declaration
# ---------------------------------------------------------------------------

class EmployerDeclarationSubmitView(EmployerRequiredMixin, View):
    """POST only — transition DRAFT → SUBMITTED."""

    def post(self, request, pk):
        employer = _get_employer_or_404(request)
        if not employer:
            messages.error(request, "Perfil de empregador não encontrado.")
            return redirect("employer-dashboard")

        declaration = get_object_or_404(PayrollDeclaration, pk=pk, employer=employer)

        if declaration.status != DeclarationStatus.DRAFT:
            messages.error(request, "Apenas declarações em rascunho podem ser submetidas.")
            return redirect("employer-declaration-detail", pk=pk)

        if declaration.total_employees == 0:
            messages.error(
                request,
                "Não é possível submeter uma declaração sem trabalhadores. Adicione pelo menos um.",
            )
            return redirect("employer-declaration-detail", pk=pk)

        declaration.status = DeclarationStatus.SUBMITTED
        declaration.submitted_at = timezone.now()
        declaration.save(update_fields=["status", "submitted_at", "updated_at"])

        # Notify agents (best-effort)
        try:
            from apps.notifications.models import Notification
            from apps.accounts.models import User

            agents = User.objects.filter(role__in=["AGENT", "ADMIN"])
            for agent in agents:
                Notification.objects.create(
                    recipient=agent,
                    title="Nova declaração submetida",
                    message=f"A empresa {employer.company_name} submeteu a declaração {declaration.reference} para validação.",
                    notification_type="INFO",
                )
        except Exception:
            pass

        messages.success(
            request,
            f"Declaração {declaration.reference} submetida com sucesso. Aguardando validação pelo INSS.",
        )
        return redirect("employer-declaration-detail", pk=pk)


# ---------------------------------------------------------------------------
# Employer: Reopen (REJECTED → DRAFT)
# ---------------------------------------------------------------------------

class EmployerDeclarationReopenView(EmployerRequiredMixin, View):
    """POST only — transition REJECTED → DRAFT so employer can fix and resubmit."""

    def post(self, request, pk):
        employer = _get_employer_or_404(request)
        if not employer:
            messages.error(request, "Perfil de empregador não encontrado.")
            return redirect("employer-dashboard")

        declaration = get_object_or_404(PayrollDeclaration, pk=pk, employer=employer)

        if declaration.status != DeclarationStatus.REJECTED:
            messages.error(request, "Apenas declarações rejeitadas podem ser reabertas.")
            return redirect("employer-declaration-detail", pk=pk)

        declaration.status = DeclarationStatus.DRAFT
        declaration.rejected_by = None
        declaration.rejected_at = None
        declaration.rejection_reason = ""
        declaration.save(
            update_fields=["status", "rejected_by", "rejected_at", "rejection_reason", "updated_at"]
        )

        messages.info(request, "Declaração reaberta. Pode corrigir e submeter novamente.")
        return redirect("employer-declaration-detail", pk=pk)


# ---------------------------------------------------------------------------
# Employer: Download Bulletin PDF
# ---------------------------------------------------------------------------

class EmployerDeclarationBulletinView(EmployerRequiredMixin, View):
    """GET — generate and download PDF bulletin for VALIDATED declarations."""

    def get(self, request, pk):
        employer = _get_employer_or_404(request)
        if not employer:
            messages.error(request, "Perfil de empregador não encontrado.")
            return redirect("employer-dashboard")

        declaration = get_object_or_404(PayrollDeclaration, pk=pk, employer=employer)

        if declaration.status != DeclarationStatus.VALIDATED:
            messages.error(request, "O boletim só está disponível para declarações validadas.")
            return redirect("employer-declaration-detail", pk=pk)

        lines = declaration.lines.select_related("affiliate").all()
        html_content = render(
            request,
            "portal/employer/declarations/bulletin_pdf.html",
            {"declaration": declaration, "lines": lines},
        ).content.decode("utf-8")

        try:
            from weasyprint import HTML as WeasyHTML

            pdf_bytes = WeasyHTML(string=html_content, base_url=request.build_absolute_uri("/")).write_pdf()
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="boletim-{declaration.reference}.pdf"'
            )
            return response
        except ImportError:
            # WeasyPrint not installed — return HTML fallback
            return HttpResponse(html_content, content_type="text/html")


# ---------------------------------------------------------------------------
# Agent: Declaration List
# ---------------------------------------------------------------------------

class AgentDeclarationListView(AgentRequiredMixin, TemplateView):
    template_name = "portal/agent/declarations/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        status_filter = self.request.GET.get("status", "")
        employer_q = self.request.GET.get("q", "").strip()
        year_filter = self.request.GET.get("year", "")

        # SUBMITTED ones first, then others
        qs = PayrollDeclaration.objects.select_related("employer", "validated_by", "rejected_by").order_by(
            # SUBMITTED first
            "-period_year",
            "-period_month",
        )

        if status_filter:
            qs = qs.filter(status=status_filter)
        if employer_q:
            qs = qs.filter(employer__company_name__icontains=employer_q) | qs.filter(
                employer__nuit__icontains=employer_q
            )
        if year_filter:
            qs = qs.filter(period_year=year_filter)

        # Sort: SUBMITTED first within results
        submitted = qs.filter(status=DeclarationStatus.SUBMITTED)
        others = qs.exclude(status=DeclarationStatus.SUBMITTED)

        ctx["submitted_declarations"] = submitted
        ctx["other_declarations"] = others
        ctx["all_declarations"] = qs
        ctx["status_filter"] = status_filter
        ctx["employer_q"] = employer_q
        ctx["year_filter"] = year_filter
        ctx["DeclarationStatus"] = DeclarationStatus
        ctx["declarations_to_validate"] = submitted.count()

        from django.utils import timezone
        ctx["years"] = list(range(2020, timezone.now().year + 2))
        return ctx


# ---------------------------------------------------------------------------
# Agent: Declaration Detail
# ---------------------------------------------------------------------------

class AgentDeclarationDetailView(AgentRequiredMixin, View):
    template_name = "portal/agent/declarations/detail.html"

    def get(self, request, pk):
        declaration = get_object_or_404(
            PayrollDeclaration.objects.select_related("employer", "validated_by", "rejected_by", "created_by"),
            pk=pk,
        )
        lines = declaration.lines.select_related("affiliate", "contribution").all()
        reject_form = AgentRejectForm()
        validate_form = AgentValidateForm()
        return render(
            request,
            self.template_name,
            {
                "declaration": declaration,
                "lines": lines,
                "reject_form": reject_form,
                "validate_form": validate_form,
                "DeclarationStatus": DeclarationStatus,
            },
        )


# ---------------------------------------------------------------------------
# Agent: Validate Declaration
# ---------------------------------------------------------------------------

class AgentDeclarationValidateView(AgentRequiredMixin, View):
    """POST — SUBMITTED → VALIDATED. Creates contributions."""

    def post(self, request, pk):
        declaration = get_object_or_404(PayrollDeclaration, pk=pk)

        if declaration.status != DeclarationStatus.SUBMITTED:
            messages.error(request, "Apenas declarações submetidas podem ser validadas.")
            return redirect("agent-declaration-detail", pk=pk)

        form = AgentValidateForm(request.POST)
        if form.is_valid():
            notes = form.cleaned_data.get("validation_notes", "")
        else:
            notes = ""

        declaration.status = DeclarationStatus.VALIDATED
        declaration.validated_by = request.user
        declaration.validated_at = timezone.now()
        declaration.validation_notes = notes
        declaration.save(
            update_fields=["status", "validated_by", "validated_at", "validation_notes", "updated_at"]
        )

        created_count = declaration.generate_contributions(request.user)

        # Notify employer
        try:
            from apps.notifications.models import Notification

            Notification.objects.create(
                recipient=declaration.employer.user,
                title="Declaração validada",
                message=(
                    f"A sua declaração {declaration.reference} ({declaration.get_period_display()}) "
                    f"foi validada. {created_count} contribuição(ões) gerada(s)."
                ),
                notification_type="SUCCESS",
            )
        except Exception:
            pass

        messages.success(
            request,
            f"Declaração {declaration.reference} validada. {created_count} contribuição(ões) gerada(s).",
        )
        return redirect("agent-declaration-detail", pk=pk)


# ---------------------------------------------------------------------------
# Agent: Reject Declaration
# ---------------------------------------------------------------------------

class AgentDeclarationRejectView(AgentRequiredMixin, View):
    """POST — SUBMITTED → REJECTED with rejection_reason."""

    def post(self, request, pk):
        declaration = get_object_or_404(PayrollDeclaration, pk=pk)

        if declaration.status != DeclarationStatus.SUBMITTED:
            messages.error(request, "Apenas declarações submetidas podem ser rejeitadas.")
            return redirect("agent-declaration-detail", pk=pk)

        form = AgentRejectForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Forneça um motivo de rejeição.")
            return redirect("agent-declaration-detail", pk=pk)

        declaration.status = DeclarationStatus.REJECTED
        declaration.rejected_by = request.user
        declaration.rejected_at = timezone.now()
        declaration.rejection_reason = form.cleaned_data["rejection_reason"]
        declaration.save(
            update_fields=["status", "rejected_by", "rejected_at", "rejection_reason", "updated_at"]
        )

        # Notify employer
        try:
            from apps.notifications.models import Notification

            Notification.objects.create(
                recipient=declaration.employer.user,
                title="Declaração rejeitada",
                message=(
                    f"A sua declaração {declaration.reference} ({declaration.get_period_display()}) "
                    f"foi rejeitada. Motivo: {declaration.rejection_reason}"
                ),
                notification_type="WARNING",
            )
        except Exception:
            pass

        messages.warning(
            request,
            f"Declaração {declaration.reference} rejeitada.",
        )
        return redirect("agent-declaration-detail", pk=pk)

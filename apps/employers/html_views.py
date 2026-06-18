from decimal import Decimal

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.mixins import EmployerRequiredMixin, AgentRequiredMixin
from apps.contributions.forms import ContributionCreateForm
from apps.contributions.models import Contribution

from .forms import EmployerCreateForm
from .models import Employer


# ---------------------------------------------------------------------------
# Espaço Empregador
# ---------------------------------------------------------------------------

class EmployerDashboardView(EmployerRequiredMixin, TemplateView):
    template_name = "portal/employer/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.utils import timezone

        try:
            employer = self.request.user.employer
        except Employer.DoesNotExist:
            ctx["employer"] = None
            return ctx

        ctx["employer"] = employer

        today = timezone.now()
        ctx["contributions_month"] = employer.contributions.filter(
            period_year=today.year,
            period_month=today.month,
        )
        ctx["late_contributions"] = employer.contributions.filter(status="LATE")
        ctx["total_paid_month"] = sum(
            c.total_amount for c in ctx["contributions_month"]
        )
        ctx["employees_count"] = employer.contributions.filter(
            period_year=today.year, period_month=today.month
        ).values("affiliate").distinct().count()

        return ctx


class EmployerProfileView(EmployerRequiredMixin, TemplateView):
    template_name = "portal/employer/profile.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            ctx["employer"] = self.request.user.employer
        except Employer.DoesNotExist:
            ctx["employer"] = None
        return ctx


class EmployerContributionsView(EmployerRequiredMixin, TemplateView):
    template_name = "portal/employer/contributions.html"

    def _get_queryset(self, request):
        try:
            employer = request.user.employer
        except Employer.DoesNotExist:
            return Contribution.objects.none()

        qs = employer.contributions.select_related("affiliate").order_by("-period_year", "-period_month")

        year = request.GET.get("year")
        month = request.GET.get("month")
        status = request.GET.get("status")

        if year:
            qs = qs.filter(period_year=year)
        if month:
            qs = qs.filter(period_month=month)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.utils import timezone
        from apps.contributions.models import ContributionStatus

        qs = self._get_queryset(self.request)
        ctx["contributions"] = qs
        ctx["status_choices"] = ContributionStatus.choices
        ctx["selected_year"] = self.request.GET.get("year", "")
        ctx["selected_month"] = self.request.GET.get("month", "")
        ctx["selected_status"] = self.request.GET.get("status", "")
        ctx["years"] = list(range(2020, timezone.now().year + 1))
        ctx["months"] = list(range(1, 13))
        return ctx

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        if request.headers.get("HX-Request"):
            return render(request, "portal/employer/partials/contributions_tbody.html", ctx)
        return render(request, self.template_name, ctx)


class EmployerContributionCreateView(EmployerRequiredMixin, View):
    template_name = "portal/employer/contribution_form.html"

    def get(self, request):
        try:
            employer = request.user.employer
        except Employer.DoesNotExist:
            messages.error(request, "Perfil de empregador não encontrado.")
            return redirect("employer-dashboard")

        form = ContributionCreateForm(initial={"employer": employer})
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        try:
            employer = request.user.employer
        except Employer.DoesNotExist:
            messages.error(request, "Perfil de empregador não encontrado.")
            return redirect("employer-dashboard")

        form = ContributionCreateForm(request.POST)
        if form.is_valid():
            contribution = form.save(commit=False)
            contribution.employer = employer
            contribution.created_by = request.user
            contribution.save()
            messages.success(request, "Contribuição registada com sucesso.")
            return redirect("employer-contributions")

        return render(request, self.template_name, {"form": form})


class EmployerContributionCalculateView(EmployerRequiredMixin, View):
    """POST /portal/employer/contributions/calculate/ — retorna fragmento HTML."""

    def post(self, request):
        try:
            salary_base = Decimal(str(request.POST.get("salary_base", "0") or "0"))
        except Exception:
            salary_base = Decimal("0")

        employee_rate = Decimal("0.0400")
        employer_rate = Decimal("0.0800")

        employee_amount = salary_base * employee_rate
        employer_amount = salary_base * employer_rate
        total_amount = employee_amount + employer_amount

        ctx = {
            "employee_amount": employee_amount,
            "employer_amount": employer_amount,
            "total_amount": total_amount,
            "salary_base": salary_base,
        }
        return render(request, "portal/employer/partials/calculation_result.html", ctx)


# ---------------------------------------------------------------------------
# Vistas de Agente — Empregadores
# ---------------------------------------------------------------------------

class AgentEmployerListView(AgentRequiredMixin, TemplateView):
    template_name = "portal/agent/employer_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip()
        qs = Employer.objects.select_related("user").order_by("-registration_date")
        if q:
            qs = qs.filter(company_name__icontains=q) | qs.filter(nuit__icontains=q)
        ctx["employers"] = qs[:50]
        ctx["q"] = q
        return ctx

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        if request.headers.get("HX-Request"):
            return render(request, "portal/agent/partials/employer_rows.html", ctx)
        return render(request, self.template_name, ctx)


class AgentEmployerCreateView(AgentRequiredMixin, View):
    template_name = "portal/agent/employer_form.html"

    def get(self, request):
        form = EmployerCreateForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = EmployerCreateForm(request.POST)
        if form.is_valid():
            from django.contrib.auth import get_user_model
            User = get_user_model()

            # Criar utilizador associado ao empregador
            email = request.POST.get("user_email", "").strip()
            password = request.POST.get("user_password", "").strip()

            if not email or not password:
                form.add_error(None, "Email e senha do utilizador são obrigatórios.")
                return render(request, self.template_name, {"form": form})

            if User.objects.filter(email=email).exists():
                form.add_error(None, "Este email já está registado.")
                return render(request, self.template_name, {"form": form})

            user = User.objects.create_user(email=email, password=password, role="EMPLOYER")
            employer = form.save(commit=False)
            employer.user = user
            employer.registered_by = request.user
            employer.save()

            messages.success(request, f"Empregador {employer.company_name} criado com sucesso.")
            return redirect("agent-employers")

        return render(request, self.template_name, {"form": form})

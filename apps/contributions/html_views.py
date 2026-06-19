from decimal import Decimal

from django.db.models import Sum, Avg
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.mixins import CitizenRequiredMixin, AgentRequiredMixin
from apps.affiliates.models import Affiliate
from apps.contributions.models import Contribution, CareerStatementLog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_career_context(affiliate, paid_only=True):
    """Return a dict with all career data for an affiliate."""
    qs = Contribution.objects.filter(affiliate=affiliate)
    if paid_only:
        qs = qs.filter(status="PAID")
    contributions = qs.select_related("employer").order_by("period_year", "period_month")

    total_months = contributions.count()
    total_contributed = contributions.aggregate(s=Sum("total_amount"))["s"] or Decimal("0")
    avg_salary = contributions.aggregate(a=Avg("salary_base"))["a"] or Decimal("0")
    first_contribution = contributions.first()
    last_contribution = contributions.last()

    # Group by employer
    employers_map = {}
    for c in contributions:
        key = c.employer_id if c.employer_id is not None else "independant"
        if key not in employers_map:
            employers_map[key] = {
                "employer": c.employer,
                "contributions": [],
                "months_count": 0,
                "total_amount": Decimal("0"),
            }
        employers_map[key]["contributions"].append(c)
        employers_map[key]["months_count"] += 1
        employers_map[key]["total_amount"] += c.total_amount

    employer_groups = list(employers_map.values())

    # Group by year
    years_map = {}
    for c in contributions:
        y = c.period_year
        if y not in years_map:
            years_map[y] = {
                "year": y,
                "contributions": [],
                "months": 0,
                "total": Decimal("0"),
            }
        years_map[y]["contributions"].append(c)
        years_map[y]["months"] += 1
        years_map[y]["total"] += c.total_amount

    year_groups = sorted(years_map.values(), key=lambda x: x["year"], reverse=True)

    return {
        "affiliate": affiliate,
        "contributions": contributions,
        "employer_groups": employer_groups,
        "year_groups": year_groups,
        "total_months": total_months,
        "total_contributed": total_contributed,
        "avg_salary": avg_salary,
        "first_contribution": first_contribution,
        "last_contribution": last_contribution,
        "generated_at": timezone.now(),
    }


# ---------------------------------------------------------------------------
# Citizen — Career Statement (online HTML)
# ---------------------------------------------------------------------------

class CitizenCareerView(CitizenRequiredMixin, TemplateView):
    template_name = "portal/citizen/career/statement.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            affiliate = self.request.user.affiliate
        except Affiliate.DoesNotExist:
            ctx["affiliate"] = None
            return ctx

        ctx.update(_build_career_context(affiliate, paid_only=True))
        return ctx


# ---------------------------------------------------------------------------
# Citizen — Career Statement PDF download
# ---------------------------------------------------------------------------

class CitizenCareerPDFView(CitizenRequiredMixin, View):
    def get(self, request):
        try:
            affiliate = request.user.affiliate
        except Affiliate.DoesNotExist:
            return HttpResponse("Perfil de afiliado não encontrado.", status=404)

        context = _build_career_context(affiliate, paid_only=True)

        html = render_to_string(
            "portal/citizen/career/statement_pdf.html",
            context,
            request=request,
        )

        import weasyprint  # noqa: PLC0415
        pdf = weasyprint.HTML(
            string=html, base_url=request.build_absolute_uri("/")
        ).write_pdf()

        # Log generation
        CareerStatementLog.objects.create(
            affiliate=affiliate,
            generated_by=request.user,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        filename = f"releve-carriere-{affiliate.niss}-{timezone.now().strftime('%Y%m%d')}.pdf"
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# ---------------------------------------------------------------------------
# Agent — Career Statement for any affiliate (online HTML)
# ---------------------------------------------------------------------------

class AgentCareerView(AgentRequiredMixin, TemplateView):
    template_name = "portal/agent/career/statement.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        affiliate = get_object_or_404(
            Affiliate.objects.select_related("user"),
            pk=kwargs["affiliate_pk"],
        )

        ctx.update(_build_career_context(affiliate, paid_only=False))

        # Generation history
        ctx["generation_logs"] = CareerStatementLog.objects.filter(
            affiliate=affiliate
        ).select_related("generated_by").order_by("-generated_at")[:20]

        return ctx


# ---------------------------------------------------------------------------
# Agent — Career Statement PDF for any affiliate
# ---------------------------------------------------------------------------

class AgentCareerPDFView(AgentRequiredMixin, View):
    def get(self, request, affiliate_pk):
        affiliate = get_object_or_404(
            Affiliate.objects.select_related("user"),
            pk=affiliate_pk,
        )

        context = _build_career_context(affiliate, paid_only=False)

        html = render_to_string(
            "portal/citizen/career/statement_pdf.html",
            context,
            request=request,
        )

        import weasyprint  # noqa: PLC0415
        pdf = weasyprint.HTML(
            string=html, base_url=request.build_absolute_uri("/")
        ).write_pdf()

        # Log generation
        CareerStatementLog.objects.create(
            affiliate=affiliate,
            generated_by=request.user,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        filename = f"releve-carriere-{affiliate.niss}-{timezone.now().strftime('%Y%m%d')}.pdf"
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

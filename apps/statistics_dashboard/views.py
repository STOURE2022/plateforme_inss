"""
views.py — Statistics dashboard views (agent/admin only).
"""

import csv
import json
from datetime import date

from django.http import HttpResponse
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.mixins import AgentRequiredMixin

from .services import (
    get_affiliates_growth_chart,
    get_benefits_stats,
    get_claims_stats,
    get_contribution_stats,
    get_coverage_stats,
    get_defaulting_employers,
    get_monthly_contributions_chart,
    get_sector_breakdown,
    get_top_contributing_employers,
)


class NationalStatsDashboardView(AgentRequiredMixin, TemplateView):
    """Main national statistics dashboard — AGENT and ADMIN only."""

    template_name = "portal/agent/statistics/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        year = int(self.request.GET.get("year", date.today().year))
        sector_data = get_sector_breakdown()
        ctx.update({
            "selected_year": year,
            "available_years": list(
                range(date.today().year, date.today().year - 5, -1)
            ),
            "coverage": get_coverage_stats(),
            "contributions": get_contribution_stats(year),
            "monthly_chart": json.dumps(get_monthly_contributions_chart(year)),
            "defaulting_employers": get_defaulting_employers(),
            "benefits": get_benefits_stats(),
            "claims": get_claims_stats(),
            "growth_chart": json.dumps(get_affiliates_growth_chart()),
            "sector_breakdown": sector_data,
            "sector_breakdown_json": json.dumps(sector_data),
            "top_employers": get_top_contributing_employers(),
        })
        return ctx


class StatsExportView(AgentRequiredMixin, View):
    """Export statistics as CSV — AGENT and ADMIN only."""

    def get(self, request, *args, **kwargs):
        export_type = request.GET.get("export", "")
        year = int(request.GET.get("year", date.today().year))

        if export_type == "contributions_monthly":
            return self._export_contributions_monthly(year)
        elif export_type == "defaulting_employers":
            return self._export_defaulting_employers()
        elif export_type == "top_employers":
            return self._export_top_employers(year)

        return HttpResponse("Tipo de exportação inválido.", status=400)

    def _make_response(self, filename):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write("\ufeff")  # UTF-8 BOM for Excel compatibility
        return response

    def _export_contributions_monthly(self, year):
        response = self._make_response(f"cotizacoes_mensais_{year}.csv")
        writer = csv.writer(response)
        writer.writerow(["Mês", "Nº Pago", "Montante (XOF)"])
        for row in get_monthly_contributions_chart(year):
            writer.writerow([row["month_label"], row["paid_count"], row["amount"]])
        return response

    def _export_defaulting_employers(self):
        response = self._make_response("empregadores_incumpridores.csv")
        writer = csv.writer(response)
        writer.writerow(["Empresa", "NUIT", "Meses em Falta", "Total em Dívida (XOF)"])
        for row in get_defaulting_employers(limit=100):
            writer.writerow([
                row.get("employer__company_name", ""),
                row.get("employer__nuit", ""),
                row.get("late_months", 0),
                row.get("total_due", 0),
            ])
        return response

    def _export_top_employers(self, year):
        response = self._make_response(f"top_empregadores_{year}.csv")
        writer = csv.writer(response)
        writer.writerow(["Empresa", "NUIT", "Sector", "Total Pago (XOF)", "Meses"])
        for row in get_top_contributing_employers(limit=100):
            writer.writerow([
                row.get("employer__company_name", ""),
                row.get("employer__nuit", ""),
                row.get("employer__sector", ""),
                row.get("total", 0),
                row.get("months", 0),
            ])
        return response

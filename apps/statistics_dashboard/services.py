"""
services.py — all heavy data computation for the national statistics dashboard.
No models live here; everything is aggregated from existing app models.
"""

from datetime import date, timedelta

from django.db.models import Avg, Count, Q, Sum

from apps.affiliates.models import Affiliate, Dependent
from apps.contributions.models import Contribution
from apps.employers.models import Employer


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------

def get_coverage_stats():
    """Taux de couverture — affiliates, dependents, employers."""
    total_affiliates = Affiliate.objects.count()
    active_affiliates = Affiliate.objects.filter(status="ACTIVE").count()
    total_dependents = Dependent.objects.filter(is_active=True).count()
    total_covered = active_affiliates + total_dependents
    total_employers = Employer.objects.count()
    active_employers = Employer.objects.filter(status="ACTIVE").count()
    inactive_employers = Employer.objects.filter(
        status__in=["INACTIVE", "SUSPENDED"]
    ).count()

    # New affiliates this month
    today = date.today()
    new_this_month = Affiliate.objects.filter(
        registration_date__year=today.year,
        registration_date__month=today.month,
    ).count()

    return {
        "total_affiliates": total_affiliates,
        "active_affiliates": active_affiliates,
        "total_dependents": total_dependents,
        "total_covered": total_covered,
        "total_employers": total_employers,
        "active_employers": active_employers,
        "inactive_employers": inactive_employers,
        "new_this_month": new_this_month,
        "coverage_rate": (
            round(active_affiliates / total_affiliates * 100, 1) if total_affiliates else 0
        ),
    }


# ---------------------------------------------------------------------------
# Contributions
# ---------------------------------------------------------------------------

def get_contribution_stats(year=None):
    """Masse cotisante — optionally filtered by year."""
    year = year or date.today().year
    qs = Contribution.objects.filter(period_year=year)
    paid = qs.filter(status="PAID")
    pending = qs.filter(status="PENDING")
    late = qs.filter(status="LATE")
    total_count = qs.count()

    return {
        "year": year,
        "total_expected": total_count,
        "total_paid": paid.count(),
        "total_pending": pending.count(),
        "total_late": late.count(),
        "payment_rate": round(paid.count() / total_count * 100, 1) if total_count else 0,
        "amount_collected": paid.aggregate(s=Sum("total_amount"))["s"] or 0,
        "amount_pending": pending.aggregate(s=Sum("total_amount"))["s"] or 0,
        "amount_late": late.aggregate(s=Sum("total_amount"))["s"] or 0,
    }


def get_monthly_contributions_chart(year=None):
    """Monthly contribution amounts for bar chart — returns list of 12 dicts."""
    year = year or date.today().year
    month_labels = [
        "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
        "Jul", "Ago", "Set", "Out", "Nov", "Dez",
    ]
    months = []
    for m in range(1, 13):
        paid = Contribution.objects.filter(
            period_year=year, period_month=m, status="PAID"
        )
        months.append({
            "month": m,
            "month_label": month_labels[m - 1],
            "paid_count": paid.count(),
            "amount": float(paid.aggregate(s=Sum("total_amount"))["s"] or 0),
        })
    return months


def get_defaulting_employers(limit=10):
    """Empregadores com cotizações em atraso (últimos 90 dias)."""
    cutoff = date.today() - timedelta(days=90)
    late_employers = (
        Contribution.objects
        .filter(status__in=["LATE", "PENDING"])
        .filter(
            Q(period_year__gt=cutoff.year)
            | Q(period_year=cutoff.year, period_month__gte=cutoff.month)
        )
        .values("employer__id", "employer__company_name", "employer__nuit")
        .annotate(
            late_months=Count("id"),
            total_due=Sum("total_amount"),
        )
        .order_by("-late_months")[:limit]
    )
    return list(late_employers)


def get_top_contributing_employers(limit=10):
    """Top employers by total paid contributions this year."""
    year = date.today().year
    return list(
        Contribution.objects
        .filter(status="PAID", period_year=year)
        .values("employer__company_name", "employer__nuit", "employer__sector")
        .annotate(total=Sum("total_amount"), months=Count("id"))
        .order_by("-total")[:limit]
    )


# ---------------------------------------------------------------------------
# Benefits
# ---------------------------------------------------------------------------

def get_benefits_stats():
    """Statistiques des prestations."""
    from apps.benefits.models import BenefitRequest, BenefitPayment, BenefitCategory

    total_requests = BenefitRequest.objects.count()

    by_category = []
    for cat in BenefitCategory:
        by_category.append({
            "category": cat.value,
            "label": cat.label,
            "count": BenefitRequest.objects.filter(
                benefit_type__category=cat.value
            ).count(),
        })

    return {
        "total_requests": total_requests,
        "pending_review": BenefitRequest.objects.filter(
            status__in=["SUBMITTED", "UNDER_REVIEW"]
        ).count(),
        "approved": BenefitRequest.objects.filter(status="APPROVED").count(),
        "rejected": BenefitRequest.objects.filter(status="REJECTED").count(),
        "paying": BenefitRequest.objects.filter(status="PAYING").count(),
        "total_paid_this_year": BenefitPayment.objects.filter(
            status="PAID", period_year=date.today().year
        ).aggregate(s=Sum("amount"))["s"] or 0,
        "by_category": by_category,
    }


# ---------------------------------------------------------------------------
# Claims
# ---------------------------------------------------------------------------

def get_claims_stats():
    """Statistiques des réclamations."""
    from apps.claims.models import Claim

    total = Claim.objects.count()
    resolved_count = Claim.objects.filter(status="RESOLVED").count()

    avg_satisfaction = (
        Claim.objects.filter(satisfaction_rating__isnull=False)
        .aggregate(a=Avg("satisfaction_rating"))["a"]
        or 0
    )

    return {
        "total": total,
        "open": Claim.objects.filter(status="OPEN").count(),
        "under_review": Claim.objects.filter(status="UNDER_REVIEW").count(),
        "resolved": resolved_count,
        "rejected": Claim.objects.filter(status="REJECTED").count(),
        "overdue": Claim.objects.filter(
            due_date__lt=date.today(),
            status__in=["OPEN", "UNDER_REVIEW", "ADDITIONAL_INFO", "ESCALATED"],
        ).count(),
        "resolution_rate": round(resolved_count / total * 100, 1) if total else 0,
        "avg_satisfaction": round(float(avg_satisfaction), 1),
        "avg_satisfaction_int": int(round(float(avg_satisfaction))),
    }


# ---------------------------------------------------------------------------
# Growth chart
# ---------------------------------------------------------------------------

def get_affiliates_growth_chart():
    """New affiliates per month for last 12 months."""
    today = date.today()
    months = []
    for i in range(11, -1, -1):
        # Step back by approximate months
        d = today.replace(day=1) - timedelta(days=1)
        # Re-compute: go back i months from today's month
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        count = Affiliate.objects.filter(
            registration_date__year=year,
            registration_date__month=month,
        ).count()
        label_date = date(year, month, 1)
        months.append({
            "label": label_date.strftime("%b/%y"),
            "count": count,
        })
    return months


# ---------------------------------------------------------------------------
# Sector breakdown
# ---------------------------------------------------------------------------

def get_sector_breakdown():
    """Employers and paid contributions by sector for current year."""
    from apps.employers.models import SectorChoices

    sectors = []
    year = date.today().year
    for sector in SectorChoices:
        employers = Employer.objects.filter(
            sector=sector.value, status="ACTIVE"
        ).count()
        contributions = (
            Contribution.objects.filter(
                employer__sector=sector.value,
                status="PAID",
                period_year=year,
            ).aggregate(s=Sum("total_amount"))["s"]
            or 0
        )
        sectors.append({
            "sector": sector.value,
            "label": sector.label,
            "employers": employers,
            "contributions": float(contributions),
        })
    return sectors

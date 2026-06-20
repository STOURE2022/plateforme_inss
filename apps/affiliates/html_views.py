from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.mixins import CitizenRequiredMixin, AgentRequiredMixin
from apps.cards.models import HealthCard
from apps.contributions.models import Contribution
from apps.verification.models import VerificationLog

from .forms import AffiliateCreateForm
from .models import Affiliate


# ---------------------------------------------------------------------------
# Espaço Cidadão
# ---------------------------------------------------------------------------

class CitizenDashboardView(CitizenRequiredMixin, TemplateView):
    template_name = "portal/citizen/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            affiliate = self.request.user.affiliate
        except Affiliate.DoesNotExist:
            ctx["affiliate"] = None
            return ctx

        ctx["affiliate"] = affiliate

        # Carta
        try:
            ctx["card"] = affiliate.health_card
        except HealthCard.DoesNotExist:
            ctx["card"] = None

        # Últimas 3 contribuições
        ctx["recent_contributions"] = affiliate.contributions.order_by("-period_year", "-period_month")[:3]

        # Dependentes ativos
        ctx["dependents"] = affiliate.dependents.filter(is_active=True)
        ctx["dependents_count"] = ctx["dependents"].count()
        ctx["contributions_count"] = affiliate.contributions.count()

        # Prestacoes
        ctx["benefit_requests_count"] = affiliate.benefit_requests.count()

        # Reclamações abertas
        try:
            from apps.claims.models import Claim, ClaimStatus
            ctx["open_claims_count"] = Claim.objects.filter(
                filed_by=self.request.user,
                status__in=[ClaimStatus.OPEN, ClaimStatus.UNDER_REVIEW, ClaimStatus.ADDITIONAL_INFO, ClaimStatus.ESCALATED],
            ).count()
        except Exception:
            ctx["open_claims_count"] = 0

        # Actos médicos registados no cartão do cidadão
        try:
            if ctx.get("card"):
                from apps.verification.models import ProviderMedicalAct
                ctx["recent_medical_acts"] = ProviderMedicalAct.objects.filter(
                    card=ctx["card"]
                ).select_related("provider").order_by("-created_at")[:5]
            else:
                ctx["recent_medical_acts"] = []
        except Exception:
            ctx["recent_medical_acts"] = []

        return ctx


class CitizenCardView(CitizenRequiredMixin, TemplateView):
    template_name = "portal/citizen/card.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            affiliate = self.request.user.affiliate
            ctx["affiliate"] = affiliate
            ctx["card"] = affiliate.health_card
        except (Affiliate.DoesNotExist, HealthCard.DoesNotExist):
            ctx["affiliate"] = None
            ctx["card"] = None
        return ctx


class CitizenCardQRView(CitizenRequiredMixin, TemplateView):
    template_name = "portal/citizen/card_qr.html"

    def get_context_data(self, **kwargs):
        import base64
        from apps.cards.services.qr_service import QRTokenService

        ctx = super().get_context_data(**kwargs)
        try:
            affiliate = self.request.user.affiliate
            card = affiliate.health_card
            ctx["card"] = card
            service = QRTokenService()
            token = service.generate_token(card)
            qr_bytes = service.generate_qr_image(token)
            ctx["qr_b64"] = base64.b64encode(qr_bytes).decode("utf-8")
        except (Affiliate.DoesNotExist, HealthCard.DoesNotExist):
            ctx["card"] = None
            ctx["qr_b64"] = None
        return ctx


class CitizenContributionsView(CitizenRequiredMixin, TemplateView):
    template_name = "portal/citizen/contributions.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            affiliate = self.request.user.affiliate
        except Affiliate.DoesNotExist:
            ctx["contributions"] = []
            ctx["years"] = []
            return ctx

        year = self.request.GET.get("year")
        qs = affiliate.contributions.all()
        if year:
            qs = qs.filter(period_year=year)

        ctx["contributions"] = qs
        ctx["years"] = list(
            affiliate.contributions.values_list("period_year", flat=True).distinct().order_by("-period_year")
        )
        ctx["selected_year"] = year
        return ctx

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        # Resposta parcial HTMX
        if request.headers.get("HX-Request"):
            return render(request, "portal/citizen/partials/contributions_table.html", ctx)
        return render(request, self.template_name, ctx)


class CitizenDependentsView(CitizenRequiredMixin, TemplateView):
    template_name = "portal/citizen/dependents.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            affiliate = self.request.user.affiliate
            ctx["dependents"] = affiliate.dependents.all()
            ctx["affiliate"] = affiliate
        except Affiliate.DoesNotExist:
            ctx["dependents"] = []
            ctx["affiliate"] = None
        return ctx


# ---------------------------------------------------------------------------
# Espaço Agente — Afiliados
# ---------------------------------------------------------------------------

class AgentDashboardView(AgentRequiredMixin, TemplateView):
    template_name = "portal/agent/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.utils import timezone
        from apps.cards.models import HealthCard, CardStatus
        from apps.accounts.models import User

        today = timezone.now().date()

        ctx["total_affiliates"] = Affiliate.objects.filter(status="ACTIVE").count()
        ctx["cards_issued_today"] = HealthCard.objects.filter(issued_date=today).count()
        ctx["verifications_today"] = VerificationLog.objects.filter(
            verified_at__date=today
        ).count()
        ctx["recent_logs"] = VerificationLog.objects.select_related("verifier", "card").order_by("-verified_at")[:5]

        # Prestacoes pendentes
        try:
            from apps.benefits.models import BenefitRequest, BenefitRequestStatus
            ctx["benefits_pending_count"] = BenefitRequest.objects.filter(
                status__in=[BenefitRequestStatus.SUBMITTED, BenefitRequestStatus.UNDER_REVIEW]
            ).count()
        except Exception:
            ctx["benefits_pending_count"] = 0

        # Reclamações pendentes
        try:
            from apps.claims.models import Claim, ClaimStatus
            ctx["pending_claims_count"] = Claim.objects.filter(
                status__in=[ClaimStatus.OPEN, ClaimStatus.UNDER_REVIEW, ClaimStatus.ESCALATED]
            ).count()
        except Exception:
            ctx["pending_claims_count"] = 0

        # Declarações de massa salarial a validar
        try:
            from apps.payroll.models import PayrollDeclaration, DeclarationStatus
            ctx["declarations_to_validate"] = PayrollDeclaration.objects.filter(
                status=DeclarationStatus.SUBMITTED
            ).count()
        except Exception:
            ctx["declarations_to_validate"] = 0

        # Controlos de empregadores ativos
        try:
            from apps.controls.models import EmployerControl, ControlStatus
            ctx["active_controls_count"] = EmployerControl.objects.filter(
                status__in=[
                    ControlStatus.PLANNED,
                    ControlStatus.IN_PROGRESS,
                    ControlStatus.PV_DRAFTED,
                    ControlStatus.NOTIFIED,
                    ControlStatus.DISPUTED,
                ]
            ).count()
        except Exception:
            ctx["active_controls_count"] = 0

        # Actos médicos pendentes
        try:
            from apps.verification.models import ProviderMedicalAct, ActStatus
            ctx["pending_medical_acts_count"] = ProviderMedicalAct.objects.filter(
                status=ActStatus.PENDING
            ).count()
        except Exception:
            ctx["pending_medical_acts_count"] = 0

        return ctx


class AgentAffiliateListView(AgentRequiredMixin, TemplateView):
    template_name = "portal/agent/affiliate_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip()
        qs = Affiliate.objects.select_related("user").order_by("-registration_date")
        if q:
            qs = qs.filter(full_name__icontains=q) | qs.filter(niss__icontains=q)
        ctx["affiliates"] = qs[:50]
        ctx["q"] = q
        return ctx

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        if request.headers.get("HX-Request"):
            return render(request, "portal/agent/partials/affiliate_rows.html", ctx)
        return render(request, self.template_name, ctx)


class AgentAffiliateDetailView(AgentRequiredMixin, TemplateView):
    template_name = "portal/agent/affiliate_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        affiliate = get_object_or_404(
            Affiliate.objects.select_related("user").prefetch_related("dependents", "contributions"),
            pk=kwargs["pk"],
        )
        ctx["affiliate"] = affiliate

        try:
            ctx["card"] = affiliate.health_card
        except HealthCard.DoesNotExist:
            ctx["card"] = None

        tab = self.request.GET.get("tab", "info")
        ctx["tab"] = tab
        ctx["tab_choices"] = [
            ("info", "Informações"),
            ("contributions", "Cotizações"),
            ("card", "Carta"),
            ("dependents", "Dependentes"),
        ]
        return ctx

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        tab = ctx["tab"]
        if request.headers.get("HX-Request"):
            tab_template_map = {
                "info": "portal/agent/partials/tab_info.html",
                "contributions": "portal/agent/partials/tab_contributions.html",
                "card": "portal/agent/partials/tab_card.html",
                "dependents": "portal/agent/partials/tab_dependents.html",
            }
            tmpl = tab_template_map.get(tab, "portal/agent/partials/tab_info.html")
            return render(request, tmpl, ctx)
        return render(request, self.template_name, ctx)


class AgentAffiliateCreateView(AgentRequiredMixin, View):
    template_name = "portal/agent/affiliate_form.html"

    def get(self, request):
        form = AffiliateCreateForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = AffiliateCreateForm(request.POST)
        if form.is_valid():
            from django.contrib.auth import get_user_model
            import uuid

            User = get_user_model()
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            if User.objects.filter(email=email).exists():
                form.add_error("email", "Este email já está registado.")
                return render(request, self.template_name, {"form": form})

            user = User.objects.create_user(
                email=email,
                password=password,
                role="CITIZEN",
            )

            # Gera NISS único
            niss_base = f"GW{user.pk:010d}"

            affiliate = form.save(commit=False)
            affiliate.user = user
            affiliate.niss = niss_base
            affiliate.save()

            messages.success(request, f"Afiliado {affiliate.full_name} criado com sucesso.")
            return redirect("agent-affiliate-detail", pk=affiliate.pk)

        return render(request, self.template_name, {"form": form})


class AgentCardView(AgentRequiredMixin, TemplateView):
    template_name = "portal/agent/card_view.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        affiliate = get_object_or_404(Affiliate, pk=kwargs["pk"])
        ctx["affiliate"] = affiliate
        try:
            ctx["card"] = affiliate.health_card
        except HealthCard.DoesNotExist:
            ctx["card"] = None
        return ctx


class AgentCardCreateView(AgentRequiredMixin, View):
    """POST — cria ou renova a carta de um afiliado."""

    def post(self, request, pk):
        affiliate = get_object_or_404(Affiliate, pk=pk)

        # Se já existir carta, revogar e criar nova
        try:
            old_card = affiliate.health_card
            from apps.cards.models import CardStatus
            old_card.status = CardStatus.CANCELLED
            old_card.save()
        except HealthCard.DoesNotExist:
            pass

        card = HealthCard.objects.create(
            affiliate=affiliate,
            created_by=request.user,
        )
        messages.success(request, f"Carta {card.card_number} emitida com sucesso.")
        return redirect("agent-affiliate-card", pk=pk)


class AgentVerificationLogView(AgentRequiredMixin, TemplateView):
    template_name = "portal/agent/verification_logs.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = VerificationLog.objects.select_related("verifier", "card").order_by("-verified_at")

        result_filter = self.request.GET.get("result", "")
        if result_filter:
            qs = qs.filter(result=result_filter)

        ctx["logs"] = qs[:100]
        ctx["result_filter"] = result_filter
        from apps.verification.models import VerificationResult
        ctx["result_choices"] = VerificationResult.choices
        return ctx

    def get(self, request, *args, **kwargs):
        ctx = self.get_context_data(**kwargs)
        if request.headers.get("HX-Request"):
            return render(request, "portal/agent/partials/log_rows.html", ctx)
        return render(request, self.template_name, ctx)

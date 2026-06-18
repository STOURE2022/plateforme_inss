import time

from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.mixins import ProviderRequiredMixin
from apps.cards.models import HealthCard, CardStatus
from apps.cards.services.qr_service import QRTokenService
from apps.cards.exceptions import HealthCardVerificationError

from .models import VerificationLog, VerificationResult


def _get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class ProviderDashboardView(ProviderRequiredMixin, TemplateView):
    template_name = "portal/provider/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()

        my_logs = VerificationLog.objects.filter(verifier=self.request.user)
        today_logs = my_logs.filter(verified_at__date=today)

        total_today = today_logs.count()
        success_today = today_logs.filter(result=VerificationResult.SUCCESS).count()
        success_rate = round((success_today / total_today * 100), 1) if total_today > 0 else 0.0

        ctx["total_today"] = total_today
        ctx["success_today"] = success_today
        ctx["success_rate"] = success_rate
        return ctx


class ProviderVerifyView(ProviderRequiredMixin, View):
    template_name = "portal/provider/verify.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        start_time = time.monotonic()
        token = request.POST.get("token", "").strip()
        is_htmx = request.headers.get("HX-Request")

        if not token:
            ctx = {"error": "Por favor, insira o token do QR code.", "success": False}
            tmpl = "portal/provider/partials/verify_result.html" if is_htmx else self.template_name
            return render(request, tmpl, ctx)

        qr_service = QRTokenService()
        verifier = request.user
        verifier_ip = _get_client_ip(request)

        try:
            payload = qr_service.verify_token(token)
            card_number = payload.get("card_number", "")

            try:
                card = HealthCard.objects.select_related("affiliate").get(card_number=card_number)
            except HealthCard.DoesNotExist:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                VerificationLog.objects.create(
                    verifier=verifier,
                    verifier_ip=verifier_ip,
                    verifier_role=verifier.role,
                    card_number=card_number,
                    result=VerificationResult.INVALID,
                    failure_reason="Cartão não encontrado.",
                    response_ms=elapsed_ms,
                )
                ctx = {
                    "success": False,
                    "error": "Cartão não encontrado no sistema.",
                    "token": token,
                }
                tmpl = "portal/provider/partials/verify_result.html" if is_htmx else self.template_name
                return render(request, tmpl, ctx)

            if not card.is_valid():
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                if card.status == CardStatus.SUSPENDED:
                    msg = "Cartão suspenso."
                    result_code = VerificationResult.FAILURE
                elif card.status == CardStatus.CANCELLED:
                    msg = "Cartão cancelado."
                    result_code = VerificationResult.REVOKED
                else:
                    msg = "Cartão expirado."
                    result_code = VerificationResult.EXPIRED

                VerificationLog.objects.create(
                    verifier=verifier,
                    verifier_ip=verifier_ip,
                    verifier_role=verifier.role,
                    card=card,
                    card_number=card.card_number,
                    result=result_code,
                    failure_reason=msg,
                    response_ms=elapsed_ms,
                )
                ctx = {"success": False, "error": msg, "token": token}
                tmpl = "portal/provider/partials/verify_result.html" if is_htmx else self.template_name
                return render(request, tmpl, ctx)

            # Sucesso
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            VerificationLog.objects.create(
                verifier=verifier,
                verifier_ip=verifier_ip,
                verifier_role=verifier.role,
                card=card,
                card_number=card.card_number,
                result=VerificationResult.SUCCESS,
                response_ms=elapsed_ms,
            )
            ctx = {
                "success": True,
                "card": card,
                "affiliate": card.affiliate,
                "verified_at": timezone.now(),
            }
            tmpl = "portal/provider/partials/verify_result.html" if is_htmx else self.template_name
            return render(request, tmpl, ctx)

        except HealthCardVerificationError as exc:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            err_str = str(exc)
            if "expirado" in err_str.lower():
                result_code = VerificationResult.EXPIRED
                msg = "Token expirado."
            elif "revogado" in err_str.lower():
                result_code = VerificationResult.REVOKED
                msg = "Token revogado."
            else:
                result_code = VerificationResult.INVALID
                msg = "Token inválido."

            VerificationLog.objects.create(
                verifier=verifier,
                verifier_ip=verifier_ip,
                verifier_role=verifier.role,
                result=result_code,
                failure_reason=err_str,
                response_ms=elapsed_ms,
            )
            ctx = {"success": False, "error": msg, "token": token}
            tmpl = "portal/provider/partials/verify_result.html" if is_htmx else self.template_name
            return render(request, tmpl, ctx)


class ProviderHistoryView(ProviderRequiredMixin, TemplateView):
    template_name = "portal/provider/history.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["logs"] = VerificationLog.objects.filter(
            verifier=self.request.user
        ).select_related("card").order_by("-verified_at")[:100]
        return ctx

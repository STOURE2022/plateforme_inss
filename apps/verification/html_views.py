import time

from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.mixins import ProviderRequiredMixin, AgentRequiredMixin
from apps.cards.models import HealthCard, CardStatus
from apps.cards.services.qr_service import QRTokenService
from apps.cards.exceptions import HealthCardVerificationError

from .models import VerificationLog, VerificationResult, ProviderMedicalAct, ActType, ActStatus, ProviderProfile


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

        my_acts = ProviderMedicalAct.objects.filter(provider=self.request.user)
        ctx["acts_pending"] = my_acts.filter(status=ActStatus.PENDING).count()
        ctx["acts_validated"] = my_acts.filter(status=ActStatus.VALIDATED).count()
        ctx["acts_total"] = my_acts.count()
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
            ctx = {"valid": False, "error": "Por favor, insira o token do QR code.", "error_code": "EMPTY"}
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
                    "valid": False,
                    "error": "Cartão não encontrado no sistema.",
                    "error_code": "NOT_FOUND",
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
                ctx = {"valid": False, "error": msg, "error_code": result_code}
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
                "valid": True,
                "affiliate_name": card.affiliate.full_name,
                "card_number": card.card_number,
                "niss": card.affiliate.niss,
                "expiry_date": card.expiry_date.strftime("%d/%m/%Y"),
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
            ctx = {"valid": False, "error": msg, "error_code": result_code}
            tmpl = "portal/provider/partials/verify_result.html" if is_htmx else self.template_name
            return render(request, tmpl, ctx)


class ProviderVerifyByNumberView(ProviderRequiredMixin, View):
    """Vérification par numéro de carte (sans token JWS)."""

    def post(self, request):
        start_time = time.monotonic()
        card_number = request.POST.get("card_number", "").strip().upper()
        is_htmx = request.headers.get("HX-Request")
        verifier = request.user
        verifier_ip = _get_client_ip(request)

        if not card_number:
            ctx = {"valid": False, "error": "Por favor, insira o número do cartão.", "error_code": "EMPTY"}
            return render(request, "portal/provider/partials/verify_result.html", ctx)

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
            ctx = {"valid": False, "error": "Cartão não encontrado no sistema.", "error_code": "NOT_FOUND"}
            return render(request, "portal/provider/partials/verify_result.html", ctx)

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        if not card.is_valid():
            if card.status == CardStatus.SUSPENDED:
                msg, result_code = "Cartão suspenso.", VerificationResult.FAILURE
            elif card.status == CardStatus.CANCELLED:
                msg, result_code = "Cartão cancelado.", VerificationResult.REVOKED
            else:
                msg, result_code = "Cartão expirado.", VerificationResult.EXPIRED

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
            ctx = {"valid": False, "error": msg, "error_code": result_code}
            return render(request, "portal/provider/partials/verify_result.html", ctx)

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
            "valid": True,
            "affiliate_name": card.affiliate.full_name,
            "card_number": card.card_number,
            "niss": card.affiliate.niss,
            "expiry_date": card.expiry_date.strftime("%d/%m/%Y"),
            "verified_at": timezone.now(),
        }
        return render(request, "portal/provider/partials/verify_result.html", ctx)


class ProviderRegisterActView(ProviderRequiredMixin, View):
    """Enregistrement d'un acte médical après vérification réussie."""

    def post(self, request):
        card_number = request.POST.get("card_number", "").strip().upper()
        act_type = request.POST.get("act_type", "").strip()
        act_date = request.POST.get("act_date", "").strip()
        estimated_amount = request.POST.get("estimated_amount", "").strip() or None
        observations = request.POST.get("observations", "").strip()

        # Validation basique
        errors = []
        if not card_number:
            errors.append("Número do cartão obrigatório.")
        if act_type not in [c[0] for c in ActType.choices]:
            errors.append("Tipo de acto inválido.")
        if not act_date:
            errors.append("Data do acto obrigatória.")

        if errors:
            return render(request, "portal/provider/partials/act_result.html", {
                "act_success": False,
                "error": " ".join(errors),
            })

        try:
            card = HealthCard.objects.select_related("affiliate").get(card_number=card_number)
        except HealthCard.DoesNotExist:
            return render(request, "portal/provider/partials/act_result.html", {
                "act_success": False,
                "error": "Cartão não encontrado.",
            })

        from datetime import date
        try:
            parsed_date = date.fromisoformat(act_date)
        except ValueError:
            return render(request, "portal/provider/partials/act_result.html", {
                "act_success": False,
                "error": "Data inválida.",
            })

        act = ProviderMedicalAct.objects.create(
            card=card,
            affiliate_name=card.affiliate.full_name,
            affiliate_niss=card.affiliate.niss,
            provider=request.user,
            act_type=act_type,
            act_date=parsed_date,
            estimated_amount=estimated_amount if estimated_amount else None,
            observations=observations,
            status=ActStatus.PENDING,
        )

        # Notificar o cidadão
        try:
            from apps.notifications.models import Notification, NotificationType
            citizen_user = card.affiliate.user
            provider_name = request.user.email
            try:
                provider_name = request.user.provider_profile.get_display_name()
            except Exception:
                pass
            Notification.objects.create(
                recipient=citizen_user,
                title="Acto médico registado no seu cartão",
                message=f"O prestador {provider_name} registou um acto '{act.get_act_type_display()}' no seu cartão em {act.act_date.strftime('%d/%m/%Y')}. Referência: {act.reference}.",
                notification_type=NotificationType.INFO,
                resource_type="medical_act",
                resource_id=str(act.pk),
            )
        except Exception:
            pass

        return render(request, "portal/provider/partials/act_result.html", {
            "act_success": True,
            "act": act,
        })


class AgentMedicalActListView(AgentRequiredMixin, TemplateView):
    template_name = "portal/agent/medical_acts/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        status_filter = self.request.GET.get("status", "PENDING")
        qs = ProviderMedicalAct.objects.select_related("card", "provider", "reviewed_by")
        if status_filter and status_filter != "ALL":
            qs = qs.filter(status=status_filter)

        # Filter by provider
        provider_filter = self.request.GET.get("provider", "")
        if provider_filter:
            qs = qs.filter(provider__email__icontains=provider_filter)
        ctx["provider_filter"] = provider_filter

        ctx["acts"] = qs[:200]
        ctx["status_filter"] = status_filter
        ctx["act_statuses"] = ActStatus.choices
        ctx["pending_count"] = ProviderMedicalAct.objects.filter(status=ActStatus.PENDING).count()

        from django.db.models import Count, Sum
        ctx["stats_by_type"] = ProviderMedicalAct.objects.values("act_type").annotate(count=Count("id")).order_by("-count")
        ctx["total_validated_amount"] = ProviderMedicalAct.objects.filter(
            status=ActStatus.VALIDATED, validated_amount__isnull=False
        ).aggregate(total=Sum("validated_amount"))["total"] or 0

        from apps.accounts.models import User, UserRole
        ctx["providers"] = User.objects.filter(role=UserRole.PROVIDER).order_by("email")
        return ctx


class AgentMedicalActReviewView(AgentRequiredMixin, View):
    template_name = "portal/agent/medical_acts/detail.html"

    def get(self, request, pk):
        act = get_object_or_404(ProviderMedicalAct, pk=pk)
        return render(request, self.template_name, {"act": act, "act_types": ActType})

    def post(self, request, pk):
        act = get_object_or_404(ProviderMedicalAct, pk=pk)
        action = request.POST.get("action")
        review_notes = request.POST.get("review_notes", "").strip()
        validated_amount = request.POST.get("validated_amount", "").strip()

        if action == "validate":
            act.status = ActStatus.VALIDATED
            if validated_amount:
                try:
                    act.validated_amount = float(validated_amount)
                except ValueError:
                    pass
        elif action == "reject":
            act.status = ActStatus.REJECTED
        else:
            return render(request, self.template_name, {
                "act": act,
                "error": "Acção inválida.",
            })

        act.reviewed_by = request.user
        act.reviewed_at = timezone.now()
        act.review_notes = review_notes
        act.save(update_fields=["status", "validated_amount", "reviewed_by", "reviewed_at", "review_notes"])

        return redirect("agent-medical-act-list")


class ProviderMyActsView(ProviderRequiredMixin, TemplateView):
    template_name = "portal/provider/my_acts.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        status_filter = self.request.GET.get("status", "")
        qs = ProviderMedicalAct.objects.filter(provider=self.request.user).select_related("card")
        if status_filter:
            qs = qs.filter(status=status_filter)
        ctx["acts"] = qs[:100]
        ctx["status_filter"] = status_filter
        ctx["act_statuses"] = ActStatus.choices
        ctx["pending_count"] = ProviderMedicalAct.objects.filter(provider=self.request.user, status=ActStatus.PENDING).count()
        return ctx


class ProviderActDetailView(ProviderRequiredMixin, View):
    template_name = "portal/provider/act_detail.html"

    def get(self, request, pk):
        act = get_object_or_404(ProviderMedicalAct, pk=pk, provider=request.user)
        return render(request, self.template_name, {"act": act})


class ProviderProfileView(ProviderRequiredMixin, View):
    template_name = "portal/provider/profile.html"

    def get(self, request):
        profile, _ = ProviderProfile.objects.get_or_create(user=request.user)
        return render(request, self.template_name, {"profile": profile})

    def post(self, request):
        profile, _ = ProviderProfile.objects.get_or_create(user=request.user)
        profile.clinic_name = request.POST.get("clinic_name", "").strip()
        profile.specialty = request.POST.get("specialty", "").strip()
        profile.phone = request.POST.get("phone", "").strip()
        profile.address = request.POST.get("address", "").strip()
        profile.license_number = request.POST.get("license_number", "").strip()
        profile.save()
        from django.contrib import messages
        messages.success(request, "Perfil atualizado com sucesso.")
        return redirect("/portal/provider/profile/")


class ProviderHistoryView(ProviderRequiredMixin, TemplateView):
    template_name = "portal/provider/history.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["logs"] = VerificationLog.objects.filter(
            verifier=self.request.user
        ).select_related("card").order_by("-verified_at")[:100]
        return ctx

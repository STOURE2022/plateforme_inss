from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from .models import User, UserRole

ROLE_REDIRECT = {
    UserRole.CITIZEN: "/portal/citizen/",
    UserRole.EMPLOYER: "/portal/employer/",
    UserRole.AGENT: "/portal/agent/",
    UserRole.PROVIDER: "/portal/provider/",
    UserRole.ADMIN: "/admin/",
    UserRole.DEPENDENT: "/portal/citizen/",
}


class HTMLLoginView(View):
    """GET/POST /auth/login/ — formulário de autenticação HTML."""

    template_name = "auth/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(ROLE_REDIRECT.get(request.user.role, "/auth/login/"))
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=email, password=password)

        if user is None:
            return render(
                request,
                self.template_name,
                {"error": "Email ou senha inválidos. Tente novamente."},
            )

        if not user.is_active:
            return render(
                request,
                self.template_name,
                {"error": "Esta conta está desativada. Contacte o INSS."},
            )

        if user.mfa_enabled:
            # Guarda o id em sessão para o passo MFA
            request.session["mfa_user_id"] = user.pk
            return redirect("/auth/mfa/")

        login(request, user)
        next_url = request.GET.get("next") or ROLE_REDIRECT.get(user.role, "/auth/login/")
        return redirect(next_url)


class HTMLLogoutView(LoginRequiredMixin, View):
    login_url = "/auth/login/"

    def get(self, request):
        logout(request)
        return redirect("/auth/login/")


class HTMLMFAVerifyView(View):
    """GET/POST /auth/mfa/ — verificação TOTP."""

    template_name = "auth/mfa.html"

    def get(self, request):
        if "mfa_user_id" not in request.session:
            return redirect("/auth/login/")
        return render(request, self.template_name)

    def post(self, request):
        from .models import User
        from .services import verify_mfa_code

        user_id = request.session.get("mfa_user_id")
        if not user_id:
            return redirect("/auth/login/")

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return redirect("/auth/login/")

        code = request.POST.get("code", "").strip()
        if not verify_mfa_code(user, code):
            return render(
                request,
                self.template_name,
                {"error": "Código inválido. Verifique o seu autenticador."},
            )

        del request.session["mfa_user_id"]
        login(request, user)
        return redirect(ROLE_REDIRECT.get(user.role, "/auth/login/"))


class HTMLMFASetupView(LoginRequiredMixin, View):
    """GET /auth/mfa/setup/ — generate QR code and temp secret.
       POST /auth/mfa/setup/ — verify code, persist secret, enable MFA."""

    login_url = "/auth/login/"
    template_name = "auth/mfa_setup.html"

    def get(self, request):
        if request.user.mfa_enabled:
            return redirect("/auth/settings/security/")
        from .services import generate_mfa_secret, get_mfa_provisioning_uri, generate_qr_code_base64

        secret = generate_mfa_secret()
        request.session["mfa_pending_secret"] = secret
        request.user.mfa_secret = secret
        uri = get_mfa_provisioning_uri(request.user)
        return render(request, self.template_name, {
            "qr_b64": generate_qr_code_base64(uri),
            "secret": secret,
        })

    def post(self, request):
        from django.contrib import messages
        from .services import verify_mfa_code, get_mfa_provisioning_uri, generate_qr_code_base64

        secret = request.session.get("mfa_pending_secret")
        if not secret:
            return redirect("/auth/mfa/setup/")

        request.user.mfa_secret = secret
        code = request.POST.get("code", "").strip()

        if not verify_mfa_code(request.user, code):
            uri = get_mfa_provisioning_uri(request.user)
            return render(request, self.template_name, {
                "qr_b64": generate_qr_code_base64(uri),
                "secret": secret,
                "error": "Código inválido. Verifique o seu autenticador e tente novamente.",
            })

        request.user.mfa_secret = secret
        request.user.mfa_enabled = True
        request.user.save(update_fields=["mfa_secret", "mfa_enabled"])
        del request.session["mfa_pending_secret"]
        messages.success(request, "MFA ativado com sucesso! A sua conta está mais segura.")
        return redirect("/auth/settings/security/")


class HTMLMFADisableView(LoginRequiredMixin, View):
    """POST /auth/mfa/disable/ — verify current TOTP then disable MFA."""

    login_url = "/auth/login/"

    def post(self, request):
        from django.contrib import messages
        from .services import verify_mfa_code

        if not request.user.mfa_enabled:
            return redirect("/auth/settings/security/")

        code = request.POST.get("code", "").strip()
        if not verify_mfa_code(request.user, code):
            messages.error(request, "Código inválido. O MFA não foi desativado.")
            return redirect("/auth/settings/security/")

        request.user.mfa_enabled = False
        request.user.mfa_secret = ""
        request.user.save(update_fields=["mfa_enabled", "mfa_secret"])
        messages.success(request, "MFA desativado. Pode reativá-lo a qualquer momento.")
        return redirect("/auth/settings/security/")


class HTMLSecuritySettingsView(LoginRequiredMixin, View):
    """GET /auth/settings/security/ — MFA status + enable/disable actions."""

    login_url = "/auth/login/"
    template_name = "portal/security_settings.html"

    def get(self, request):
        return render(request, self.template_name)


class HTMLRegisterView(View):
    """GET/POST /auth/register/ — auto-inscription cidadão ou empregador."""

    template_name = "auth/register.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(ROLE_REDIRECT.get(request.user.role, "/auth/login/"))
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm_password", "")
        role_str = request.POST.get("role", "CITIZEN")
        accept = request.POST.get("accept_terms")

        errors = {}

        if not email:
            errors["email"] = "O e-mail é obrigatório."
        elif User.objects.filter(email=email).exists():
            errors["email"] = "Este e-mail já está registado."

        if len(password) < 8:
            errors["password"] = "A senha deve ter pelo menos 8 caracteres."
        elif password != confirm:
            errors["confirm_password"] = "As senhas não coincidem."

        if role_str not in ("CITIZEN", "EMPLOYER"):
            errors["role"] = "Seleccione um tipo de conta válido."

        if not accept:
            errors["terms"] = "Deve aceitar os termos para continuar."

        if errors:
            return render(request, self.template_name, {
                "errors": errors,
                "form_data": request.POST,
            })

        role = UserRole.CITIZEN if role_str == "CITIZEN" else UserRole.EMPLOYER
        user = User.objects.create_user(email=email, password=password, role=role, is_active=True)
        login(request, user)
        return redirect(ROLE_REDIRECT.get(role, "/auth/login/"))

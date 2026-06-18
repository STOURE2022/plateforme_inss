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

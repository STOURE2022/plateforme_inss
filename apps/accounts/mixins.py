from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin(LoginRequiredMixin):
    """Mixin que verifica o papel (role) do utilizador autenticado."""

    required_role = None
    login_url = "/auth/login/"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.required_role and request.user.role != self.required_role:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class CitizenRequiredMixin(RoleRequiredMixin):
    required_role = "CITIZEN"


class EmployerRequiredMixin(RoleRequiredMixin):
    required_role = "EMPLOYER"


class ProviderRequiredMixin(RoleRequiredMixin):
    required_role = "PROVIDER"


class AgentRequiredMixin(LoginRequiredMixin):
    """Aceita AGENT e ADMIN."""

    login_url = "/auth/login/"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in ("AGENT", "ADMIN"):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

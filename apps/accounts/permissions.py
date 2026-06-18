from rest_framework.permissions import BasePermission
from .models import UserRole


class IsAgent(BasePermission):
    """Acesso restrito a agentes INSS."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == UserRole.AGENT)


class IsAdminRole(BasePermission):
    """Acesso restrito a administradores."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == UserRole.ADMIN)


class IsAgentOrAdmin(BasePermission):
    """Acesso para agentes ou administradores."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (UserRole.AGENT, UserRole.ADMIN)
        )


class IsCitizen(BasePermission):
    """Acesso restrito a cidadãos."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == UserRole.CITIZEN)


class IsCitizenOrAgent(BasePermission):
    """Acesso para cidadãos ou agentes."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (UserRole.CITIZEN, UserRole.AGENT, UserRole.ADMIN)
        )


class IsProvider(BasePermission):
    """Acesso restrito a prestadores de cuidados."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == UserRole.PROVIDER)


class IsEmployer(BasePermission):
    """Acesso restrito a entidades empregadoras."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == UserRole.EMPLOYER)

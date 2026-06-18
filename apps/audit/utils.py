from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.audit.models import AuditEvent


def log_event(
    action: str,
    request=None,
    user=None,
    resource=None,
    details: dict | None = None,
    old_values: dict | None = None,
    new_values: dict | None = None,
) -> "AuditEvent":
    """
    Crée un AuditEvent.

    Usage:
        log_event('affiliate.created', request=request, resource=affiliate_instance)
        log_event('card.suspended', request=request, resource=card,
                  old_values={'status': 'ACTIVE'}, new_values={'status': 'SUSPENDED'})
    """
    from apps.audit.models import AuditEvent

    resolved_user = user
    ip_address = None
    user_agent = ""
    user_email = ""
    user_role = ""

    if request is not None:
        if request.user and request.user.is_authenticated:
            resolved_user = request.user
        ip_address = _get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

    if resolved_user is not None:
        user_email = resolved_user.email or ""
        user_role = getattr(resolved_user, "role", "")

    resource_type = ""
    resource_id = ""
    resource_repr = ""

    if resource is not None:
        resource_type = resource.__class__.__name__
        resource_id = str(getattr(resource, "pk", "") or "")
        resource_repr = str(resource)

    return AuditEvent.objects.create(
        user=resolved_user,
        user_email=user_email,
        user_role=user_role,
        ip_address=ip_address,
        user_agent=user_agent,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_repr=resource_repr,
        details=details or {},
        old_values=old_values,
        new_values=new_values,
    )


def _get_client_ip(request) -> str | None:
    """Extrait l'adresse IP réelle du client depuis les headers HTTP."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None

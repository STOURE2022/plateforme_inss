from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.cards.models import HealthCard
    from apps.contributions.models import Contribution

from apps.notifications.models import Notification, NotificationType


class NotificationService:

    @staticmethod
    def notify(
        recipient,
        title: str,
        message: str,
        notification_type: str = NotificationType.INFO,
        resource=None,
        resource_url: str = "",
    ) -> Notification:
        """Crée une notification en base pour le destinataire."""
        resource_type = ""
        resource_id = ""

        if resource is not None:
            resource_type = resource.__class__.__name__
            resource_id = str(getattr(resource, "pk", "") or "")

        return Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notification_type,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_url=resource_url,
        )

    @staticmethod
    def notify_card_expiring_soon(card: "HealthCard") -> Notification:
        """Notifie le citoyen que sa carte expire dans 30 jours."""
        recipient = card.affiliate.user
        return NotificationService.notify(
            recipient=recipient,
            title="Cartão a expirar",
            message=(
                f"O seu cartão de saúde {card.card_number} expira em 30 dias "
                f"({card.expiry_date}). Por favor, renove-o antes dessa data."
            ),
            notification_type=NotificationType.WARNING,
            resource=card,
            resource_url=f"/portal/citizen/card/",
        )

    @staticmethod
    def notify_contribution_late(contribution: "Contribution") -> Notification:
        """Notifie l'employer d'une cotisation en retard."""
        employer = contribution.employer
        if employer is None:
            return None
        recipient = employer.user
        return NotificationService.notify(
            recipient=recipient,
            title="Cotização em atraso",
            message=(
                f"A cotização {contribution.reference} referente a "
                f"{contribution.period_year}/{contribution.period_month:02d} "
                f"está em atraso. Por favor, regularize a sua situação."
            ),
            notification_type=NotificationType.ERROR,
            resource=contribution,
            resource_url=f"/portal/employer/contributions/",
        )

    @staticmethod
    def notify_card_created(card: "HealthCard") -> Notification:
        """Notifie le citoyen que sa carte a été créée."""
        recipient = card.affiliate.user
        return NotificationService.notify(
            recipient=recipient,
            title="Cartão de saúde criado",
            message=(
                f"O seu cartão de saúde {card.card_number} foi criado com sucesso. "
                f"Válido até {card.expiry_date}."
            ),
            notification_type=NotificationType.SUCCESS,
            resource=card,
            resource_url=f"/portal/citizen/card/",
        )

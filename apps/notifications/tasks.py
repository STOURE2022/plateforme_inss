from celery import shared_task
from django.utils import timezone
from datetime import timedelta


@shared_task(name="notifications.check_expiring_cards")
def check_expiring_cards():
    """
    Tâche périodique quotidienne.
    Trouve les cartes ACTIVE qui expirent dans ~30 jours (29 à 31 jours).
    Crée une notification pour chaque affilié concerné si pas déjà notifié aujourd'hui.
    """
    from apps.cards.models import HealthCard, CardStatus
    from apps.notifications.models import Notification
    from apps.notifications.services import NotificationService

    today = timezone.now().date()
    target_date_min = today + timedelta(days=29)
    target_date_max = today + timedelta(days=31)

    expiring_cards = HealthCard.objects.filter(
        status=CardStatus.ACTIVE,
        expiry_date__gte=target_date_min,
        expiry_date__lte=target_date_max,
    ).select_related("affiliate__user")

    notified_count = 0
    for card in expiring_cards:
        recipient = card.affiliate.user
        # Eviter les doublons : pas de notification du même type aujourd'hui
        already_notified = Notification.objects.filter(
            recipient=recipient,
            resource_type="HealthCard",
            resource_id=str(card.pk),
            notification_type="WARNING",
            created_at__date=today,
        ).exists()

        if not already_notified:
            NotificationService.notify_card_expiring_soon(card)
            notified_count += 1

    return f"{notified_count} notifications d'expiration créées."


@shared_task(name="notifications.check_late_contributions")
def check_late_contributions():
    """
    Tâche périodique : 1er de chaque mois.
    Trouve les contributions PENDING du mois précédent.
    Les passe en LATE et notifie l'employer.
    """
    from apps.contributions.models import Contribution, ContributionStatus
    from apps.notifications.services import NotificationService

    today = timezone.now().date()
    # Mois précédent
    if today.month == 1:
        prev_year = today.year - 1
        prev_month = 12
    else:
        prev_year = today.year
        prev_month = today.month - 1

    late_contributions = Contribution.objects.filter(
        status=ContributionStatus.PENDING,
        period_year=prev_year,
        period_month=prev_month,
    ).select_related("employer__user", "affiliate")

    updated_count = 0
    for contribution in late_contributions:
        contribution.status = ContributionStatus.LATE
        contribution.save(update_fields=["status"])
        if contribution.employer:
            NotificationService.notify_contribution_late(contribution)
        updated_count += 1

    return f"{updated_count} cotizações marcadas como LATE."

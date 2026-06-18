from django.db.models.signals import post_save
from django.dispatch import receiver


def _connect_signals():
    """Connecte les signals d'audit. Appelé depuis AuditConfig.ready()."""
    from apps.cards.models import HealthCard
    from apps.affiliates.models import Affiliate
    from apps.contributions.models import Contribution
    from apps.audit.utils import log_event

    @receiver(post_save, sender=HealthCard, weak=False)
    def audit_health_card(sender, instance, created, **kwargs):
        action = "card.created" if created else "card.updated"
        log_event(action=action, resource=instance)

    @receiver(post_save, sender=Affiliate, weak=False)
    def audit_affiliate(sender, instance, created, **kwargs):
        action = "affiliate.created" if created else "affiliate.updated"
        log_event(action=action, resource=instance)

    @receiver(post_save, sender=Contribution, weak=False)
    def audit_contribution(sender, instance, created, **kwargs):
        if created:
            log_event(action="contribution.created", resource=instance)

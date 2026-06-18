"""
Tests Lot 5 — AuditEvent, Notifications, seed_demo, OpenAPI
Minimum 20 tests pytest.
"""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.tests.factories import AdminFactory, AgentFactory, UserFactory
from tests.factories import AffiliateFactory, HealthCardFactory, ContributionFactory, EmployerProfileFactory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_client(user):
    """Retourne un APIClient authentifié JWT pour le user donné."""
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


def make_request_mock(user=None, ip="1.2.3.4", ua="TestAgent/1.0"):
    """Crée un mock de request Django pour les tests log_event."""
    req = MagicMock()
    req.user = user
    req.user.is_authenticated = user is not None
    req.META = {
        "REMOTE_ADDR": ip,
        "HTTP_USER_AGENT": ua,
    }
    return req


# ---------------------------------------------------------------------------
# 1. AuditEvent créé lors de la création d'un Affiliate (signal)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_audit_signal_affiliate_created():
    """Signal post_save Affiliate → AuditEvent 'affiliate.created' créé."""
    from apps.audit.models import AuditEvent

    initial_count = AuditEvent.objects.filter(action="affiliate.created").count()
    affiliate = AffiliateFactory()
    assert AuditEvent.objects.filter(action="affiliate.created").count() == initial_count + 1


# ---------------------------------------------------------------------------
# 2. AuditEvent créé lors de la création d'une HealthCard (signal)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_audit_signal_health_card_created():
    """Signal post_save HealthCard → AuditEvent 'card.created' créé."""
    from apps.audit.models import AuditEvent

    initial_count = AuditEvent.objects.filter(action="card.created").count()
    card = HealthCardFactory()
    assert AuditEvent.objects.filter(action="card.created").count() == initial_count + 1


# ---------------------------------------------------------------------------
# 3. log_event() avec request → capture ip_address et user_email
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_log_event_with_request_captures_ip_and_email():
    """log_event() avec request → ip_address et user_email renseignés."""
    from apps.audit.utils import log_event

    user = UserFactory()
    request = make_request_mock(user=user, ip="10.10.10.10")

    event = log_event("test.action", request=request)
    assert event.ip_address == "10.10.10.10"
    assert event.user_email == user.email


# ---------------------------------------------------------------------------
# 4. log_event() avec old_values/new_values
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_log_event_stores_old_and_new_values():
    """log_event() avec old_values/new_values → stocké correctement en JSON."""
    from apps.audit.utils import log_event

    old = {"status": "ACTIVE"}
    new = {"status": "SUSPENDED"}
    event = log_event("card.suspended", old_values=old, new_values=new)

    assert event.old_values == {"status": "ACTIVE"}
    assert event.new_values == {"status": "SUSPENDED"}


# ---------------------------------------------------------------------------
# 5. GET /api/v1/audit/ : admin peut lister → 200
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_audit_list_admin_200():
    """Admin peut lister les audit events."""
    admin = AdminFactory()
    client = make_client(admin)
    response = client.get("/api/v1/audit/")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 6. GET /api/v1/audit/ : agent ne peut pas → 403
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_audit_list_agent_403():
    """Agent ne peut PAS lister les audit events."""
    agent = AgentFactory()
    client = make_client(agent)
    response = client.get("/api/v1/audit/")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# 7. Filtre audit par action
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_audit_filter_by_action():
    """Filtre audit par action retourne uniquement les events correspondants."""
    from apps.audit.utils import log_event

    log_event("affiliate.created")
    log_event("card.suspended")

    admin = AdminFactory()
    client = make_client(admin)
    response = client.get("/api/v1/audit/?action=affiliate.created")
    assert response.status_code == 200
    data = response.json()
    results = data.get("results", data)
    for item in results:
        assert "affiliate" in item["action"]


# ---------------------------------------------------------------------------
# 8. Filtre audit par date_from/date_to
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_audit_filter_by_date_range():
    """Filtre audit par date_from/date_to."""
    from apps.audit.utils import log_event

    log_event("test.date.filter")

    admin = AdminFactory()
    client = make_client(admin)
    today = timezone.now().date().isoformat()
    response = client.get(f"/api/v1/audit/?date_from={today}T00:00:00&date_to={today}T23:59:59")
    assert response.status_code == 200
    data = response.json()
    results = data.get("results", data)
    assert len(results) >= 1


# ---------------------------------------------------------------------------
# 9. Notification créée via NotificationService.notify()
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_notification_service_notify():
    """NotificationService.notify() crée une Notification en base."""
    from apps.notifications.models import Notification
    from apps.notifications.services import NotificationService

    user = UserFactory()
    notif = NotificationService.notify(
        recipient=user,
        title="Test titre",
        message="Test message",
        notification_type="INFO",
    )
    assert notif.pk is not None
    assert Notification.objects.filter(recipient=user, title="Test titre").exists()


# ---------------------------------------------------------------------------
# 10. notify_card_created() crée notification pour le citoyen
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_notify_card_created():
    """notify_card_created() crée une notification SUCCESS pour l'affilié."""
    from apps.notifications.models import Notification, NotificationType
    from apps.notifications.services import NotificationService

    card = HealthCardFactory()
    NotificationService.notify_card_created(card)

    assert Notification.objects.filter(
        recipient=card.affiliate.user,
        notification_type=NotificationType.SUCCESS,
    ).exists()


# ---------------------------------------------------------------------------
# 11. GET /api/v1/notifications/ : citoyen voit ses notifications
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_notifications_list_own():
    """Citoyen peut lister ses propres notifications."""
    from apps.notifications.models import Notification

    user = UserFactory()
    Notification.objects.create(
        recipient=user,
        title="Ma notif",
        message="msg",
        notification_type="INFO",
    )
    client = make_client(user)
    response = client.get("/api/v1/notifications/")
    assert response.status_code == 200
    data = response.json()
    results = data.get("results", data)
    assert len(results) >= 1


# ---------------------------------------------------------------------------
# 12. Citoyen ne voit PAS les notifications des autres
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_notifications_list_isolation():
    """Citoyen ne peut PAS voir les notifications d'un autre utilisateur."""
    from apps.notifications.models import Notification

    owner = UserFactory()
    other = UserFactory()
    Notification.objects.create(
        recipient=owner,
        title="Notif de owner",
        message="msg",
        notification_type="INFO",
    )

    client = make_client(other)
    response = client.get("/api/v1/notifications/")
    assert response.status_code == 200
    data = response.json()
    results = data.get("results", data)
    # other ne doit pas voir les notifs de owner
    assert all(item["title"] != "Notif de owner" for item in results)


# ---------------------------------------------------------------------------
# 13. PATCH /api/v1/notifications/{id}/ → is_read=True, read_at renseigné
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_notification_mark_as_read():
    """PATCH notification → is_read=True, read_at renseigné."""
    from apps.notifications.models import Notification

    user = UserFactory()
    notif = Notification.objects.create(
        recipient=user,
        title="À lire",
        message="msg",
        notification_type="INFO",
        is_read=False,
    )
    client = make_client(user)
    response = client.patch(
        f"/api/v1/notifications/{notif.pk}/",
        {"is_read": True},
        format="json",
    )
    assert response.status_code == 200
    notif.refresh_from_db()
    assert notif.is_read is True
    assert notif.read_at is not None


# ---------------------------------------------------------------------------
# 14. GET /api/v1/notifications/unread_count/ → {"count": N}
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_notifications_unread_count():
    """GET unread_count retourne le bon nombre."""
    from apps.notifications.models import Notification

    user = UserFactory()
    # 3 non lues, 1 lue
    for i in range(3):
        Notification.objects.create(
            recipient=user,
            title=f"Notif {i}",
            message="msg",
            notification_type="INFO",
            is_read=False,
        )
    Notification.objects.create(
        recipient=user,
        title="Lue",
        message="msg",
        notification_type="INFO",
        is_read=True,
    )

    client = make_client(user)
    response = client.get("/api/v1/notifications/unread_count/")
    assert response.status_code == 200
    assert response.json()["count"] == 3


# ---------------------------------------------------------------------------
# 15. Tâche check_expiring_cards() → crée notification pour carte expirant dans 30j
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_check_expiring_cards_creates_notification():
    """check_expiring_cards() crée une notification pour une carte expirant dans 30j."""
    from apps.notifications.tasks import check_expiring_cards
    from apps.notifications.models import Notification
    from apps.cards.models import CardStatus

    card = HealthCardFactory()
    # Mettre la date d'expiration à 30 jours
    card.status = CardStatus.ACTIVE
    card.expiry_date = timezone.now().date() + timedelta(days=30)
    card.save(update_fields=["status", "expiry_date"])

    check_expiring_cards()

    assert Notification.objects.filter(
        recipient=card.affiliate.user,
        notification_type="WARNING",
    ).exists()


# ---------------------------------------------------------------------------
# 16. check_expiring_cards() → ne crée PAS de notification pour carte expirée dans 60j
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_check_expiring_cards_no_notification_for_far_expiry():
    """check_expiring_cards() ne crée PAS de notif pour carte expirant dans 60 jours."""
    from apps.notifications.tasks import check_expiring_cards
    from apps.notifications.models import Notification
    from apps.cards.models import CardStatus

    card = HealthCardFactory()
    card.status = CardStatus.ACTIVE
    card.expiry_date = timezone.now().date() + timedelta(days=60)
    card.save(update_fields=["status", "expiry_date"])

    initial_count = Notification.objects.filter(recipient=card.affiliate.user).count()
    check_expiring_cards()

    assert Notification.objects.filter(recipient=card.affiliate.user).count() == initial_count


# ---------------------------------------------------------------------------
# 17. check_late_contributions() → passe contributions PENDING mois précédent en LATE
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_check_late_contributions_marks_pending_as_late():
    """check_late_contributions() passe les contributions PENDING du mois précédent en LATE."""
    from apps.notifications.tasks import check_late_contributions
    from apps.contributions.models import ContributionStatus

    today = timezone.now().date()
    if today.month == 1:
        prev_year, prev_month = today.year - 1, 12
    else:
        prev_year, prev_month = today.year, today.month - 1

    contrib = ContributionFactory(
        period_year=prev_year,
        period_month=prev_month,
        status=ContributionStatus.PENDING,
    )

    check_late_contributions()

    contrib.refresh_from_db()
    assert contrib.status == ContributionStatus.LATE


# ---------------------------------------------------------------------------
# 18. seed_demo : idempotence (exécuter 2 fois ne duplique pas les données)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_seed_demo_idempotent():
    """seed_demo exécutée 2 fois ne duplique pas les données."""
    from django.core.management import call_command
    from apps.accounts.models import User
    from apps.affiliates.models import Affiliate

    call_command("seed_demo", verbosity=0)
    users_after_first = User.objects.count()
    affiliates_after_first = Affiliate.objects.count()

    call_command("seed_demo", verbosity=0)
    assert User.objects.count() == users_after_first
    assert Affiliate.objects.count() == affiliates_after_first


# ---------------------------------------------------------------------------
# 19. GET /notifications/dropdown/ → fragment HTML, contient notifications non lues
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_notifications_dropdown_html():
    """GET /notifications/dropdown/ retourne un fragment HTML avec les notifs non lues."""
    from apps.notifications.models import Notification
    from django.test import Client as DjangoClient

    user = UserFactory()
    Notification.objects.create(
        recipient=user,
        title="Notif visible",
        message="msg",
        notification_type="INFO",
        is_read=False,
    )

    client = DjangoClient()
    client.force_login(user)
    response = client.get("/notifications/dropdown/")
    assert response.status_code == 200
    assert b"Notif visible" in response.content


# ---------------------------------------------------------------------------
# 20. AuditEvent.details JSONField : stockage et récupération dict
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_audit_event_details_json():
    """AuditEvent.details JSONField stocke et retourne un dict correctement."""
    from apps.audit.utils import log_event

    details = {"extra": "data", "count": 42, "nested": {"key": "value"}}
    event = log_event("test.json.field", details=details)

    event.refresh_from_db()
    assert event.details == details
    assert event.details["nested"]["key"] == "value"

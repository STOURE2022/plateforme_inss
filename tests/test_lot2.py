"""
Tests Lot 2 — HealthCard, QR JWS, PDF WeasyPrint, Celery
Couvre les 20 cas de test requis.
"""
import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _agent_client(db):
    from apps.accounts.tests.factories import AgentFactory

    agent = AgentFactory()
    refresh = RefreshToken.for_user(agent)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client, agent


def _citizen_client_with_affiliate(affiliate):
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(affiliate.user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


def _make_card(affiliate=None, **kwargs):
    """Crée et sauvegarde un HealthCard."""
    from tests.factories import AffiliateFactory
    from apps.cards.models import HealthCard

    if affiliate is None:
        affiliate = AffiliateFactory()
    card = HealthCard(affiliate=affiliate, **kwargs)
    card.save()
    return card


def _make_expired_card(affiliate=None):
    """Crée un HealthCard avec expiry_date dans le passé, sans passer par save()."""
    from tests.factories import AffiliateFactory
    from apps.cards.models import HealthCard, CardStatus

    if affiliate is None:
        affiliate = AffiliateFactory()
    past = timezone.now().date() - timedelta(days=1)
    # On insère directement en DB pour contourner le recalcul de expiry_date dans save()
    card = HealthCard.objects.create(
        affiliate=affiliate,
        card_number=f"INSS-{affiliate.niss}-{timezone.now().year}",
        expiry_date=past,
        status=CardStatus.ACTIVE,
    )
    return card


# ===========================================================================
# TEST 1 — Génération card_number automatique au save()
# ===========================================================================

@pytest.mark.django_db
def test_card_number_auto_generated():
    from tests.factories import AffiliateFactory
    from apps.cards.models import HealthCard

    affiliate = AffiliateFactory()
    card = HealthCard(affiliate=affiliate)
    card.save()

    year = timezone.now().year
    assert card.card_number == f"INSS-{affiliate.niss}-{year}"


# ===========================================================================
# TEST 2 — Calcul expiry_date automatique (issued + 365 jours)
# ===========================================================================

@pytest.mark.django_db
def test_expiry_date_auto_calculated():
    from tests.factories import AffiliateFactory
    from apps.cards.models import HealthCard

    affiliate = AffiliateFactory()
    card = HealthCard(affiliate=affiliate)
    card.save()

    expected = card.issued_date + timedelta(days=365)
    assert card.expiry_date == expected


# ===========================================================================
# TEST 3 — generate_token() payload contient jti, card_number, status, exp, iat
# ===========================================================================

@pytest.mark.django_db
def test_generate_token_payload_fields(qr_service):
    import jwt as pyjwt

    card = _make_card()
    token = qr_service.generate_token(card)
    payload = pyjwt.decode(token, qr_service._get_public_key(), algorithms=["RS256"])

    assert "jti" in payload
    assert payload["card_number"] == card.card_number
    assert payload["status"] == card.status
    assert "exp" in payload
    assert "iat" in payload


# ===========================================================================
# TEST 4 — generate_token() stocke le jti dans card.current_token_jti
# ===========================================================================

@pytest.mark.django_db
def test_generate_token_stores_jti(qr_service):
    card = _make_card()
    qr_service.generate_token(card)

    card.refresh_from_db()
    assert card.current_token_jti != ""
    # UUID4 hex = 32 caractères
    assert len(card.current_token_jti) == 32


# ===========================================================================
# TEST 5 — verify_token() : token valide → retourne le payload
# ===========================================================================

@pytest.mark.django_db
def test_verify_token_valid_returns_payload(qr_service):
    card = _make_card()
    token = qr_service.generate_token(card)
    payload = qr_service.verify_token(token)

    assert payload["card_number"] == card.card_number


# ===========================================================================
# TEST 6 — verify_token() : token expiré → lève HealthCardVerificationError
# ===========================================================================

@pytest.mark.django_db
def test_verify_token_expired_raises_error(qr_service):
    import jwt as pyjwt
    from apps.cards.exceptions import HealthCardVerificationError

    card = _make_card()
    now = timezone.now()
    past = now - timedelta(minutes=10)
    jti = uuid.uuid4().hex

    payload = {
        "jti": jti,
        "card_number": card.card_number,
        "status": card.status,
        "exp": int(past.timestamp()),
        "iat": int((past - timedelta(minutes=5)).timestamp()),
    }

    expired_token = pyjwt.encode(payload, qr_service._get_private_key(), algorithm="RS256")

    with pytest.raises(HealthCardVerificationError, match="expirado"):
        qr_service.verify_token(expired_token)


# ===========================================================================
# TEST 7 — verify_token() : mauvais jti (rotation) → lève HealthCardVerificationError
# ===========================================================================

@pytest.mark.django_db
def test_verify_token_wrong_jti_raises_error(qr_service):
    import jwt as pyjwt
    from apps.cards.exceptions import HealthCardVerificationError

    card = _make_card()
    # Enregistre un jti légitime
    qr_service.generate_token(card)

    # Crée un token valide mais avec un jti différent (pas enregistré)
    now = timezone.now()
    exp = now + timedelta(minutes=5)
    wrong_jti = uuid.uuid4().hex

    payload = {
        "jti": wrong_jti,
        "card_number": card.card_number,
        "status": card.status,
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
    }

    fake_token = pyjwt.encode(payload, qr_service._get_private_key(), algorithm="RS256")

    with pytest.raises(HealthCardVerificationError, match="JTI"):
        qr_service.verify_token(fake_token)


# ===========================================================================
# TEST 8 — generate_qr_image() retourne bytes PNG valides
# ===========================================================================

@pytest.mark.django_db
def test_generate_qr_image_returns_valid_png(qr_service):
    card = _make_card()
    token = qr_service.generate_token(card)
    png_bytes = qr_service.generate_qr_image(token)

    # Signature PNG (magic bytes)
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"


# ===========================================================================
# TEST 9 — PDFService.generate_card_pdf() retourne bytes PDF
# ===========================================================================

@pytest.mark.django_db
def test_generate_card_pdf_returns_pdf_bytes(pdf_service):
    card = _make_card()
    pdf_bytes = pdf_service.generate_card_pdf(card)

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:4] == b"%PDF"


# ===========================================================================
# TEST 10 — GET /api/v1/cards/{id}/qr/ : retourne image/png (200)
# ===========================================================================

@pytest.mark.django_db
def test_qr_endpoint_returns_png_200(db, rsa_key_pair):
    from apps.cards.services.qr_service import QRTokenService

    private_pem, public_pem = rsa_key_pair
    client, _ = _agent_client(db)
    card = _make_card()

    with patch(
        "apps.cards.views.QRTokenService",
        return_value=QRTokenService(private_key=private_pem, public_key=public_pem),
    ):
        response = client.get(f"/api/v1/cards/{card.pk}/qr/")

    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"


# ===========================================================================
# TEST 11 — GET /api/v1/cards/{id}/qr/ : accès refusé sans auth (401)
# ===========================================================================

@pytest.mark.django_db
def test_qr_endpoint_requires_authentication():
    card = _make_card()
    client = APIClient()  # sans credentials
    response = client.get(f"/api/v1/cards/{card.pk}/qr/")
    assert response.status_code == 401


# ===========================================================================
# TEST 12 — GET /api/v1/cards/me/ : citoyen voit sa propre carte
# ===========================================================================

@pytest.mark.django_db
def test_my_card_citizen_sees_own_card():
    from tests.factories import AffiliateFactory
    from apps.cards.models import HealthCard

    affiliate = AffiliateFactory()
    card = HealthCard(affiliate=affiliate)
    card.save()

    client = _citizen_client_with_affiliate(affiliate)
    response = client.get("/api/v1/cards/me/")

    assert response.status_code == 200
    assert response.data["card_number"] == card.card_number


# ===========================================================================
# TEST 13 — GET /api/v1/cards/me/ : citoyen sans carte → 404
# ===========================================================================

@pytest.mark.django_db
def test_my_card_citizen_without_card_returns_404():
    from tests.factories import AffiliateFactory

    affiliate = AffiliateFactory()
    client = _citizen_client_with_affiliate(affiliate)
    response = client.get("/api/v1/cards/me/")

    assert response.status_code == 404


# ===========================================================================
# TEST 14 — POST /api/v1/cards/ : agent crée une carte → 201
# ===========================================================================

@pytest.mark.django_db
def test_agent_can_create_card(db):
    from tests.factories import AffiliateFactory

    client, _ = _agent_client(db)
    affiliate = AffiliateFactory()

    with patch("apps.cards.views.generate_card_pdf_task") as mock_task:
        mock_task.delay = MagicMock()
        response = client.post(
            "/api/v1/cards/",
            {"affiliate": affiliate.pk},
            format="json",
        )

    assert response.status_code == 201


# ===========================================================================
# TEST 15 — POST /api/v1/cards/ : citoyen ne peut pas créer → 403
# ===========================================================================

@pytest.mark.django_db
def test_citizen_cannot_create_card():
    from tests.factories import AffiliateFactory

    affiliate = AffiliateFactory()
    other_affiliate = AffiliateFactory()
    client = _citizen_client_with_affiliate(affiliate)

    response = client.post(
        "/api/v1/cards/",
        {"affiliate": other_affiliate.pk},
        format="json",
    )

    assert response.status_code == 403


# ===========================================================================
# TEST 16 — GET /api/v1/cards/{id}/pdf/ : agent peut télécharger le PDF
# ===========================================================================

@pytest.mark.django_db
def test_agent_can_download_pdf(db, rsa_key_pair):
    from apps.cards.services.qr_service import QRTokenService
    from apps.cards.services.pdf_service import PDFService

    private_pem, public_pem = rsa_key_pair
    client, _ = _agent_client(db)
    card = _make_card()

    qr_svc = QRTokenService(private_key=private_pem, public_key=public_pem)
    pdf_svc = PDFService(qr_service=qr_svc)

    with patch("apps.cards.views.PDFService", return_value=pdf_svc):
        response = client.get(f"/api/v1/cards/{card.pk}/pdf/")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


# ===========================================================================
# TEST 17 — is_valid() : carte ACTIVE non expirée → True
# ===========================================================================

@pytest.mark.django_db
def test_is_valid_active_not_expired():
    from apps.cards.models import CardStatus

    card = _make_card()

    assert card.status == CardStatus.ACTIVE
    assert card.expiry_date > timezone.now().date()
    assert card.is_valid() is True


# ===========================================================================
# TEST 18 — is_valid() : carte SUSPENDED → False
# ===========================================================================

@pytest.mark.django_db
def test_is_valid_suspended_card():
    from apps.cards.models import CardStatus

    card = _make_card(status=CardStatus.SUSPENDED)
    assert card.is_valid() is False


# ===========================================================================
# TEST 19 — is_valid() : carte ACTIVE expirée → False
# ===========================================================================

@pytest.mark.django_db
def test_is_valid_active_but_expired():
    card = _make_expired_card()
    assert card.is_valid() is False


# ===========================================================================
# TEST 20 — expire_cards() : passe bien en EXPIRED les cartes expirées
# ===========================================================================

@pytest.mark.django_db
def test_expire_cards_task_marks_expired_cards():
    from apps.cards.models import CardStatus
    from apps.cards.tasks import expire_cards

    # Carte avec expiry_date dans le passé
    card_past = _make_expired_card()

    # Carte valide (expiry_date dans le futur via save() normal)
    card_future = _make_card()

    count = expire_cards()

    card_past.refresh_from_db()
    card_future.refresh_from_db()

    assert card_past.status == CardStatus.EXPIRED
    assert card_future.status == CardStatus.ACTIVE
    assert count >= 1

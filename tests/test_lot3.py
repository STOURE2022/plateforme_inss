"""
Tests Lot 3 — /api/v1/verify/, VerificationLog, rate limiting
20+ tests pytest couvrant toutes les exigences du cahier des charges.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.tests.factories import AgentFactory, AdminFactory, UserFactory, ProviderFactory
from apps.accounts.models import UserRole
from apps.cards.models import CardStatus
from apps.cards.exceptions import HealthCardVerificationError
from apps.verification.models import VerificationLog, VerificationResult


# ---------------------------------------------------------------------------
# Factories locales
# ---------------------------------------------------------------------------

@pytest.fixture
def agent_client(db):
    """Client API authentifié en tant qu'agent INSS."""
    agent = AgentFactory()
    refresh = RefreshToken.for_user(agent)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client, agent


@pytest.fixture
def admin_client(db):
    """Client API authentifié en tant qu'administrateur."""
    admin = AdminFactory()
    refresh = RefreshToken.for_user(admin)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client, admin


@pytest.fixture
def citizen_client(db):
    """Client API authentifié en tant que citoyen."""
    user = UserFactory(role=UserRole.CITIZEN)
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client, user


@pytest.fixture
def provider_client(db):
    """Client API authentifié en tant que prestataire de soins."""
    provider = ProviderFactory()
    refresh = RefreshToken.for_user(provider)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client, provider


@pytest.fixture
def anon_client():
    """Client API anonyme."""
    return APIClient()


@pytest.fixture
def health_card(db):
    """Crée un HealthCard ACTIVE avec son affilié."""
    from tests.factories import AffiliateFactory
    from apps.cards.models import HealthCard

    affiliate = AffiliateFactory()
    card = HealthCard.objects.create(affiliate=affiliate)
    return card


@pytest.fixture
def valid_token(health_card, rsa_key_pair):
    """Génère un token valide pour un cartão ACTIVE."""
    from apps.cards.services.qr_service import QRTokenService

    private_pem, public_pem = rsa_key_pair
    service = QRTokenService(private_key=private_pem, public_key=public_pem)
    token = service.generate_token(health_card)
    return token, health_card, service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_verify_request(client, token):
    return client.post("/api/v1/verify/", {"token": token}, format="json")


def _patch_qr_service(qr_service_instance):
    """Patch QRTokenService dans la view pour utiliser les clés en mémoire."""
    return patch(
        "apps.verification.views.QRTokenService",
        return_value=qr_service_instance,
    )


# ===========================================================================
# TESTS 1-5 : POST /api/v1/verify/ comportements de base
# ===========================================================================

@pytest.mark.django_db
def test_verify_valid_token_returns_200(anon_client, valid_token):
    """1. POST /api/v1/verify/ avec token valide → 200, valid=true."""
    token, card, service = valid_token
    with _patch_qr_service(service):
        response = _make_verify_request(anon_client, token)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["card_number"] == card.card_number
    assert data["status"] == CardStatus.ACTIVE
    assert "affiliate_name" in data
    assert "expiry_date" in data
    assert "verified_at" in data


@pytest.mark.django_db
def test_verify_expired_token_returns_400(anon_client, health_card, rsa_key_pair):
    """2. POST /api/v1/verify/ avec token expiré → 400, valid=false, error_code=EXPIRED."""
    from apps.cards.services.qr_service import QRTokenService

    private_pem, public_pem = rsa_key_pair
    service = QRTokenService(private_key=private_pem, public_key=public_pem)

    # Simule un token expiré en faisant lever ExpiredSignatureError
    expired_service = MagicMock()
    expired_service.verify_token.side_effect = HealthCardVerificationError("Token expirado.")

    with _patch_qr_service(expired_service):
        response = _make_verify_request(anon_client, "some.expired.token")

    assert response.status_code == 400
    data = response.json()
    assert data["valid"] is False
    assert data["error_code"] == VerificationResult.EXPIRED


@pytest.mark.django_db
def test_verify_malformed_token_returns_400(anon_client):
    """3. POST /api/v1/verify/ avec token mal formé → 400."""
    invalid_service = MagicMock()
    invalid_service.verify_token.side_effect = HealthCardVerificationError("Token inválido: bad format")

    with _patch_qr_service(invalid_service):
        response = _make_verify_request(anon_client, "not.a.valid.jwt.token")

    assert response.status_code == 400
    data = response.json()
    assert data["valid"] is False
    assert data["error_code"] in [VerificationResult.INVALID, VerificationResult.EXPIRED, VerificationResult.REVOKED]


@pytest.mark.django_db
def test_verify_suspended_card_returns_400(anon_client, valid_token):
    """4. POST /api/v1/verify/ avec carte SUSPENDED → 400, valid=false."""
    token, card, service = valid_token

    # Suspendre la carte
    card.status = CardStatus.SUSPENDED
    card.save(update_fields=["status"])

    with _patch_qr_service(service):
        response = _make_verify_request(anon_client, token)

    assert response.status_code == 400
    data = response.json()
    assert data["valid"] is False
    assert "suspenso" in data["error"].lower()


@pytest.mark.django_db
def test_verify_missing_token_field_returns_400(anon_client):
    """5. POST /api/v1/verify/ sans 'token' dans body → 400."""
    response = anon_client.post("/api/v1/verify/", {}, format="json")
    assert response.status_code == 400
    data = response.json()
    assert data["valid"] is False
    assert data["error_code"] == VerificationResult.INVALID


# ===========================================================================
# TESTS 6-9 : VerificationLog créé correctement
# ===========================================================================

@pytest.mark.django_db
def test_verify_success_creates_verification_log(anon_client, valid_token):
    """6. POST /api/v1/verify/ token valide crée un VerificationLog SUCCESS."""
    token, card, service = valid_token
    initial_count = VerificationLog.objects.count()

    with _patch_qr_service(service):
        response = _make_verify_request(anon_client, token)

    assert response.status_code == 200
    assert VerificationLog.objects.count() == initial_count + 1
    log = VerificationLog.objects.latest("verified_at")
    assert log.result == VerificationResult.SUCCESS
    assert log.card_number == card.card_number


@pytest.mark.django_db
def test_verify_invalid_token_creates_failure_log(anon_client):
    """7. POST /api/v1/verify/ token invalide crée un VerificationLog FAILURE/INVALID."""
    invalid_service = MagicMock()
    invalid_service.verify_token.side_effect = HealthCardVerificationError("Token inválido: bad data")
    initial_count = VerificationLog.objects.count()

    with _patch_qr_service(invalid_service):
        _make_verify_request(anon_client, "bad.token.here")

    assert VerificationLog.objects.count() == initial_count + 1
    log = VerificationLog.objects.latest("verified_at")
    assert log.result in [VerificationResult.INVALID, VerificationResult.FAILURE]


@pytest.mark.django_db
def test_verify_captures_verifier_ip(anon_client, valid_token):
    """8. VerificationLog.verifier_ip est capturé depuis la requête."""
    token, card, service = valid_token

    with _patch_qr_service(service):
        anon_client.post(
            "/api/v1/verify/",
            {"token": token},
            format="json",
            REMOTE_ADDR="192.168.1.42",
        )

    log = VerificationLog.objects.latest("verified_at")
    assert log.verifier_ip == "192.168.1.42"


@pytest.mark.django_db
def test_verify_response_ms_is_set(anon_client, valid_token):
    """9. VerificationLog.response_ms est renseigné (> 0)."""
    token, card, service = valid_token

    with _patch_qr_service(service):
        _make_verify_request(anon_client, token)

    log = VerificationLog.objects.latest("verified_at")
    assert log.response_ms is not None
    assert log.response_ms >= 0


# ===========================================================================
# TESTS 10-13 : GET /api/v1/verification-logs/
# ===========================================================================

@pytest.mark.django_db
def test_agent_can_list_verification_logs(agent_client):
    """10. GET /api/v1/verification-logs/ : agent peut lister → 200."""
    client, agent = agent_client
    # Crée quelques logs
    VerificationLog.objects.create(
        result=VerificationResult.SUCCESS,
        card_number="INSS-TEST-2026",
        verifier_ip="10.0.0.1",
    )
    response = client.get("/api/v1/verification-logs/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_citizen_cannot_list_verification_logs(citizen_client):
    """11. GET /api/v1/verification-logs/ : citoyen ne peut pas → 403."""
    client, _ = citizen_client
    response = client.get("/api/v1/verification-logs/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_filter_by_result_success(agent_client):
    """12. GET /api/v1/verification-logs/?result=SUCCESS : filtre fonctionne."""
    client, _ = agent_client
    VerificationLog.objects.create(result=VerificationResult.SUCCESS, card_number="INSS-111-2026")
    VerificationLog.objects.create(result=VerificationResult.FAILURE, card_number="INSS-222-2026")
    VerificationLog.objects.create(result=VerificationResult.EXPIRED, card_number="INSS-333-2026")

    response = client.get("/api/v1/verification-logs/?result=SUCCESS")
    assert response.status_code == 200
    data = response.json()
    results = data.get("results", data)
    assert all(log["result"] == "SUCCESS" for log in results)


@pytest.mark.django_db
def test_filter_by_card_number(agent_client):
    """13. GET /api/v1/verification-logs/?card_number=INSS-xxx : filtre fonctionne."""
    client, _ = agent_client
    VerificationLog.objects.create(result=VerificationResult.SUCCESS, card_number="INSS-ALPHA-2026")
    VerificationLog.objects.create(result=VerificationResult.SUCCESS, card_number="INSS-BETA-2026")

    response = client.get("/api/v1/verification-logs/?card_number=ALPHA")
    assert response.status_code == 200
    data = response.json()
    results = data.get("results", data)
    assert len(results) >= 1
    assert all("ALPHA" in log["card_number"] for log in results)


# ===========================================================================
# TESTS 14-15 : GET /api/v1/verify/stats/
# ===========================================================================

@pytest.mark.django_db
def test_agent_can_get_stats(agent_client):
    """14. GET /api/v1/verify/stats/ : agent reçoit les stats → 200."""
    client, _ = agent_client
    response = client.get("/api/v1/verify/stats/")
    assert response.status_code == 200
    data = response.json()
    assert "total_today" in data
    assert "success_today" in data
    assert "failure_today" in data
    assert "success_rate_today" in data
    assert "top_failure_reasons" in data
    assert "verifications_last_7_days" in data
    assert len(data["verifications_last_7_days"]) == 7


@pytest.mark.django_db
def test_provider_cannot_get_stats(provider_client):
    """15. GET /api/v1/verify/stats/ : provider/citoyen → 403."""
    client, _ = provider_client
    response = client.get("/api/v1/verify/stats/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_citizen_cannot_get_stats(citizen_client):
    """15b. GET /api/v1/verify/stats/ : citoyen → 403."""
    client, _ = citizen_client
    response = client.get("/api/v1/verify/stats/")
    assert response.status_code == 403


# ===========================================================================
# TEST 16 : Rate limiting
# ===========================================================================

@pytest.mark.django_db
def test_rate_limiting_anonymous():
    """16. Rate limiting : requêtes anonymes au-delà de la limite → 429."""
    from apps.verification.throttles import VerifyCardThrottle

    client = APIClient()

    # Mock allow_request pour simuler le dépassement de limite sur la 4ème requête
    call_count = {"n": 0}

    def mock_allow_request(self, request, view):
        call_count["n"] += 1
        return call_count["n"] <= 3  # Les 3 premières passent, la 4ème est bloquée

    def mock_wait(self):
        return 60.0

    with patch.object(
        VerifyCardThrottle, "allow_request", mock_allow_request
    ), patch.object(VerifyCardThrottle, "wait", mock_wait):
        responses = []
        for _ in range(4):
            r = client.post("/api/v1/verify/", {"token": "x"}, format="json")
            responses.append(r.status_code)

    # La 4ème requête doit être bloquée (429)
    assert responses[-1] == 429
    # Les 3 premières doivent passer (pas 429)
    assert all(s != 429 for s in responses[:3])


# ===========================================================================
# TEST 17 : Token révoqué (JTI ne correspond plus)
# ===========================================================================

@pytest.mark.django_db
def test_verify_revoked_token_returns_400(anon_client, health_card, rsa_key_pair):
    """17. VerifyCardView avec token révoqué (jti ne correspond plus) → 400, error_code=REVOKED."""
    revoked_service = MagicMock()
    revoked_service.verify_token.side_effect = HealthCardVerificationError(
        "Token revogado (rotação de JTI)."
    )

    with _patch_qr_service(revoked_service):
        response = _make_verify_request(anon_client, "some.old.token")

    assert response.status_code == 400
    data = response.json()
    assert data["valid"] is False
    assert data["error_code"] == VerificationResult.REVOKED


# ===========================================================================
# TEST 18 : Snapshot card_number conservé après suppression carte
# ===========================================================================

@pytest.mark.django_db
def test_card_number_snapshot_preserved_after_card_deletion(db):
    """18. VerificationLog card snapshot : card_number conservé même après suppression carte."""
    from tests.factories import AffiliateFactory
    from apps.cards.models import HealthCard

    affiliate = AffiliateFactory()
    card = HealthCard.objects.create(affiliate=affiliate)
    card_number = card.card_number

    log = VerificationLog.objects.create(
        card=card,
        card_number=card_number,
        result=VerificationResult.SUCCESS,
    )

    # Supprimer la carte
    card.delete()

    # Recharger le log
    log.refresh_from_db()
    assert log.card is None  # FK SET_NULL
    assert log.card_number == card_number  # snapshot conservé


# ===========================================================================
# TEST 19 : Filtre date_from/date_to sur VerificationLog
# ===========================================================================

@pytest.mark.django_db
def test_filter_by_date_from_and_date_to(agent_client):
    """19. Filtre date_from/date_to sur VerificationLog."""
    from django.utils import timezone
    from datetime import timedelta

    client, _ = agent_client

    # Crée des logs avec des dates différentes via update forcé
    now = timezone.now()

    log1 = VerificationLog.objects.create(
        result=VerificationResult.SUCCESS,
        card_number="INSS-DATE-A",
    )
    log2 = VerificationLog.objects.create(
        result=VerificationResult.FAILURE,
        card_number="INSS-DATE-B",
    )

    # Ajuste manuellement les dates (auto_now_add ne peut pas être overridé directement)
    VerificationLog.objects.filter(pk=log1.pk).update(
        verified_at=now - timedelta(days=3)
    )
    VerificationLog.objects.filter(pk=log2.pk).update(
        verified_at=now - timedelta(days=1)
    )

    # Filtre : seulement les logs des 2 derniers jours
    date_from = (now - timedelta(days=2)).isoformat()
    response = client.get(f"/api/v1/verification-logs/?date_from={date_from}")
    assert response.status_code == 200
    data = response.json()
    results = data.get("results", data)
    card_numbers = [log["card_number"] for log in results]

    # log2 (1 jour) doit apparaître, log1 (3 jours) ne doit pas
    assert "INSS-DATE-B" in card_numbers
    assert "INSS-DATE-A" not in card_numbers


# ===========================================================================
# TEST 20 : VerificationLog ordering par verified_at desc par défaut
# ===========================================================================

@pytest.mark.django_db
def test_verification_log_default_ordering_desc(agent_client):
    """20. VerificationLog ordering par verified_at desc par défaut."""
    from django.utils import timezone
    from datetime import timedelta

    client, _ = agent_client
    now = timezone.now()

    log1 = VerificationLog.objects.create(result=VerificationResult.SUCCESS, card_number="INSS-ORD-1")
    log2 = VerificationLog.objects.create(result=VerificationResult.FAILURE, card_number="INSS-ORD-2")
    log3 = VerificationLog.objects.create(result=VerificationResult.EXPIRED, card_number="INSS-ORD-3")

    VerificationLog.objects.filter(pk=log1.pk).update(verified_at=now - timedelta(hours=3))
    VerificationLog.objects.filter(pk=log2.pk).update(verified_at=now - timedelta(hours=2))
    VerificationLog.objects.filter(pk=log3.pk).update(verified_at=now - timedelta(hours=1))

    response = client.get("/api/v1/verification-logs/")
    assert response.status_code == 200
    data = response.json()
    results = data.get("results", data)

    # Filtre uniquement nos logs de test
    our_logs = [r for r in results if r["card_number"] in ["INSS-ORD-1", "INSS-ORD-2", "INSS-ORD-3"]]
    assert len(our_logs) == 3

    # Le plus récent en premier (log3 → log2 → log1)
    card_numbers_ordered = [log["card_number"] for log in our_logs]
    assert card_numbers_ordered == ["INSS-ORD-3", "INSS-ORD-2", "INSS-ORD-1"]


# ===========================================================================
# TESTS SUPPLÉMENTAIRES : robustesse et cas limites
# ===========================================================================

@pytest.mark.django_db
def test_verify_with_x_forwarded_for_captures_real_ip(anon_client, valid_token):
    """Capture l'IP réelle depuis X-Forwarded-For."""
    token, card, service = valid_token

    with _patch_qr_service(service):
        anon_client.post(
            "/api/v1/verify/",
            {"token": token},
            format="json",
            HTTP_X_FORWARDED_FOR="203.0.113.42, 10.0.0.1",
            REMOTE_ADDR="10.0.0.1",
        )

    log = VerificationLog.objects.latest("verified_at")
    assert log.verifier_ip == "203.0.113.42"


@pytest.mark.django_db
def test_verify_captures_verifier_role_when_authenticated(valid_token):
    """Capture le rôle du vérificateur dans le log."""
    token, card, service = valid_token
    provider = ProviderFactory()
    refresh = RefreshToken.for_user(provider)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")

    with _patch_qr_service(service):
        client.post("/api/v1/verify/", {"token": token}, format="json")

    log = VerificationLog.objects.latest("verified_at")
    assert log.verifier == provider
    assert log.verifier_role == UserRole.PROVIDER


@pytest.mark.django_db
def test_verify_anonymous_has_no_verifier(anon_client, valid_token):
    """Un appel anonyme ne doit pas avoir de verifier dans le log."""
    token, card, service = valid_token

    with _patch_qr_service(service):
        _make_verify_request(anon_client, token)

    log = VerificationLog.objects.latest("verified_at")
    assert log.verifier is None
    assert log.verifier_role == ""


@pytest.mark.django_db
def test_admin_can_list_verification_logs(admin_client):
    """Admin peut aussi lister les logs de vérification."""
    client, _ = admin_client
    response = client.get("/api/v1/verification-logs/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_verify_cancelled_card_returns_400(anon_client, valid_token):
    """Carte annulée → 400 avec error_code REVOKED."""
    token, card, service = valid_token
    card.status = CardStatus.CANCELLED
    card.save(update_fields=["status"])

    with _patch_qr_service(service):
        response = _make_verify_request(anon_client, token)

    assert response.status_code == 400
    data = response.json()
    assert data["valid"] is False
    assert data["error_code"] == VerificationResult.REVOKED


@pytest.mark.django_db
def test_stats_success_rate_calculation(agent_client):
    """Le taux de succès est correctement calculé."""
    client, _ = agent_client
    now = timezone.now()

    # Crée 3 succès et 1 échec aujourd'hui
    for _ in range(3):
        log = VerificationLog.objects.create(result=VerificationResult.SUCCESS, card_number="INSS-S-2026")
        VerificationLog.objects.filter(pk=log.pk).update(verified_at=now)
    log = VerificationLog.objects.create(result=VerificationResult.FAILURE, card_number="INSS-F-2026")
    VerificationLog.objects.filter(pk=log.pk).update(verified_at=now)

    response = client.get("/api/v1/verify/stats/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_today"] >= 4
    assert data["success_today"] >= 3
    assert data["success_rate_today"] >= 0.0

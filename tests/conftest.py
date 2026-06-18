import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(db):
    from apps.accounts.tests.factories import UserFactory
    from rest_framework_simplejwt.tokens import RefreshToken

    user = UserFactory()
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client, user


# ------------------------------------------------------------------
# Fixtures RSA en mémoire pour les tests du Lot 2
# ------------------------------------------------------------------

@pytest.fixture(scope="session")
def rsa_key_pair():
    """Génère une paire de clés RSA 2048 bits en mémoire pour les tests."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


@pytest.fixture
def qr_service(rsa_key_pair):
    """Instance de QRTokenService utilisant des clés RSA en mémoire."""
    from apps.cards.services.qr_service import QRTokenService

    private_pem, public_pem = rsa_key_pair
    return QRTokenService(private_key=private_pem, public_key=public_pem)


@pytest.fixture
def pdf_service(qr_service):
    """Instance de PDFService utilisant le qr_service de test."""
    from apps.cards.services.pdf_service import PDFService

    return PDFService(qr_service=qr_service)

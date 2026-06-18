import uuid
import io
from datetime import timedelta

import jwt
import qrcode
from django.conf import settings
from django.utils import timezone

from apps.cards.exceptions import HealthCardVerificationError


def _load_private_key() -> bytes:
    """Carrega a chave privada RSA a partir do caminho configurado."""
    with open(settings.INSS_PRIVATE_KEY_PATH, "rb") as f:
        return f.read()


def _load_public_key() -> bytes:
    """Carrega a chave pública RSA a partir do caminho configurado."""
    with open(settings.INSS_PUBLIC_KEY_PATH, "rb") as f:
        return f.read()


class QRTokenService:
    """Gera e verifica os tokens JWS assinados RSA para o QR code."""

    def __init__(self, private_key: bytes = None, public_key: bytes = None):
        """
        Permite injectar chaves em memória (útil para testes).
        Se não fornecidas, carrega dos ficheiros configurados.
        """
        self._private_key = private_key
        self._public_key = public_key

    def _get_private_key(self) -> bytes:
        if self._private_key is not None:
            return self._private_key
        return _load_private_key()

    def _get_public_key(self) -> bytes:
        if self._public_key is not None:
            return self._public_key
        return _load_public_key()

    def generate_token(self, card) -> str:
        """
        Cria um token JWS (RS256) contendo:
        {
          "jti": "<uuid4>",
          "card_number": "<card.card_number>",
          "status": "<card.status>",
          "exp": <now + 5min timestamp>,
          "iat": <now timestamp>
        }
        Nenhum dado pessoal incluído.
        Armazena o jti em card.current_token_jti e card.token_expires_at.
        """
        now = timezone.now()
        exp = now + timedelta(minutes=5)
        jti = uuid.uuid4().hex

        payload = {
            "jti": jti,
            "card_number": card.card_number,
            "status": card.status,
            "exp": int(exp.timestamp()),
            "iat": int(now.timestamp()),
        }

        private_key = self._get_private_key()
        token = jwt.encode(payload, private_key, algorithm="RS256")

        # Atualiza o cartão com o novo jti
        card.current_token_jti = jti
        card.token_issued_at = now
        card.token_expires_at = exp
        card.save(update_fields=["current_token_jti", "token_issued_at", "token_expires_at"])

        return token

    def verify_token(self, token: str) -> dict:
        """
        Verifica a assinatura RS256, expiração e que jti == card.current_token_jti (rotação).
        Levanta HealthCardVerificationError se inválido.
        Retorna o payload decodificado se válido.
        """
        from apps.cards.models import HealthCard

        public_key = self._get_public_key()

        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                options={"verify_exp": True},
            )
        except jwt.ExpiredSignatureError:
            raise HealthCardVerificationError("Token expirado.")
        except jwt.InvalidTokenError as exc:
            raise HealthCardVerificationError(f"Token inválido: {exc}")

        # Verifica rotação: jti deve corresponder ao token atual do cartão
        card_number = payload.get("card_number")
        jti = payload.get("jti")

        try:
            card = HealthCard.objects.get(card_number=card_number)
        except HealthCard.DoesNotExist:
            raise HealthCardVerificationError("Cartão não encontrado.")

        if card.current_token_jti != jti:
            raise HealthCardVerificationError("Token revogado (rotação de JTI).")

        return payload

    def generate_qr_image(self, token: str) -> bytes:
        """
        Gera uma imagem QR code PNG (bytes) contendo o token.
        Utiliza qrcode + Pillow. Nível de correção de erros H.
        Retorna bytes PNG.
        """
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(token)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

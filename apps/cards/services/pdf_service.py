import base64
import os
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from apps.cards.services.qr_service import QRTokenService


class PDFService:
    """Gera o PDF do cartão de seguro de saúde com WeasyPrint."""

    def __init__(self, qr_service: QRTokenService = None):
        self.qr_service = qr_service or QRTokenService()

    def generate_card_pdf(self, card) -> bytes:
        """
        Gera um PDF formato cartão CR80 (85.6x54mm) contendo:
        - Cabeçalho INSS
        - Nome completo do afiliado
        - NISS
        - Número do cartão
        - Datas de emissão e validade
        - Imagem QR code
        - Estado do cartão
        """
        # Gera token e QR code
        token = self.qr_service.generate_token(card)
        qr_bytes = self.qr_service.generate_qr_image(token)
        qr_base64 = base64.b64encode(qr_bytes).decode("utf-8")

        # Mapeamento de estado para classe CSS e texto
        status_map = {
            "ACTIVE": ("active", "ATIVO"),
            "SUSPENDED": ("suspended", "SUSPENSO"),
            "EXPIRED": ("expired", "EXPIRADO"),
            "CANCELLED": ("cancelled", "CANCELADO"),
        }
        status_class, status_display = status_map.get(card.status, ("active", card.status))

        context = {
            "full_name": card.affiliate.full_name,
            "niss": card.affiliate.niss,
            "card_number": card.card_number,
            "issued_date": card.issued_date.strftime("%d/%m/%Y") if card.issued_date else "",
            "expiry_date": card.expiry_date.strftime("%d/%m/%Y") if card.expiry_date else "",
            "qr_base64": qr_base64,
            "status_class": status_class,
            "status_display": status_display,
        }

        html_content = render_to_string("cards/card_pdf.html", context)

        # Import lazy : WeasyPrint requiert GTK (Linux/Docker uniquement)
        import weasyprint  # noqa: PLC0415
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
        return pdf_bytes

    def save_card_pdf(self, card) -> str:
        """
        Gera o PDF e guarda em MEDIA_ROOT/cards/pdf/{card_number}.pdf.
        Atualiza card.pdf_file e card.pdf_generated_at.
        Retorna o path relativo.
        """
        pdf_bytes = self.generate_card_pdf(card)

        # Garante que o directório existe
        pdf_dir = Path(settings.MEDIA_ROOT) / "cards" / "pdf"
        pdf_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{card.card_number}.pdf"
        relative_path = f"cards/pdf/{filename}"
        full_path = pdf_dir / filename

        with open(full_path, "wb") as f:
            f.write(pdf_bytes)

        # Atualiza o cartão
        card.pdf_file = relative_path
        card.pdf_generated_at = timezone.now()
        card.save(update_fields=["pdf_file", "pdf_generated_at"])

        return relative_path

from celery import shared_task
from django.utils import timezone


@shared_task(name="cards.rotate_card_tokens")
def rotate_card_tokens(card_id: int) -> None:
    """
    Tarefa Celery: gera um novo token JWS para o cartão.
    Invalida o JTI antigo atualizando current_token_jti.
    """
    from apps.cards.models import HealthCard
    from apps.cards.services.qr_service import QRTokenService

    try:
        card = HealthCard.objects.get(pk=card_id)
    except HealthCard.DoesNotExist:
        return

    service = QRTokenService()
    service.generate_token(card)


@shared_task(name="cards.generate_card_pdf_task")
def generate_card_pdf_task(card_id: int) -> None:
    """
    Tarefa Celery assíncrona: gera o PDF do cartão e guarda-o.
    Disparada automaticamente na criação de um cartão.
    """
    from apps.cards.models import HealthCard
    from apps.cards.services.pdf_service import PDFService

    try:
        card = HealthCard.objects.get(pk=card_id)
    except HealthCard.DoesNotExist:
        return

    service = PDFService()
    service.save_card_pdf(card)


@shared_task(name="cards.expire_cards")
def expire_cards() -> int:
    """
    Tarefa Celery periódica: marca como EXPIRED os cartões cuja expiry_date < hoje.
    Retorna o número de cartões atualizados.
    """
    from apps.cards.models import HealthCard, CardStatus

    today = timezone.now().date()
    updated = HealthCard.objects.filter(
        status=CardStatus.ACTIVE,
        expiry_date__lt=today,
    ).update(status=CardStatus.EXPIRED)

    return updated

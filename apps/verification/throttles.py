from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class VerifyCardThrottle(AnonRateThrottle):
    """
    Limita chamadas anônimas a POST /api/v1/verify/ : 60/minuto.
    Utiliza Redis como backend.
    """
    scope = "verify_card"


class VerifyCardAuthThrottle(UserRateThrottle):
    """
    Limita chamadas autenticadas a POST /api/v1/verify/ : 300/minuto.
    Para prestadores de cuidados autenticados.
    """
    scope = "verify_card_auth"

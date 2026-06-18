from rest_framework.routers import DefaultRouter
from apps.cards.views import HealthCardViewSet

router = DefaultRouter()
router.register(r"cards", HealthCardViewSet, basename="healthcard")

urlpatterns = router.urls

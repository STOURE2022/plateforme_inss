from rest_framework.routers import DefaultRouter

from .views import BenefitTypeViewSet, BenefitRequestViewSet, BenefitDocumentViewSet, BenefitPaymentViewSet

router = DefaultRouter()
router.register(r"benefit-types", BenefitTypeViewSet, basename="benefit-type")
router.register(r"benefits", BenefitRequestViewSet, basename="benefit-request")
router.register(r"benefit-documents", BenefitDocumentViewSet, basename="benefit-document")
router.register(r"benefit-payments", BenefitPaymentViewSet, basename="benefit-payment")

urlpatterns = router.urls

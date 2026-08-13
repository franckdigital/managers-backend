from rest_framework.routers import DefaultRouter

from apps.virtual_classes.views import VirtualClassViewSet

router = DefaultRouter()
router.register('virtual-classes', VirtualClassViewSet, basename='virtual-class')

urlpatterns = router.urls

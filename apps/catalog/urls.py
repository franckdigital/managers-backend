from rest_framework.routers import DefaultRouter

from apps.catalog.views import BundleViewSet, CartViewSet, CategoryViewSet, CouponViewSet, WishlistViewSet

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('coupons', CouponViewSet, basename='coupon')
router.register('bundles', BundleViewSet, basename='bundle')
router.register('cart', CartViewSet, basename='cart')
router.register('wishlist', WishlistViewSet, basename='wishlist')

urlpatterns = router.urls

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.catalog.models import Bundle, Cart, CartItem, Category, Coupon, Wishlist
from apps.catalog.serializers import (
    BundleSerializer,
    CartItemSerializer,
    CartSerializer,
    CategorySerializer,
    CouponSerializer,
    WishlistSerializer,
)
from apps.core.mixins import AuditLogMixin
from apps.core.permissions import IsCompanyAdmin, IsSuperAdmin


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filterset_fields = ['parent', 'is_active']
    search_fields = ['name']

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [IsSuperAdmin()]


class BundleViewSet(viewsets.ModelViewSet):
    queryset = Bundle.objects.prefetch_related('courses').all()
    serializer_class = BundleSerializer
    filterset_fields = ['is_active', 'company']
    search_fields = ['title', 'description']

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [IsSuperAdmin()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        is_admin = user.is_authenticated and (user.is_superuser or user.role == 'super_admin')
        if self.request.method in permissions.SAFE_METHODS and not is_admin:
            return qs.filter(is_active=True)
        return qs


class CouponViewSet(AuditLogMixin, viewsets.ModelViewSet):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsCompanyAdmin]
    filterset_fields = ['is_active', 'company', 'discount_type']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.role == 'super_admin':
            return qs
        return qs.filter(company_id=user.company_id) | qs.filter(company__isnull=True)

    def _enforce_company_scope(self, serializer):
        user = self.request.user
        if not (user.is_superuser or user.role == 'super_admin'):
            serializer.validated_data['company'] = user.company

    def perform_create(self, serializer):
        self._enforce_company_scope(serializer)
        super().perform_create(serializer)

    def perform_update(self, serializer):
        self._enforce_company_scope(serializer)
        super().perform_update(serializer)


class CartViewSet(viewsets.GenericViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_cart(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    def list(self, request):
        cart = self.get_cart(request)
        return Response(self.get_serializer(cart).data)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        cart = self.get_cart(request)
        course_id = request.data.get('course')
        bundle_id = request.data.get('bundle')
        if bool(course_id) == bool(bundle_id):
            return Response({'detail': 'Renseignez soit un cours, soit un bundle.'}, status=status.HTTP_400_BAD_REQUEST)
        item, _ = CartItem.objects.get_or_create(cart=cart, course_id=course_id, bundle_id=bundle_id)
        return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='remove-item')
    def remove_item(self, request):
        cart = self.get_cart(request)
        course_id = request.data.get('course')
        bundle_id = request.data.get('bundle')
        if course_id:
            CartItem.objects.filter(cart=cart, course_id=course_id).delete()
        if bundle_id:
            CartItem.objects.filter(cart=cart, bundle_id=bundle_id).delete()
        return Response(self.get_serializer(cart).data)

    @action(detail=False, methods=['post'])
    def clear(self, request):
        cart = self.get_cart(request)
        cart.items.all().delete()
        return Response(self.get_serializer(cart).data)


class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

from rest_framework import serializers

from apps.catalog.models import Bundle, Cart, CartItem, Category, Coupon, Wishlist
from apps.courses.serializers import CourseListSerializer


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
        read_only_fields = ('slug',)


class BundleSerializer(serializers.ModelSerializer):
    courses_detail = CourseListSerializer(source='courses', many=True, read_only=True)
    courses_count = serializers.IntegerField(source='courses.count', read_only=True)
    list_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Bundle
        fields = '__all__'
        read_only_fields = ('slug',)


class CouponSerializer(serializers.ModelSerializer):
    is_valid_now = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = '__all__'
        read_only_fields = ('used_count',)

    def get_is_valid_now(self, obj):
        return obj.is_valid_now()


class CartItemSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_price = serializers.DecimalField(source='course.price', read_only=True, max_digits=10, decimal_places=2)
    course_thumbnail = serializers.ImageField(source='course.thumbnail', read_only=True)
    bundle_title = serializers.CharField(source='bundle.title', read_only=True)
    bundle_price = serializers.DecimalField(source='bundle.price', read_only=True, max_digits=10, decimal_places=2)

    class Meta:
        model = CartItem
        fields = (
            'id', 'cart', 'course', 'course_title', 'course_price', 'course_thumbnail',
            'bundle', 'bundle_title', 'bundle_price', 'created_at',
        )
        read_only_fields = ('cart',)

    def validate(self, attrs):
        course = attrs.get('course', getattr(self.instance, 'course', None))
        bundle = attrs.get('bundle', getattr(self.instance, 'bundle', None))
        if bool(course) == bool(bundle):
            raise serializers.ValidationError("Renseignez soit un cours, soit un bundle (jamais les deux).")
        return attrs


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ('id', 'user', 'items', 'total', 'created_at')
        read_only_fields = ('user',)


class WishlistSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Wishlist
        fields = '__all__'
        read_only_fields = ('user',)

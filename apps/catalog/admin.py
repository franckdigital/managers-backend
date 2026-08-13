from django.contrib import admin

from apps.catalog.models import Cart, CartItem, Category, Coupon, Wishlist


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'is_active')
    search_fields = ('name',)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'company', 'discount_type', 'amount', 'valid_from', 'valid_to', 'used_count', 'is_active')
    list_filter = ('discount_type', 'is_active')
    search_fields = ('code',)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user',)
    inlines = [CartItemInline]


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'created_at')

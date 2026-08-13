from django.contrib import admin

from apps.payments.models import Invoice, Order, OrderItem, Payment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'company', 'order_type', 'status', 'total_amount', 'currency', 'created_at')
    list_filter = ('status', 'order_type')
    search_fields = ('user__email',)
    inlines = [OrderItemInline, PaymentInline]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'order', 'issued_at')

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    icon = models.CharField(max_length=50, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Coupon(TimeStampedModel):
    PERCENTAGE = 'percentage'
    FIXED = 'fixed'
    DISCOUNT_TYPE_CHOICES = [(PERCENTAGE, 'Pourcentage'), (FIXED, 'Montant fixe')]

    company = models.ForeignKey(
        'tenants.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='coupons'
    )
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=12, choices=DISCOUNT_TYPE_CHOICES, default=PERCENTAGE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    applicable_courses = models.ManyToManyField('courses.Course', blank=True, related_name='coupons')
    applicable_categories = models.ManyToManyField(Category, blank=True, related_name='coupons')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

    def is_valid_now(self):
        from django.utils import timezone

        now = timezone.now()
        if not self.is_active or now < self.valid_from or now > self.valid_to:
            return False
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False
        return True

    def compute_discount(self, price):
        if self.discount_type == self.PERCENTAGE:
            return price * (self.amount / 100)
        return min(self.amount, price)


class Bundle(TimeStampedModel):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)
    courses = models.ManyToManyField('courses.Course', related_name='bundles', blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    company = models.ForeignKey(
        'tenants.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='bundles'
    )
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def list_price(self):
        return sum((c.price for c in self.courses.all()), start=0)


class Cart(TimeStampedModel):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='cart')

    def __str__(self):
        return f'Panier de {self.user}'

    @property
    def total(self):
        total = 0
        for item in self.items.select_related('course', 'bundle'):
            total += item.course.price if item.course else item.bundle.price
        return total


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    course = models.ForeignKey(
        'courses.Course', on_delete=models.CASCADE, related_name='cart_items', null=True, blank=True
    )
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE, related_name='cart_items', null=True, blank=True)

    class Meta:
        unique_together = ('cart', 'course', 'bundle')

    def __str__(self):
        return f'{self.course or self.bundle} in {self.cart}'


class Wishlist(TimeStampedModel):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='wishlist_items')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='wishlisted_by')

    class Meta:
        unique_together = ('user', 'course')

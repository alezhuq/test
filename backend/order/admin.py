from django.contrib import admin

from .models import Order, OrderItem, SubscriptionItem, Subscription


# Register your models here.

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Order)
class Order(admin.ModelAdmin):
    inlines = [
        OrderItemInline
    ]
    search_fields = ("user__email", "phonenum")


class SubscriptionItemInline(admin.TabularInline):
    model = SubscriptionItem
    extra = 1


@admin.register(Subscription)
class Subscription(admin.ModelAdmin):
    inlines = [
        SubscriptionItemInline
    ]
    search_fields = ("user__email", "phonenum")

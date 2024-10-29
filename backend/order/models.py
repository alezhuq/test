import datetime

from django.db import models
from django.utils.timezone import now
from shop.models import ProductFlavor
from django.contrib.auth import get_user_model

# Create your models here.


User = get_user_model()


class PaymentStatus(models.TextChoices):
    PD = "pd", "Paid"
    PG = "pg", "Pending"
    CN = "cn", "Canceled"


class ShipmentStatus(models.TextChoices):
    PR = "pr", "Processing"
    SH = "sh", "Shipping"
    AR = "ar", "Arrived"


"""-------------------------ORDERS-------------------------"""


class Subscription(models.Model):
    stripe_sub_id = models.CharField(max_length=60, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscription", null=True, blank=True)

    # Payment and subscription tracking
    is_paid = models.BooleanField(default=False)
    date_start = models.DateField()
    date_end = models.DateField(null=True, blank=True)
    last_paid = models.DateField(null=True, blank=True)  # Changed to DateField
    next_payment_due = models.DateField(null=True, blank=True)  # New field for upcoming payment

    # Status tracking
    STATUS_CHOICES = (
        ("active", "Active"),
        ("canceled", "Canceled"),
        ("past_due", "Past Due"),
        ("trialing", "Trialing"),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES,
                              default="active")  # New field for subscription status

    # Shipping and personal info
    region = models.CharField(max_length=3, default="UA", choices=(("UA", "ua",), ("EU", 'eu',)))
    city = models.CharField(max_length=20, default="default")
    shipment_address = models.CharField(max_length=20, default="default")
    name = models.CharField(max_length=20, default="default")
    surname = models.CharField(max_length=20, default="default")
    lastname = models.CharField(max_length=20, default="default", blank=True)
    phonenum = models.CharField(max_length=20, default="default")

    delivery_reference = models.CharField(max_length=100, null=True, blank=True)
    def __str__(self):
        return f"Subscription for {self.user} - {self.status}"


class SubscriptionItem(models.Model):
    product = models.ForeignKey(ProductFlavor, on_delete=models.SET_NULL, related_name="subscription_item", null=True)# FIX
    order = models.ForeignKey(Subscription, on_delete=models.SET_NULL, related_name="subscription_item", null=True)# FIX
    amount = models.IntegerField(default=0)
    pass


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="order", null=True, blank=True)
    shipment_status = models.CharField(max_length=20, choices=ShipmentStatus.choices)
    date = models.DateField()
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices)
    region = models.CharField(max_length=3, default="ua", choices=(("UA", "ua",), ("EU", 'eu',)))
    city = models.CharField(max_length=20, default="default")
    shipment_address = models.CharField(max_length=20, default="default")
    name = models.CharField(max_length=20, default="default")
    surname = models.CharField(max_length=20, default="default")
    lastname = models.CharField(max_length=20, default="default", blank=True)
    phonenum = models.CharField(max_length=20, default="default")
    stripe_id = models.CharField(max_length=255, null=True, blank=True)
    # delivery_reference = models.CharField(max_length=100, null=True, blank=True)  # To store the delivery reference


class OrderItem(models.Model):
    product = models.ForeignKey(ProductFlavor, on_delete=models.SET_NULL, related_name="order_item", null=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, related_name="order_item", null=True)
    amount = models.IntegerField()

    # id product
    # id flavor
    # amount

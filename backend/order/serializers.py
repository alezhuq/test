import datetime

from django.db import transaction, IntegrityError
from django.db.models import F
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import (
    Order,
    OrderItem, SubscriptionItem, Subscription,

)
from django.contrib.auth import get_user_model

from shop.models import ProductFlavor, Language
from dateutil.relativedelta import relativedelta
User = get_user_model()


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["product", "amount"]


class OrderSerializer(serializers.ModelSerializer):
    order_item = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        # fields = ["id", "shipment_status", "payment_status", "order_item"]
        fields = "__all__"

class UserOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id"]


class OrderCreateSerializer(serializers.ModelSerializer):
    order_item = OrderItemSerializer(many=True)
    region = serializers.CharField(write_only=True)

    ref_city = serializers.CharField(write_only=True)

    rec_warehouse = serializers.CharField(write_only=True)

    class Meta:
        model = Order
        fields = [
            "user",
            "order_item",
            "region",
            "phonenum",
            "rec_warehouse",
            "city",
            "ref_city",
            "name",
            "surname",
            "lastname",
        ]

    def create(self, validated_data):
        print(validated_data)
        if not validated_data['order_item']:
            raise serializers.ValidationError("order_item cannot be empty")

        order_items_data = validated_data.pop('order_item')
        region = validated_data.pop('region')
        validated_data.pop("ref_city")
        validated_data.pop("rec_warehouse")
        print(order_items_data)
        product_ids = {item['product'].id: item['amount'] for item in order_items_data}
        # # Create a new Order instance with the user_id

        with transaction.atomic():
            order = Order.objects.create(**validated_data, payment_status="Pending", date=datetime.datetime.now())

            if region == "ua":
                try:
                    for pr_id, amount in product_ids.items():
                        ProductFlavor.objects.filter(pk=pr_id).update(ua_quantity=F("ua_quantity") - amount)
                except IntegrityError as e:
                    raise ValidationError({"field": "ua_quantity", "msg": e})

            if region == "eu":
                try:
                    for pr_id, amount in product_ids.items():
                        ProductFlavor.objects.filter(pk=pr_id).update(eu_quantity=F("eu_quantity") - amount)
                except IntegrityError as e:
                    raise ValidationError({"field": "eu_quantity", "msg": e})

            # Loop through the order_item data and create OrderItem instances
            order_items = [OrderItem(order=order, **item_data) for item_data in order_items_data]

            # Use bulk_create to create OrderItem instances efficiently
            OrderItem.objects.bulk_create(order_items)

        return order


class SubscriptionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionItem
        fields = ["product", "amount"]


class SubscriptionSerializer(serializers.ModelSerializer):
    order_item = SubscriptionItemSerializer(many=True)

    class Meta:
        model = Subscription
        fields = ["order_item"]


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    order_item = SubscriptionItemSerializer(many=True)
    region = serializers.CharField(write_only=True)

    ref_city = serializers.CharField(write_only=True)
    rec_warehouse = serializers.CharField(write_only=True)
    country = serializers.CharField(write_only=True)
    shipment_address = serializers.CharField(write_only=True)

    class Meta:
        model = Subscription
        fields = [
            "user",
            "order_item",
            "region",
            "phonenum",
            "rec_warehouse",
            "city",
            "ref_city",
            "name",
            "surname",
            "lastname",
            "date_start",
            "date_end",
            "last_paid",
            "next_payment_due",
            "status",
            "shipment_address",
            "country"
        ]

    def create(self, validated_data):
        print(validated_data)
        if not validated_data['order_item']:
            raise serializers.ValidationError("order_item cannot be empty")

        order_items_data = validated_data.pop('order_item')
        region = validated_data.pop('region')
        validated_data.pop("ref_city")
        validated_data.pop("rec_warehouse")
        print(order_items_data)
        product_ids = {item['product'].id: item['amount'] for item in order_items_data}

        # Set initial values for new fields
        validated_data['status'] = 'active'  # Assuming a new subscription starts as 'active'
        validated_data['last_paid'] = None   # This can be updated after the first successful payment
        validated_data['next_payment_due'] = validated_data['date_start'] + relativedelta(months=1)  # Assuming the next payment is due on the start date

        with transaction.atomic():
            # Create a new Subscription instance
            subscription = Subscription.objects.create(**validated_data)

            if region == "ua":
                try:
                    for pr_id, amount in product_ids.items():
                        ProductFlavor.objects.filter(pk=pr_id).update(ua_quantity=F("ua_quantity") - amount)
                except IntegrityError as e:
                    raise ValidationError({"field": "ua_quantity", "msg": str(e)})

            elif region == "eu":
                try:
                    for pr_id, amount in product_ids.items():
                        ProductFlavor.objects.filter(pk=pr_id).update(eu_quantity=F("eu_quantity") - amount)
                except IntegrityError as e:
                    raise ValidationError({"field": "eu_quantity", "msg": str(e)})

            # Loop through the order_item data and create SubscriptionItem instances
            order_items = [SubscriptionItem(order=subscription, **item_data) for item_data in order_items_data]

            # Use bulk_create to create SubscriptionItem instances efficiently
            SubscriptionItem.objects.bulk_create(order_items)

        return subscription

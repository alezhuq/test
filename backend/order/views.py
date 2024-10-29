import datetime
import json
import time

import stripe
from celery.result import AsyncResult
from django.db import transaction, IntegrityError
from django.conf import settings
from django.db.models import Sum
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order, OrderItem, Subscription
from .serializers import OrderSerializer, OrderCreateSerializer, SubscriptionSerializer, SubscriptionCreateSerializer

from rest_framework.generics import (
    ListAPIView,
    CreateAPIView,
    RetrieveUpdateDestroyAPIView
)

from django.core.cache import cache
from shop.models import ProductFlavor, Product

# from .tasks import create_ttn, calculate_shipment
from .tasks import calculate_shipment, create_ttn, get_warehouse_by_string

stripe.api_key = settings.STRIPE_SECRET
stripe_webhook = settings.STRIPE_WEBHOOK_SECRET


def create_stripe_checkout(stripe_user_id, order, order_data):
    senderCity = cache.get("city_ref")
    rec_warehouse = order_data.get("rec_warehouse")

    currency = "price_eur" if order_data['region'] == 'eu' else "price_uah"
    rec_city = order_data.get("ref_city")
    flavors_ids = [pr_id.get("product").pk for pr_id in order_data['order_item']]
    amounts = {pr_id.get("product").pk: pr_id.get("amount") for pr_id in order_data['order_item']}
    # MAYBE different price for example if country == ua then .only() will be "name", "price_uah"
    price_name = ProductFlavor.objects.only("name", currency).filter(pk__in=flavors_ids).values()
    price = sum([elem[currency] * amounts.get(elem["id"]) for elem in price_name])
    weights = ProductFlavor.objects.filter(pk__in=flavors_ids).select_related("product").values("id", "product__weight")
    weight = sum([item["product__weight"] * amounts.get(item["id"], 0) for item in weights])
    # Extract data from the serializer

    if order_data["region"] == "ua":
        shipment_cost = calculate_shipment.delay(weight=weight, price=price, city=rec_city,
                                                 senderCity=senderCity)
    else:
        # temp, CHANGE LATER
        shipment_cost = 5

    try:
        line_items = []
        shipment_cost = shipment_cost.get()
        for elem in price_name:
            line_item = {
                "price": elem["stripe_price_ua_id"],
                "quantity": amounts.get(elem["id"])
            }
            line_items.append(line_item)
        shipping_options = [
            {
                "shipping_rate_data": {
                    "type": "fixed_amount",
                    "fixed_amount": {
                        "amount": int(shipment_cost * 100),
                        "currency": "eur" if order_data['region'] == 'eu' else 'uah'
                    },
                    "display_name": "Shipping price",
                    "delivery_estimate": {
                        "minimum": {"unit": "business_day", "value": 3},
                        "maximum": {"unit": "business_day", "value": 7},
                    },
                },
            },
        ]
        checkout_session = stripe.checkout.Session.create(
            customer=stripe_user_id,
            line_items=line_items,
            metadata={
                "region": order_data['region'],
                "recipient_warehouse_ref": rec_warehouse,  # order_data.get("recipient_city_ref"),
                "recipient_city_ref": rec_city,  # order_data.get("recipient_city_ref"),
                "sender_name": order_data.get("name"),
                "sender_surname": order_data.get("surname"),
                "sender_lastname": order_data.get("lastname"),
                "sender_phonenum": order_data.get("phonenum"),
                "price": price,
                "weight": weight,
                "order_id": order.id
            },
            mode='payment',
            success_url="http://127.0.0.1:8000/api/v1/order/payment/success/",
            cancel_url="http://localhost:8000/api/v1/order/payment/cancel/",
            shipping_options=shipping_options,
            payment_method_types=["card"],
        )

        return ({
                    'id': checkout_session.id,
                    "shipment_cost": shipment_cost,
                    "url": checkout_session.url,
                }, status.HTTP_201_CREATED,)

    except Exception as e:
        return (
            {'error 2': str(e)},
            status.HTTP_400_BAD_REQUEST,
        )


def temp(request):
    return JsonResponse({'status': 'working'})


class OrderListAPIView(ListAPIView):
    serializer_class = OrderSerializer

    # permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.select_related("user").filter(user_id=user.id)
        return queryset


class OrderAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = OrderSerializer

    # permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.select_related("user").filter(user_id=user.id)
        return queryset


class SubscriptionAPIView(ListAPIView):
    serializer_class = SubscriptionSerializer

    # permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        queryset = Subscription.objects.select_related("user").filter(user_id=user.id)
        return queryset


class OrderCreateView(CreateAPIView):
    serializer_class = OrderCreateSerializer

    def create(self, request, *args, **kwargs):

        if request.user.is_authenticated:
            stripe_user_id = request.user.stripe_customer_id

        serializer = OrderCreateSerializer(data=request.data)
        if serializer.is_valid():
            order_data = serializer.validated_data
            try:
                # Step 2: Create an Order Instance
                order = serializer.save(**order_data)
                res, status_code = create_stripe_checkout(stripe_user_id, order, order_data)
                return Response(res, status=status_code)
            except Exception as e:
                return Response(
                    str(e),
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubscriptionCreateView(CreateAPIView):
    serializer_class = SubscriptionCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = SubscriptionCreateSerializer(data=request.data)
        if serializer.is_valid():
            order_data = serializer.validated_data
            rec_warehouse = order_data.get("rec_warehouse")

            date_start = order_data.pop('date_start')
            date_end = order_data.pop('date_end', None)
            try:
                # Step 2: Create a Subscription instance
                with transaction.atomic():
                    print("Creating subscription...")

                    # Pop out fields that are not part of the Subscription model
                    order_data.pop("country")
                    senderCity = cache.get("city_ref")

                    # Create subscription and save additional fields
                    sub = serializer.save(**order_data, date_start=date_start, date_end=date_end)

                    # Currency based on region
                    currency = "price_eur" if order_data['region'] == 'eu' else "price_uah"
                    rec_city = order_data.get("ref_city")

                    # Handle Product and Pricing Logic
                    flavors_ids = [pr_id.get("product").pk for pr_id in order_data['order_item']]
                    amounts = {pr_id.get("product").pk: pr_id.get("amount") for pr_id in order_data['order_item']}
                    price_name = ProductFlavor.objects.only("name", currency).filter(pk__in=flavors_ids).values()

                    # Calculate total price and weight
                    price = sum([elem[currency] * amounts.get(elem["id"]) for elem in price_name])
                    weights = ProductFlavor.objects.filter(pk__in=flavors_ids).select_related("product").values("id",
                                                                                                                "product__weight")
                    weight = sum([item["product__weight"] * amounts.get(item["id"], 0) for item in weights])

                    # Shipment cost calculation
                    if order_data["region"] == "ua":
                        shipment_cost = calculate_shipment.delay(weight=weight, price=price, city=rec_city,
                                                                 senderCity=senderCity)
                    else:
                        shipment_cost = 10  # Set temporary EU shipment cost, change this later.

                    line_items = []
                    shipment_cost = shipment_cost.get()  # Assuming asynchronous task
                    for elem in price_name:
                        line_item = {
                            "price_data": {
                                "currency": "eur" if order_data['region'] == 'eu' else 'uah',
                                "unit_amount": int(elem[currency]) * 100,
                                "product_data": {"name": elem["name"]},
                                "recurring": {
                                    "interval": "month",
                                    "interval_count": 1,
                                },
                            },
                            "quantity": amounts.get(elem["id"])
                        }
                        line_items.append(line_item)

                    # Create Stripe Checkout Session
                    checkout_session = stripe.checkout.Session.create(
                        line_items=line_items,
                        metadata={
                            "region": order_data['region'],
                            "recipient_warehouse_ref": rec_warehouse,
                            "recipient_city_ref": rec_city,
                            "sender_name": order_data.get("name"),
                            "sender_surname": order_data.get("surname"),
                            "sender_lastname": order_data.get("lastname"),
                            "sender_phonenum": order_data.get("phonenum"),
                            "price": price,
                            "weight": weight,
                            "sub_id": sub.id
                        },
                        mode='subscription',
                        success_url="http://127.0.0.1:8000/api/v1/order/sub/success/",
                        cancel_url="http://localhost:8000/api/v1/order/sub/cancel/",
                        payment_method_types=["card"],
                    )

                    return Response(
                        {
                            'id': checkout_session.id,
                            "shipment_cost": shipment_cost,
                            "url": checkout_session.url,
                        },
                        status=status.HTTP_201_CREATED,
                    )

            except Exception as e:
                return Response(
                    {'error 2': str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
def my_webhook_view(request):
    payload = request.body
    event = None
    print("Webhook received")

    try:
        event = stripe.Event.construct_from(
            json.loads(payload), stripe_webhook
        )
    except ValueError as e:
        print("Invalid payload")
        return HttpResponse(status=400)

    # Handle the invoice.paid event (when a subscription payment is successful)
    if event.type == "invoice.paid":
        print("Handling invoice.paid")
        invoice = event.data.object
        if invoice.get("billing_reason") == "subscription_cycle":
            print("Subscription cycle payment")
            subscription_id = invoice.get("subscription")
            if not subscription_id:
                print("Missing subscription ID")
                return HttpResponse(status=400)

            try:
                single_sub = Subscription.objects.get(stripe_sub_id=subscription_id)
            except Subscription.DoesNotExist:
                print(f"Subscription {subscription_id} not found")
                return HttpResponse(status=404)

            # Fetch the required data for shipment
            res = get_warehouse_by_string.delay(
                city_name=single_sub.city,
                warehouse_str=single_sub.shipment_address
            )

            # Calculate the total weight of items in the subscription
            subscription = Subscription.objects.prefetch_related(
                "subscription_item", "subscription_item__product", "subscription_item__product__product"
            ).filter(stripe_sub_id=subscription_id)

            weight = subscription.aggregate(
                Sum("subscription_item__product__product__weight")
            ).get("subscription_item__product__product__weight__sum")

            if single_sub.region == "ua":
                address_ref, warehouse_index, city_ref = res.get()
                print("Creating shipment via NP")
                res = create_tnn_sub_np(
                    name=single_sub.name,
                    shipdate=(datetime.datetime.now() + datetime.timedelta(days=3)).strftime("%d.%m.%Y"),
                    surname=single_sub.surname,
                    lastname=single_sub.lastname,
                    phonenum=single_sub.phonenum,
                    orderid=single_sub.pk,
                    price=int(invoice.get("total")) / 100,
                    weight=weight,
                    recipient_warehouse_ref=address_ref,
                    recipient_city_ref=city_ref,
                )
                print(f"res is {res}")
            return HttpResponse(status=200)

        return HttpResponse(status=200)

    # Handle successful payment intents
    elif event.type == "payment_intent.succeeded":
        print("Handling payment_intent.succeeded")
        payment_intent = event.data.object
        payment_intent_id = payment_intent.id

        # Find the related order and update the status
        order = Order.objects.filter(stripe_id=payment_intent_id).first()
        if order:
            order.update(shipment_status="Paid")
            print(f"Order {order.id} marked as Paid.")
        else:
            print("Order not found for this Payment Intent")

        return HttpResponse(status=200)

    # Handle completed checkout sessions (especially for subscriptions)
    elif event.type == "checkout.session.completed":
        print("Handling checkout.session.completed")
        checkout = event.data.object
        order_id = checkout.metadata.get("order_id")
        sub_id = checkout.metadata.get("sub_id") or order_id
        region = checkout.metadata.get("region")

        try:
            subscription = Subscription.objects.get(pk=sub_id)
        except Subscription.DoesNotExist:
            print(f"Subscription {sub_id} not found")
            return HttpResponse(status=404)

        # If the session is for a subscription, update the subscription ID from Stripe
        if checkout.get("mode") == "subscription":
            stripe_sub_id = checkout.get("subscription")
            subscription.stripe_sub_id = stripe_sub_id
            subscription.save()

        # Handle regional-specific shipment creation
        if region == "ua":
            ref = create_tnn_np(
                name=checkout.metadata.get("sender_name"),
                shipdate=(datetime.datetime.now() + datetime.timedelta(3)).strftime("%d.%m.%Y"),
                surname=checkout.metadata.get("sender_surname"),
                lastname=checkout.metadata.get("sender_lastname"),
                phonenum=checkout.metadata.get("sender_phonenum"),
                orderid=sub_id,
                price=checkout.metadata.get("price"),
                weight=checkout.metadata.get("weight"),
                recipient_warehouse_ref=checkout.metadata.get("recipient_warehouse_ref"),
                recipient_city_ref=checkout.metadata.get("recipient_city_ref"),
            )
            subscription.delivery_reference = ref
            subscription.save()

        else:
            # Placeholder for other region shipping (DHL, etc.)
            print("Handling non-UA region shipment")

        return HttpResponse(status=200)

    # Handle expired checkout sessions
    elif event.type == "checkout.session.expired":
        checkout = event.data.object
        stripe_id = checkout.metadata.get("stripe_id")

        Order.objects.filter(stripe_id=stripe_id).update(shipment_status="Cancelled")
        print(f"Order {stripe_id} marked as Cancelled")

    else:
        print(f"Unhandled event type: {event.type}")

    return HttpResponse(status=200)


def create_tnn_np(name, surname, lastname, phonenum, shipdate, orderid, price, weight, recipient_warehouse_ref,
                  recipient_city_ref):
    order_items = Order.objects.prefetch_related(
        "order_item", "order_item__product", "order_item__product__product"
    ).filter(id=orderid).values(
        "order_item__product__product__length",
        "order_item__product__product__width",
        "order_item__product__product__height",
    )
    volume = 0
    print(order_items)
    for item in order_items:
        volume += item["order_item__product__product__length"] * item["order_item__product__product__width"] * item[
            "order_item__product__product__height"] / 1_000_000
    print(phonenum, "create_tnn_np")
    res = create_ttn(
        name=name,
        price=price,
        middlename=surname,
        payerType="Sender" if float(price) > 2000 else "Recipient",
        shipdate=shipdate,
        lastname=lastname,
        phonenum=phonenum,
        volume=volume,
        weight=int(weight) / 1000,
        description="Dietary supplements",
        recipient_warehouse_str=recipient_warehouse_ref,
        recipient_city_ref=recipient_city_ref,
    )
    return res


def create_tnn_sub_np(name, surname, lastname, phonenum, shipdate, orderid, price, weight, recipient_warehouse_ref,
                      recipient_city_ref):
    order_items = Subscription.objects.prefetch_related(
        "subscription_item", "subscription_item__product", "subscription_item__product__product"
    ).filter(id=orderid).values(
        "subscription_item__product__product__length",
        "subscription_item__product__product__width",
        "subscription_item__product__product__height",
    )
    volume = 0
    print(order_items)
    for item in order_items:
        volume += item["subscription_item__product__product__length"] * item[
            "subscription_item__product__product__width"] * item[
                      "subscription_item__product__product__height"] / 1_000_000
    print("CREATE_TNN_TASK")
    create_ttn.delay(
        name=name,
        price=price,
        middlename=surname,
        payerType="Sender" if float(price) > 2000 else "Recipient",
        shipdate=shipdate,
        lastname=lastname,
        phonenum=phonenum,
        volume=volume,
        weight=int(weight) / 1000,
        description="Dietary supplements",
        recipient_warehouse_str=recipient_warehouse_ref,
        recipient_city_ref=recipient_city_ref,
    )
    print("here!!!!!!!!!")
    return HttpResponse(status=200)

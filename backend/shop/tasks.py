# Celery tasks will be here
import os
from django.contrib.auth import get_user_model

from django.core.mail import EmailMessage
import stripe
from celery import shared_task
from django.template.loader import render_to_string
from django.conf import settings

from .models import PaymentMethod

User = get_user_model()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@shared_task
def task1(mail_subject, activation_link, user):
    message = render_to_string('activate_email.html', {
        'user': user,
        'activation_link': activation_link,

    })
    # make async task for email sending
    email = EmailMessage(
        mail_subject, message, to=[user.get("email")]
    )
    email.send()


@shared_task
def save_payment_method(user_id, payment_method_id):
    try:
        user = User.objects.get(pk=user_id)
        payment_method = stripe.PaymentMethod.attach(
            payment_method_id,
            customer=user.customer.stripe_customer_id,  # Replace with your user's Stripe customer ID
        )

        PaymentMethod.objects.create(
            user=user,
            payment_method_id=payment_method.id,
            card_brand=payment_method.card.brand,
            last4=payment_method.card.last4,
        )
    except Exception as e:
        # Handle exceptions or errors here
        pass


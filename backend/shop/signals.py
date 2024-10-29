from django.db.models.signals import post_save
from django.dispatch import receiver
import requests

from shop.models import Product


@receiver(post_save, sender=Product)  # Replace YourModel with the name of your Django model
def send_request_on_model_refresh(sender, instance, **kwargs):
    print(instance)
    print("Product changed")

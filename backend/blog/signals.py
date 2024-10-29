from django.db.models.signals import post_save
from django.dispatch import receiver
import requests

from blog.models import Blog, Tag


@receiver(post_save, sender=Blog)  # Replace YourModel with the name of your Django model
def send_request_on_model_refresh(sender, instance, **kwargs):
    # url = "http://example.com/your-endpoint"  # Replace with your endpoint
    # data = {"key": "value"}  # Replace with your data
    # response = requests.post(url, data=data)  # Send a POST request
    pass
    # make celery task


@receiver(post_save, sender=Tag)  # Replace YourModel with the name of your Django model
def send_request_on_model_refresh(sender, instance, **kwargs):
    pass

    # make celery task

import json
import time
import requests

from django.apps import AppConfig
from django.core.cache import cache

from .tasks import get_sender_address_ref_on_startup
from django.conf import settings


class OrderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'order'

    def ready(self):
        get_sender_address_ref_on_startup.delay()
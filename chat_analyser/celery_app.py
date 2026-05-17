# config/celery_app.py

from celery import Celery
from celery.signals import setup_logging
from logging.config import dictConfig

app = Celery("chat-analyser")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

@setup_logging.connect
def config_loggers(*args, **kwargs):
    from django.conf import settings as dj_settings
    dictConfig(dj_settings.LOGGING)
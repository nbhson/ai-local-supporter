import sys
import os
# Ensure the current project directory is in the python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from celery import Celery
import config

celery = Celery(
    "ai_local_support",
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

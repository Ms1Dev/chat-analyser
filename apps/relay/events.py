import json

import redis
from django.conf import settings

_redis = redis.from_url(settings.REDIS_URL)


def publish(user_id: int, event: dict) -> None:
    _redis.publish(f"relay:{user_id}", json.dumps(event))


def subscribe(user_id: int):
    pubsub = _redis.pubsub()
    pubsub.subscribe(f"relay:{user_id}")
    return pubsub

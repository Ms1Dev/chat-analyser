import json
from queue import Queue, Empty

from django.http import StreamingHttpResponse

from .events import register, unregister


def events(request):
    q = Queue()
    register(q)

    def stream():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    event = q.get(timeout=5)
                    event_type = event.get("type", "message")
                    yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"
                except Empty:
                    yield ": heartbeat\n\n"
        finally:
            unregister(q)

    resp = StreamingHttpResponse(stream(), content_type="text/event-stream")
    resp["X-Accel-Buffering"] = "no"
    resp["Cache-Control"] = "no-cache"
    return resp

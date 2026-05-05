import json
from queue import Queue, Empty

from django.http import HttpResponse, StreamingHttpResponse

from .events import register, unregister


def events(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=403)

    user_id = request.user.id
    q = Queue()
    register(user_id, q)

    def stream():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    event = q.get(timeout=5)
                    yield f"event: relay\ndata: {json.dumps(event)}\n\n"
                except Empty:
                    yield ": heartbeat\n\n"
        finally:
            unregister(user_id, q)

    resp = StreamingHttpResponse(stream(), content_type="text/event-stream")
    resp["X-Accel-Buffering"] = "no"
    resp["Cache-Control"] = "no-cache"
    return resp

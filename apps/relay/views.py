from django.http import HttpResponse, StreamingHttpResponse

from .events import subscribe


def events(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=403)

    pubsub = subscribe(request.user.id)

    def stream():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
                if msg is None:
                    yield ": heartbeat\n\n"
                elif msg["type"] == "message":
                    data = msg["data"]
                    if isinstance(data, bytes):
                        data = data.decode()
                    yield f"event: relay\ndata: {data}\n\n"
        finally:
            pubsub.unsubscribe()
            pubsub.close()

    resp = StreamingHttpResponse(stream(), content_type="text/event-stream")
    resp["X-Accel-Buffering"] = "no"
    resp["Cache-Control"] = "no-cache"
    return resp

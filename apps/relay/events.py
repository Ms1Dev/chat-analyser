import threading
from queue import Queue

_lock = threading.Lock()
_clients: list[Queue] = []


def register(q: Queue) -> None:
    with _lock:
        _clients.append(q)


def unregister(q: Queue) -> None:
    with _lock:
        if q in _clients:
            _clients.remove(q)


def publish(event: dict) -> None:
    with _lock:
        clients = list(_clients)
    for q in clients:
        q.put(event)

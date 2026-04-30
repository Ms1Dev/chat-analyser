import threading
from queue import Queue

_lock = threading.Lock()
_clients: dict[int, list[Queue]] = {}


def register(user_id: int, q: Queue) -> None:
    with _lock:
        _clients.setdefault(user_id, []).append(q)


def unregister(user_id: int, q: Queue) -> None:
    with _lock:
        if user_id in _clients:
            try:
                _clients[user_id].remove(q)
            except ValueError:
                pass
            if not _clients[user_id]:
                del _clients[user_id]


def publish(user_id: int, event: dict) -> None:
    with _lock:
        clients = list(_clients.get(user_id, []))
    for q in clients:
        q.put(event)

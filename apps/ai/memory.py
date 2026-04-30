# chat_analyser/ai/memory.py
from mem0 import Memory
from django.conf import settings

db = settings.DATABASES["default"]

memory = Memory.from_config({
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "host": db["HOST"],
            "port": int(db.get("PORT") or 5432),
            "dbname": db["NAME"],
            "user": db["USER"],
            "password": db["PASSWORD"],
            "collection_name": "mem0_memories",
        },
    },
    "llm": {
        "provider": "openai",
        "config": {"model": "gpt-4o-mini", "temperature": 0.1},
    },
    "embedder": {
        "provider": "openai",
        "config": {"model": "text-embedding-3-small"},
    },
})
# chat_analyser/ai/memory.py
from mem0 import Memory
from mem0.vector_stores.pgvector import PGVector
from django.conf import settings

# mem0's pgvector search returns cosine DISTANCE (lower = more similar) via the <=>
# operator, but score_and_rank() treats the value as cosine SIMILARITY (higher = more
# similar). This inverts both threshold filtering and result ordering. Patch the search
# method to convert distance → similarity before the scores reach the ranking logic.
_orig_pgvector_search = PGVector.search

def _pgvector_search_as_similarity(self, query, vectors, top_k, filters=None):
    results = _orig_pgvector_search(self, query=query, vectors=vectors, top_k=top_k, filters=filters)
    for r in results:
        r.score = 1.0 - r.score
    return results

PGVector.search = _pgvector_search_as_similarity

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
    "custom_instructions": """
    NEVER STORE:
    - Social Security Numbers
    - Insurance policy numbers
    - Credit card information
    - Full addresses
    - Phone numbers

    Exclude:
    - Greetings and filler
    - Casual chatter
    - Hypotheticals unless planning related
    """

})
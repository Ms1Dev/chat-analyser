import os

from mem0 import Memory

memory = Memory.from_config({
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "url": "http://{}:{}".format(
                os.environ.get("QDRANT_HOST", "localhost"),
                os.environ.get("QDRANT_PORT", "6333"),
            ),
            "api_key": os.environ.get("QDRANT_API_KEY"),
            "collection_name": "mem0_memories",
            "embedding_model_dims": 1536,
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


import sys
import os

from qdrant_client import QdrantClient
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_analyser.settings')

import django
django.setup()

import hashlib
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings

from apps.ai.models import RagDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    CSVLoader,
    UnstructuredMarkdownLoader,
)


def chunk_text(documents, chunk_size=512, chunk_overlap=64):
    """Splits text into chunks of specified size with overlap."""
        # Initialize Text Splitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return splitter.split_documents(documents)


def hash_file(file_path):
    """Generates a hash for the given file."""
    with open(file_path, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()
    return file_hash


def file_exists(hash_value):
    """Checks if a file with the given hash already exists in the database."""
    return RagDocument.objects.filter(hash=hash_value).exists()


def store_chunks(chunks):
    from qdrant_client.models import Distance, VectorParams

    client = QdrantClient(url="http://qdrant:6333")

    if not client.collection_exists("docs"):
        client.create_collection(
            collection_name="docs",
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )

    vector_store = QdrantVectorStore(
        client=client,
        collection_name="docs",
        embedding=OpenAIEmbeddings()
    )

    return vector_store.add_documents(chunks)



def chunk_file(file_path):
    file_hash = hash_file(file_path)
    if file_exists(file_hash):
        print("File already exists in the database.")
    else:
        text_loader = TextLoader(file_path)
        documents = text_loader.load()

        chunks = chunk_text(documents)

        ids = store_chunks(chunks)

        RagDocument.objects.create(
            hash=file_hash,
            chunk_ids=ids
        )

        print("File processed and chunks stored in the vector database.")



    
if __name__ == "__main__":
    chunk_file("/app/apps/ai/services/test_file.txt")


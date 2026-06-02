
import sys
import os
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_analyser.settings')

import django
django.setup()

import hashlib

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
    
    
if __name__ == "__main__":
    file_hash = hash_file("/app/apps/ai/services/test_file.txt")
    if file_exists(file_hash):
        print("File already exists in the database.")
    else:
        RagDocument.objects.create(hash=file_hash)
        
        text_loader = TextLoader("/app/apps/ai/services/test_file.txt")
        documents = text_loader.load()

        chunks = chunk_text(documents)

        print(f"Total chunks: {len(chunks)}")

        for i, chunk in enumerate(chunks):
            print(f"\n--- Chunk {i+1} ---")
            print(f"Length: {len(chunk.page_content)} chars")
            print(chunk.page_content)



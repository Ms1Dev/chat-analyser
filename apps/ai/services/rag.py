
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


if __name__ == "__main__":

    text_loader = TextLoader("/app/apps/ai/services/test_file.txt")
    documents = text_loader.load()

    chunks = chunk_text(documents)

    print(f"Total chunks: {len(chunks)}")

    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i+1} ---")
        print(f"Length: {len(chunk.page_content)} chars")
        print(chunk.page_content)



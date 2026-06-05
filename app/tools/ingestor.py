import os
from typing import List
from langchain_core.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.db import get_vector_store

@tool
def ingest_pdf(file_path: str) -> str:
    """
    Parses a local PDF file, chunks the text, and stores it in the vector database.
    
    Args:
        file_path: The absolute path to the PDF file.
    """
    if not os.path.exists(file_path):
        return f"Error: File {file_path} not found."
    
    try:
        # Load PDF
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        
        # Chunk text
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            add_start_index=True
        )
        chunks = text_splitter.split_documents(documents)
        
        # Store in vector store
        vector_store = get_vector_store()
        vector_store.add_documents(chunks)
        
        return f"Successfully ingested {len(chunks)} chunks from {file_path}."
    except Exception as e:
        return f"Error during ingestion: {str(e)}"

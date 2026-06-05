from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores.pgvector import PGVector
from app.core.config import settings

def get_vector_store(collection_name: str = "academic_papers"):
    """
    Returns a PGVector instance configured with OpenAI embeddings.
    """
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.OPENAI_API_KEY
    )
    
    return PGVector(
        connection_string=settings.DATABASE_URL,
        embedding_function=embeddings,
        collection_name=collection_name,
        use_jsonb=True # Better for metadata filtering
    )

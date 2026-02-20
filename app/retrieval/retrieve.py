import logging

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import GEMINI_API_KEY, GEMINI_EMBED_MODEL, EMBEDDING_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

query_embeddings = GoogleGenerativeAIEmbeddings(
    model=GEMINI_EMBED_MODEL,
    google_api_key=GEMINI_API_KEY,
    task_type="retrieval_query"
)

def get_vectorstore(collection_name: str) -> Chroma:
    return Chroma(
        collection_name=collection_name,
        embedding_function=query_embeddings,
        persist_directory=str(EMBEDDING_PATH),
        collection_metadata={"hnsw:space": "cosine"},
    )

def retrieve_collection(query: str, collection_name: str, top_k: int = 5) -> list[dict]:
    logger.info(f"[RETRIEVE] Collection={collection_name} | top_k={top_k}")

    query_vector = query_embeddings.embed_query(query)

    vectorstore = get_vectorstore(collection_name)
    results = vectorstore._collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
from dotenv import load_dotenv
load_dotenv()
import os
import cohere
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Clients
qdrant = QdrantClient(url=os.getenv("QDRANT_URL"))
co = cohere.Client(os.getenv("COHERE_API_KEY"))
embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY")
)

COLLECTION_NAME = "pr_reviews"
VECTOR_SIZE = 3072

def init_qdrant():
    """Create collection if not exists"""
    if not qdrant.collection_exists(COLLECTION_NAME):
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )
        print(f"Collection '{COLLECTION_NAME}' created")

def store_review(state) -> str:
    """Store PR review in Qdrant for semantic search"""
    init_qdrant()
    
    # Embed - summary + diff analysis combined
    text_to_embed = f"""
    PR: {state.repo_name} #{state.pr_number}
    Analysis: {state.diff_analysis}
    Summary: {state.review_summary}
    """
    
    vector = embedding_model.embed_query(text_to_embed)
    point_id = str(uuid.uuid4())
    
    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "pr_url": state.pr_url,
                    "pr_number": state.pr_number,
                    "repo_name": state.repo_name,
                    "review_summary": state.review_summary,
                    "final_review": state.final_review,
                    "comments_posted": state.comments_posted
                }
            )
        ]
    )
    return point_id

def search_similar_reviews(query: str, k: int = 10) -> list:
    """Search similar past reviews using hybrid search"""
    init_qdrant()
    
    # Dense search
    query_vector = embedding_model.embed_query(query)
    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=k
    ).points
    
    if not results:
        return []
    
    # Rerank with Cohere
    docs = [r.payload["review_summary"] for r in results]
    reranked = co.rerank(
        query=query,
        documents=docs,
        model="rerank-english-v3.0",
        top_n=3
    )
    
    return [results[r.index].payload for r in reranked.results]
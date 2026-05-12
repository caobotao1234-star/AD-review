"""RAG 法条检索工具：从 ChromaDB 检索相关法律条款"""

from openai import OpenAI
import chromadb

from src.config import ARK_API_KEY, ARK_BASE_URL, ARK_EMBEDDING_MODEL, CHROMA_DB_DIR
from src.models import LawArticle


def _get_embedding(text: str) -> list[float]:
    """获取文本 embedding"""
    client = OpenAI(api_key=ARK_API_KEY, base_url=ARK_BASE_URL)
    response = client.embeddings.create(
        model=ARK_EMBEDDING_MODEL,
        input=[text],
    )
    return response.data[0].embedding


def rag_search(query: str, top_k: int = 3) -> list[LawArticle]:
    """
    从 ChromaDB 检索相关法条。

    Args:
        query: 查询文本（如违规描述）
        top_k: 返回最相关的条数

    Returns:
        相关法条列表，包含法规名、条款号、原文、相关度分数
    """
    # 连接 ChromaDB
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

    try:
        collection = chroma_client.get_collection("law_articles")
    except Exception:
        return []  # 数据库未构建

    # 向量化查询
    query_embedding = _get_embedding(query)

    # 检索
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    if not results or not results["documents"]:
        return []

    articles = []
    for i, (doc, meta, distance) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )):
        # ChromaDB 返回的 distance 越小越相关，转换为 0-1 的相关度分数
        relevance = max(0.0, 1.0 - distance)
        articles.append(LawArticle(
            law_name=meta.get("law_name", ""),
            chapter=meta.get("chapter", ""),
            article_number=meta.get("article_number", ""),
            content=doc,
            relevance_score=round(relevance, 4),
        ))

    return articles

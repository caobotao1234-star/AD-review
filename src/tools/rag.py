"""RAG 法条检索工具：从 ChromaDB 检索相关法律条款"""

import chromadb

from src.config import CHROMA_DB_DIR
from src.models import LawArticle


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

    # 使用 ChromaDB 内置 embedding 检索
    results = collection.query(
        query_texts=[query],
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

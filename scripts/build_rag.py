"""
RAG 法条构建脚本

用法：
    python scripts/build_rag.py

功能：
    1. 读取 ref/ 目录下的法条 docx 文件
    2. 按"第X条"正则切分为独立条款
    3. 使用火山方舟 Doubao-embedding 模型向量化
    4. 存入 ChromaDB 本地持久化数据库

前置条件：
    - 安装依赖：pip install python-docx chromadb openai python-dotenv
    - 配置 .env 文件（参考 .env.example）
    - 将法条 docx 文件放入 ref/ 目录
"""

import os
import re
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from docx import Document
from dotenv import load_dotenv
import chromadb

load_dotenv()


def extract_text_from_docx(docx_path: str) -> str:
    """从 docx 文件提取全部文本"""
    doc = Document(docx_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def split_by_articles(full_text: str, law_name: str) -> list[dict]:
    """
    按"第X条"切分法条文本。

    Returns:
        list of dict: [{law_name, chapter, article_number, content}, ...]
    """
    # 先识别章节标题
    chapter_pattern = re.compile(r"^第[一二三四五六七八九十]+章\s*(.+)$", re.MULTILINE)
    # 按"第X条"切分
    article_pattern = re.compile(r"(第[一二三四五六七八九十百零\d]+条)")

    # 找出所有章节及其位置
    chapters = []
    for m in chapter_pattern.finditer(full_text):
        chapters.append((m.start(), m.group(0)))

    def get_chapter_at_pos(pos: int) -> str:
        """根据文本位置确定所属章节"""
        current_chapter = "总则"
        for ch_pos, ch_name in chapters:
            if ch_pos <= pos:
                current_chapter = ch_name
            else:
                break
        return current_chapter

    # 切分条款
    parts = article_pattern.split(full_text)
    articles = []

    i = 1  # parts[0] 是第一条之前的内容（标题等），跳过
    while i < len(parts) - 1:
        article_marker = parts[i].strip()  # "第X条"
        article_content = parts[i + 1].strip() if i + 1 < len(parts) else ""

        # 找到该条在原文中的位置以确定章节
        marker_pos = full_text.find(article_marker)
        chapter = get_chapter_at_pos(marker_pos)

        articles.append({
            "law_name": law_name,
            "chapter": chapter,
            "article_number": article_marker,
            "content": f"{article_marker} {article_content}",
        })
        i += 2

    return articles


def build_chroma_db(articles: list[dict], db_path: str):
    """将法条存入 ChromaDB（使用 ChromaDB 内置 embedding）"""
    chroma_client = chromadb.PersistentClient(path=db_path)

    # 创建或获取 collection（使用默认的 all-MiniLM-L6-v2 embedding）
    collection = chroma_client.get_or_create_collection(
        name="law_articles",
        metadata={"description": "广告法及相关法规条款"}
    )

    # 批量处理
    batch_size = 20
    total = len(articles)

    for start in range(0, total, batch_size):
        batch = articles[start:start + batch_size]
        texts = [a["content"] for a in batch]
        ids = [f"{a['law_name']}_{a['article_number']}" for a in batch]
        metadatas = [
            {
                "law_name": a["law_name"],
                "chapter": a["chapter"],
                "article_number": a["article_number"],
            }
            for a in batch
        ]

        # ChromaDB 自动使用内置 embedding 模型
        collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
        )

        print(f"  已处理 {min(start + batch_size, total)}/{total} 条")

    return collection


def main():
    """主流程"""
    print("=" * 60)
    print("RAG 法条构建工具")
    print("=" * 60)

    # 扫描 ref/ 目录
    ref_dir = Path(project_root) / "ref"
    docx_files = list(ref_dir.glob("*.docx"))

    if not docx_files:
        print("❌ 错误: ref/ 目录下没有找到 .docx 文件")
        sys.exit(1)

    print(f"\n📂 找到 {len(docx_files)} 个法条文件:")
    for f in docx_files:
        print(f"   - {f.name}")

    # 初始化（不再需要 API 客户端，使用 ChromaDB 内置 embedding）
    print("\n💡 使用 ChromaDB 内置 embedding 模型（无需外部 API）")

    # 处理每个文件
    all_articles = []
    for docx_file in docx_files:
        print(f"\n📖 正在处理: {docx_file.name}")

        # 从文件名推断法规名
        law_name = docx_file.stem.split("_")[0]
        print(f"   法规名称: {law_name}")

        # 提取文本
        full_text = extract_text_from_docx(str(docx_file))
        print(f"   文本长度: {len(full_text)} 字符")

        # 切分条款
        articles = split_by_articles(full_text, law_name)
        print(f"   切分条款: {len(articles)} 条")

        # 打印前 3 条作为示例
        print(f"\n   📋 示例条款（前3条）:")
        for a in articles[:3]:
            preview = a["content"][:80] + "..." if len(a["content"]) > 80 else a["content"]
            print(f"      [{a['chapter']}] {a['article_number']}: {preview}")

        all_articles.extend(articles)

    # 存入 ChromaDB
    db_path = str(Path(project_root) / "data" / "chroma_db")
    print(f"\n🔄 正在向量化并存入 ChromaDB ({db_path})...")

    collection = build_chroma_db(all_articles, db_path)

    print(f"\n✅ 构建完成!")
    print(f"   总条款数: {len(all_articles)}")
    print(f"   数据库路径: {db_path}")
    print(f"   Collection: {collection.name} (count={collection.count()})")

    # 测试检索
    print(f"\n🔍 测试检索: '虚假广告'")
    results = collection.query(query_texts=["虚假广告"], n_results=3)
    if results and results["documents"]:
        for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
            preview = doc[:60] + "..." if len(doc) > 60 else doc
            print(f"   [{i+1}] {meta['law_name']} {meta['article_number']}: {preview}")

    print("\n" + "=" * 60)
    print("RAG 构建完成，可以开始使用了！")
    print("=" * 60)


if __name__ == "__main__":
    main()

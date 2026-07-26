"""知识库构建脚本

运行一次即可将 knowledge_items.json 导入 ChromaDB 向量数据库。
首次运行时会下载 sentence-transformers 模型 (~80MB)。

Usage:
    cd agent && uv run python -m src.knowledge.build_kb
"""

from .vector_store import kb


def main():
    print("[build_kb] Building spatial knowledge base...")
    kb.build()
    collections = kb.list_collections()
    print(f"[build_kb] Done. Collections: {collections}")

    # 测试检索
    results = kb.search("咖啡店选址标准")
    print(f"[build_kb] Test query '咖啡店选址标准' → {len(results)} results:")
    for r in results:
        print(f"  [{r['metadata'].get('category','')}] {r['metadata'].get('title','')}")


if __name__ == "__main__":
    main()

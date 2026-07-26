"""ChromaDB 向量知识库

存储和检索城市规划规范、行业标准、分析方法论等空间知识。
使用 ChromaDB 嵌入式向量数据库 + 轻量 ONNX 本地 embedding。
"""

import json
import os
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

KB_DIR = Path(__file__).resolve().parent / "chroma_data"
DATA_FILE = Path(__file__).resolve().parent / "data" / "knowledge_items.json"


class SpatialKnowledgeBase:
    """空间知识库管理器"""

    def __init__(self):
        os.makedirs(KB_DIR, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(KB_DIR))
        # 使用 ChromaDB 内置 ONNX 轻量 embedding (无需 torch/sentence-transformers)
        self.ef = embedding_functions.DefaultEmbeddingFunction()

    def list_collections(self) -> list[str]:
        return [c.name for c in self.client.list_collections()]

    def build(self, items: list[dict] | None = None):
        """构建/重建知识库"""
        if items is None:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                items = json.load(f)

        # 删除旧集合
        try:
            self.client.delete_collection("spatial_knowledge")
        except Exception:
            pass

        col = self.client.create_collection(
            name="spatial_knowledge",
            embedding_function=self.ef,
            metadata={"description": "GeoAI 空间规划知识库"},
        )

        docs = [f"[{it['category']}] {it['title']}\n{it['content']}" for it in items]
        ids = [it["id"] for it in items]
        metadatas = [
            {"category": it["category"], "title": it["title"]} for it in items
        ]

        col.add(documents=docs, ids=ids, metadatas=metadatas)
        print(f"[knowledge] Built knowledge base with {len(items)} items")

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """检索相关知识条目"""
        try:
            col = self.client.get_collection(
                name="spatial_knowledge",
                embedding_function=self.ef,
            )
            results = col.query(query_texts=[query], n_results=top_k)
            items = []
            if results.get("documents") and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    items.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                        "score": results.get("distances", [[0]])[0][i] if results.get("distances") else 0,
                    })
            return items
        except Exception as e:
            print(f"[knowledge] Search error: {e}")
            return []


# 全局单例
kb = SpatialKnowledgeBase()

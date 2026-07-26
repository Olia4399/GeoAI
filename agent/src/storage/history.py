"""分析历史存储

SQLite 存储每次空间分析的完整结果，支持列表、查看、删除、对比。
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "analysis_history.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            query TEXT NOT NULL,
            intent_json TEXT,
            steps_json TEXT,
            results_json TEXT,
            report TEXT,
            tags TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_analysis(query: str, intent: dict, steps: list[dict], results: list[dict], report: str) -> str:
    """保存分析结果，返回 ID"""
    analysis_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()

    conn = _get_conn()
    conn.execute(
        "INSERT INTO analysis_history (id, created_at, query, intent_json, steps_json, results_json, report) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            analysis_id,
            now,
            query,
            json.dumps(intent, ensure_ascii=False),
            json.dumps(steps, ensure_ascii=False),
            json.dumps(results, ensure_ascii=False),
            report,
        ),
    )
    conn.commit()
    conn.close()
    return analysis_id


def list_analyses(limit: int = 20, offset: int = 0) -> list[dict]:
    """列出历史分析"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, created_at, query, intent_json FROM analysis_history ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "created_at": r["created_at"],
            "query": r["query"],
            "intent": json.loads(r["intent_json"]) if r["intent_json"] else None,
        }
        for r in rows
    ]


def get_analysis(analysis_id: str) -> dict | None:
    """获取单次分析详情"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM analysis_history WHERE id = ?", (analysis_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "query": row["query"],
        "intent": json.loads(row["intent_json"]) if row["intent_json"] else None,
        "steps": json.loads(row["steps_json"]) if row["steps_json"] else [],
        "results": json.loads(row["results_json"]) if row["results_json"] else [],
        "report": row["report"],
    }


def delete_analysis(analysis_id: str) -> bool:
    """删除分析"""
    conn = _get_conn()
    cur = conn.execute("DELETE FROM analysis_history WHERE id = ?", (analysis_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# 启动时初始化
init_db()

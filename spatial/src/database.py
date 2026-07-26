"""数据库连接模块 — 避免循环引用"""

import os


def get_db_url() -> str:
    """获取数据库连接 URL，优先从环境变量读取"""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://geoai:geoai123@localhost:5432/geoai",
    )


# 全局数据库连接 (开发阶段简单连接池)
db_conn = None

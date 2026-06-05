"""SQL ETL 引擎 — 核心：用纯 SQL 完成数据提取、清洗、转换"""

import pandas as pd
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from typing import Optional
import json

# 同步引擎缓存（用于 pandas to_sql）
_sync_engine_cache = {}


def _get_sync_engine(async_session: AsyncSession):
    """获取同步 SQLAlchemy 引擎（用于 pandas to_sql）"""
    url = str(async_session.bind.url)
    # 将 async driver 替换为 sync
    sync_url = url.replace("+aiosqlite", "")
    if sync_url not in _sync_engine_cache:
        _sync_engine_cache[sync_url] = create_engine(sync_url)
    return _sync_engine_cache[sync_url]


class SqlEtlEngine:
    """
    基于关系型数据库的 SQL ETL 引擎。
    所有数据操作通过 SQL 完成，不做 Spark。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _load_dataframe(self, file_path: str) -> pd.DataFrame:
        """加载文件到 DataFrame"""
        ext = Path(file_path).suffix.lower()
        if ext == ".csv":
            df = pd.read_csv(file_path)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path)
        elif ext == ".json":
            df = pd.read_json(file_path)
        elif ext == ".html":
            tables = pd.read_html(file_path)
            df = tables[0] if tables else pd.DataFrame()
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

        # 标准化列名
        df.columns = [
            c.strip().lower().replace(" ", "_").replace("-", "_").replace(".", "_")
            for c in df.columns
        ]
        return df

    def _df_to_sql(self, df: pd.DataFrame, table_name: str):
        """将 DataFrame 写入数据库"""
        sync_engine = _get_sync_engine(self.db)
        df.to_sql(table_name, sync_engine, if_exists="replace", index=False)

    async def load_csv_to_table(self, file_path: str, table_name: str) -> dict:
        """CSV/Excel → 数据库表"""
        df = self._load_dataframe(file_path)
        self._df_to_sql(df, table_name)

        return {
            "table_name": table_name,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        }

    async def load_file_to_table(self, file_path: str, table_name: str) -> dict:
        """自动识别文件格式并加载"""
        df = self._load_dataframe(file_path)
        self._df_to_sql(df, table_name)

        return {
            "table_name": table_name,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        }

    async def execute_sql(self, sql: str) -> dict:
        """执行任意 SQL 并返回结果"""
        result = await self.db.execute(text(sql))
        if result.returns_rows:
            rows = result.fetchall()
            columns = list(result.keys())
            data = [dict(zip(columns, row)) for row in rows]
            return {"columns": columns, "data": data, "row_count": len(data)}
        else:
            return {"message": "SQL executed successfully", "rows_affected": result.rowcount}

    async def generate_etl_sql(self, config: dict) -> str:
        """根据 ETL 配置生成 SQL"""
        parts = []

        # SELECT
        fields = []
        for f in config.get("target_fields", []):
            table_alias = f.get("table", "")
            field = f.get("field", "*")
            alias = f.get("alias", "")
            col = f"{table_alias}.{field}" if table_alias else field
            if alias:
                col = f"{col} AS {alias}"
            fields.append(col)
        parts.append(f"SELECT {', '.join(fields) if fields else '*'}")

        # FROM
        tables = config.get("source_tables", [])
        parts.append(f"FROM {tables[0]}" if tables else "FROM dual")

        # JOIN
        for j in config.get("joins", []):
            join_type = j.get("type", "LEFT JOIN")
            # 从 right 字段推导表名（如 "raw_529335fc.subjectid" → "raw_529335fc"）
            right_table = j.get("right_table", "")
            if not right_table and "." in j.get("right", ""):
                right_table = j["right"].split(".")[0]
            parts.append(f"{join_type} {right_table} ON {j['left']} = {j['right']}")

        # WHERE
        filters = config.get("filters", [])
        if filters:
            parts.append(f"WHERE {' AND '.join(filters)}")

        # GROUP BY
        group_by = config.get("group_by", [])
        if group_by:
            parts.append(f"GROUP BY {', '.join(group_by)}")

        # HAVING
        having = config.get("having", [])
        if having:
            parts.append(f"HAVING {' AND '.join(having)}")

        # ORDER BY
        order_by = config.get("order_by", [])
        if order_by:
            parts.append(f"ORDER BY {', '.join(order_by)}")

        return "\n".join(parts)

    async def run_etl(self, etl_config: dict) -> dict:
        """执行完整的 ETL 流程"""
        sql = await self.generate_etl_sql(etl_config)
        result = await self.execute_sql(sql)
        result["generated_sql"] = sql
        return result

    async def list_tables(self) -> list:
        """列出数据库中所有表"""
        result = await self.db.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        )
        return [row[0] for row in result.fetchall()]

    async def describe_table(self, table_name: str) -> dict:
        """获取表结构"""
        result = await self.db.execute(text(f"PRAGMA table_info({table_name})"))
        columns = []
        for row in result.fetchall():
            columns.append({
                "cid": row[0],
                "name": row[1],
                "type": row[2],
                "notnull": bool(row[3]),
                "default": row[5],
                "pk": bool(row[6]),
            })
        return {"table_name": table_name, "columns": columns}

    async def preview_table(self, table_name: str, limit: int = 10) -> dict:
        """预览表数据"""
        result = await self.db.execute(text(f"SELECT * FROM {table_name} LIMIT {limit}"))
        rows = result.fetchall()
        columns = list(result.keys())
        data = [dict(zip(columns, row)) for row in rows]
        return {"columns": columns, "data": data, "row_count": len(data)}

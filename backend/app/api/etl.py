"""ETL API — SQL ETL 生成与执行"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.etl.engine import SqlEtlEngine

router = APIRouter(prefix="/api/etl", tags=["etl"])


class EtlRequest(BaseModel):
    source_tables: list[str]
    target_fields: list[dict]  # [{table, field, alias}]
    joins: list[dict] = []     # [{left, right, type}]
    filters: list[str] = []
    group_by: list[str] = []
    having: list[str] = []
    order_by: list[str] = []


class SqlRequest(BaseModel):
    sql: str


@router.post("/generate")
async def generate_etl_sql(request: EtlRequest, db: AsyncSession = Depends(get_db)):
    """根据配置生成 ETL SQL"""
    engine = SqlEtlEngine(db)
    config = request.model_dump()
    sql = await engine.generate_etl_sql(config)
    return {"sql": sql, "config": config}


@router.post("/execute")
async def execute_etl(request: EtlRequest, db: AsyncSession = Depends(get_db)):
    """执行 ETL（生成 SQL 并运行）"""
    engine = SqlEtlEngine(db)
    config = request.model_dump()
    result = await engine.run_etl(config)
    return result


@router.post("/sql")
async def execute_raw_sql(request: SqlRequest, db: AsyncSession = Depends(get_db)):
    """直接执行 SQL 查询"""
    engine = SqlEtlEngine(db)
    # 安全校验：只允许 SELECT
    sql_upper = request.sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        raise HTTPException(400, "仅支持 SELECT 查询（安全限制）")
    try:
        result = await engine.execute_sql(request.sql)
        return result
    except Exception as e:
        raise HTTPException(400, f"SQL 执行错误: {str(e)}")


@router.get("/tables")
async def list_tables(db: AsyncSession = Depends(get_db)):
    """列出数据库中的所有表"""
    engine = SqlEtlEngine(db)
    tables = await engine.list_tables()
    return {"tables": tables}


@router.get("/tables/{table_name}/schema")
async def get_table_schema(table_name: str, db: AsyncSession = Depends(get_db)):
    """获取表结构"""
    engine = SqlEtlEngine(db)
    try:
        schema = await engine.describe_table(table_name)
        return schema
    except Exception as e:
        raise HTTPException(400, f"获取表结构失败: {str(e)}")


@router.get("/tables/{table_name}/preview")
async def preview_table(table_name: str, limit: int = 10, db: AsyncSession = Depends(get_db)):
    """预览表数据"""
    engine = SqlEtlEngine(db)
    try:
        result = await engine.preview_table(table_name, limit)
        return result
    except Exception as e:
        raise HTTPException(400, f"预览失败: {str(e)}")

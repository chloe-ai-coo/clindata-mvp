"""数据集 API — 上传、解析、管理"""

import os
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import DATA_DIR, ALLOWED_EXTENSIONS
from app.models.models import Dataset, FieldMeta
from app.etl.engine import SqlEtlEngine

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.post("/upload")
async def upload_dataset(
    project_id: int,
    file: UploadFile = File(...),
    name: str = "",
    source_type: str = "unknown",
    db: AsyncSession = Depends(get_db),
):
    """上传数据文件并自动入库"""
    # 检查文件格式
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件格式: {ext}")

    # 保存文件
    file_id = str(uuid.uuid4())[:8]
    save_path = DATA_DIR / f"{file_id}_{file.filename}"
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # 自动识别 source_type
    if source_type == "unknown":
        fname = file.filename.lower()
        if "ae" in fname or "adverse" in fname:
            source_type = "ae"
        elif "lb" in fname or "lab" in fname:
            source_type = "lab"
        elif "vs" in fname or "vital" in fname:
            source_type = "vs"
        elif "cm" in fname or "medic" in fname:
            source_type = "cm"
        elif "dm" in fname:
            source_type = "dm"
        elif "edc" in fname or "rave" in fname:
            source_type = "edc"
        elif "epro" in fname or "eCOA" in fname:
            source_type = "epro"

    # 生成表名
    table_name = f"raw_{file_id}"

    # 用 ETL 引擎加载数据
    engine = SqlEtlEngine(db)
    try:
        load_result = await engine.load_file_to_table(str(save_path), table_name)
    except Exception as e:
        raise HTTPException(500, f"数据解析失败: {str(e)}")

    # 保存数据集元数据
    dataset = Dataset(
        project_id=project_id,
        name=name or file.filename,
        source_type=source_type,
        file_format=ext,
        file_path=str(save_path),
        field_count=load_result["column_count"],
        record_count=load_result["row_count"],
        metadata_json=load_result,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)

    # 保存字段元数据
    for col in load_result["columns"]:
        dtype = load_result["dtypes"].get(col, "text")
        field_type = "numeric" if "int" in dtype or "float" in dtype else "text"
        field = FieldMeta(
            dataset_id=dataset.id,
            field_name=col,
            field_label=col.replace("_", " ").title(),
            field_type=field_type,
        )
        db.add(field)
    await db.commit()

    return {
        "dataset_id": dataset.id,
        "table_name": table_name,
        "source_type": source_type,
        "row_count": load_result["row_count"],
        "column_count": load_result["column_count"],
        "columns": load_result["columns"],
    }


@router.get("/list")
async def list_datasets(project_id: int, db: AsyncSession = Depends(get_db)):
    """列出项目下的所有数据集"""
    result = await db.execute(
        select(Dataset).where(Dataset.project_id == project_id).order_by(Dataset.created_at.desc())
    )
    datasets = result.scalars().all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "source_type": d.source_type,
            "field_count": d.field_count,
            "record_count": d.record_count,
            "created_at": d.created_at.isoformat(),
        }
        for d in datasets
    ]


@router.get("/{dataset_id}/fields")
async def get_dataset_fields(dataset_id: int, db: AsyncSession = Depends(get_db)):
    """获取数据集字段元数据"""
    result = await db.execute(
        select(FieldMeta).where(FieldMeta.dataset_id == dataset_id)
    )
    fields = result.scalars().all()
    return [
        {
            "id": f.id,
            "field_name": f.field_name,
            "field_label": f.field_label,
            "field_type": f.field_type,
            "is_primary_key": f.is_primary_key,
            "mapped_to": f.mapped_to,
        }
        for f in fields
    ]


@router.get("/{dataset_id}/preview")
async def preview_dataset(dataset_id: int, limit: int = 20, db: AsyncSession = Depends(get_db)):
    """预览数据集内容"""
    dataset = await db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "数据集不存在")

    engine = SqlEtlEngine(db)
    table_name = dataset.metadata_json.get("table_name", "")
    if not table_name:
        raise HTTPException(400, "数据集表名缺失")

    result = await engine.preview_table(table_name, limit)
    return result

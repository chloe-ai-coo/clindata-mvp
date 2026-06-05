"""可视化 API — 调用 Python plotly 或 R 生成图表"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.etl.engine import SqlEtlEngine
from app.services.visualization import VisualizationService

router = APIRouter(prefix="/api/viz", tags=["visualization"])


class ChartRequest(BaseModel):
    chart_type: str  # hy_law, timeline, waterfall, bar, box, sankey
    sql: str = ""    # 可选：直接传 SQL 查询数据
    table_name: str = ""  # 可选：从表中取数据
    params: dict = {}     # 图表参数


@router.post("/chart")
async def generate_chart(request: ChartRequest, db: AsyncSession = Depends(get_db)):
    """生成可视化图表（返回 Plotly JSON）"""
    engine = SqlEtlEngine(db)
    viz = VisualizationService()

    # 获取数据
    if request.sql:
        result = await engine.execute_sql(request.sql)
        data = result.get("data", [])
    elif request.table_name:
        result = await engine.preview_table(request.table_name, limit=1000)
        data = result.get("data", [])
    else:
        data = request.params.get("data", [])

    if not data:
        raise HTTPException(400, "无数据可用于生成图表")

    # 根据类型生成图表
    try:
        if request.chart_type == "hy_law":
            chart_json = viz.hy_law_scatter(data)
        elif request.chart_type == "timeline":
            subject_id = request.params.get("subject_id", "unknown")
            chart_json = viz.subject_timeline(data, subject_id)
        elif request.chart_type == "bar":
            chart_json = viz.bar_chart(
                data,
                x_field=request.params.get("x", list(data[0].keys())[0]),
                y_field=request.params.get("y", list(data[0].keys())[1]),
                title=request.params.get("title", "Bar Chart"),
                color_field=request.params.get("color", ""),
            )
        elif request.chart_type == "box":
            chart_json = viz.box_plot(
                data,
                x_field=request.params.get("x", list(data[0].keys())[0]),
                y_field=request.params.get("y", list(data[0].keys())[1]),
                title=request.params.get("title", "Box Plot"),
            )
        elif request.chart_type == "waterfall":
            labels = request.params.get("labels", [d.get("label", "") for d in data])
            values = request.params.get("values", [d.get("value", 0) for d in data])
            chart_json = viz.waterfall_chart(data, labels, values)
        elif request.chart_type == "sankey":
            chart_json = viz.sankey_diagram(data)
        else:
            raise HTTPException(400, f"不支持的图表类型: {request.chart_type}")

        return {"chart_type": request.chart_type, "chart": chart_json}
    except Exception as e:
        raise HTTPException(500, f"图表生成失败: {str(e)}")


@router.post("/r-script")
async def generate_r_script(request: ChartRequest, db: AsyncSession = Depends(get_db)):
    """生成 R 脚本（用于需要 R 特有图表的场景）"""
    engine = SqlEtlEngine(db)
    viz = VisualizationService()

    if request.sql:
        result = await engine.execute_sql(request.sql)
        data = result.get("data", [])
    else:
        data = request.params.get("data", [])

    output_path = f"/tmp/clindata_chart_{request.chart_type}.png"
    script_path = viz.generate_r_script(data, request.chart_type, output_path)

    return {
        "script_path": script_path,
        "output_path": output_path,
        "run_command": f"Rscript {script_path}",
    }

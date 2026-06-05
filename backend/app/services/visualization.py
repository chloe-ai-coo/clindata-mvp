"""可视化服务 — 支持 Python (plotly) 和 R (通过脚本调用)"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


class VisualizationService:
    """临床数据可视化引擎"""

    @staticmethod
    def subject_timeline(data: list[dict], subject_id: str) -> dict:
        """360° 受试者动态档案 — AE/用药/实验室时间轴"""
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=("不良事件 (AE)", "实验室检查 (LB)", "用药记录 (CM)"),
            shared_xaxes=True,
            vertical_spacing=0.08,
        )

        # AE 时间轴
        ae_data = [d for d in data if d.get("domain") == "AE"]
        if ae_data:
            fig.add_trace(
                go.Scatter(
                    x=[d["start_date"] for d in ae_data],
                    y=[d.get("term", "AE") for d in ae_data],
                    mode="markers",
                    marker=dict(size=12, color="red"),
                    name="AE",
                    text=[d.get("severity", "") for d in ae_data],
                ),
                row=1, col=1,
            )

        # LB 时间轴
        lb_data = [d for d in data if d.get("domain") == "LB"]
        if lb_data:
            fig.add_trace(
                go.Scatter(
                    x=[d["date"] for d in lb_data],
                    y=[d.get("value", 0) for d in lb_data],
                    mode="lines+markers",
                    line=dict(color="blue"),
                    name="Lab Value",
                ),
                row=2, col=1,
            )
            # ULN 参考线
            uln = max(d.get("value", 0) for d in lb_data) * 0.8
            fig.add_hline(y=uln, line_dash="dash", line_color="orange",
                          annotation_text="ULN", row=2, col=1)

        # CM 时间轴
        cm_data = [d for d in data if d.get("domain") == "CM"]
        if cm_data:
            fig.add_trace(
                go.Bar(
                    x=[d["start_date"] for d in cm_data],
                    y=[1] * len(cm_data),
                    name="Medication",
                    text=[d.get("drug_name", "") for d in cm_data],
                ),
                row=3, col=1,
            )

        fig.update_layout(height=600, title_text=f"受试者 {subject_id} 动态档案")
        return json.loads(fig.to_json())

    @staticmethod
    def hy_law_scatter(data: list[dict]) -> dict:
        """海氏法则散点图 (Hy's Law)"""
        alt_data = [d for d in data if d.get("test") == "ALT"]
        bil_data = [d for d in data if d.get("test") == "BIL"]

        # 按 subject_id + date 关联
        merged = {}
        for a in alt_data:
            key = f"{a.get('subject_id')}_{a.get('date')}"
            merged.setdefault(key, {})["alt"] = a.get("value", 0)
            merged.setdefault(key, {})["subject_id"] = a.get("subject_id")

        for b in bil_data:
            key = f"{b.get('subject_id')}_{b.get('date')}"
            merged.setdefault(key, {})["bil"] = b.get("value", 0)

        points = list(merged.values())
        x_vals = [p.get("alt", 0) for p in points]
        y_vals = [p.get("bil", 0) for p in points]
        labels = [p.get("subject_id", "") for p in points]

        # Hy's Law 区域: ALT > 3x ULN AND BIL > 2x ULN
        alt_uln = max(x_vals) * 0.33 if x_vals else 100
        bil_uln = max(y_vals) * 0.5 if y_vals else 20

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_vals, y=y_vals,
            mode="markers",
            marker=dict(size=10, color="steelblue"),
            text=labels,
            hovertemplate="Subject: %{text}<br>ALT: %{x}<br>BIL: %{y}<extra></extra>",
        ))

        # Hy's Law 危险区域
        fig.add_shape(
            type="rect", x0=3 * alt_uln, y0=2 * bil_uln,
            x1=max(x_vals) * 1.2 if x_vals else 500,
            y1=max(y_vals) * 1.2 if y_vals else 50,
            fillcolor="red", opacity=0.15, line=dict(color="red", dash="dash"),
        )
        fig.add_annotation(
            x=3 * alt_uln, y=2 * bil_uln,
            text="Hy's Law Zone", showarrow=False,
            font=dict(color="red", size=12),
        )

        fig.update_layout(
            title="海氏法则散点图 (Hy's Law)",
            xaxis_title="ALT (U/L)",
            yaxis_title="BIL (μmol/L)",
            height=500,
        )
        return json.loads(fig.to_json())

    @staticmethod
    def waterfall_chart(data: list[dict], labels: list[str], values: list[float]) -> dict:
        """瀑布图 — 适合展示受试者状态变化"""
        measures = ["relative"] * len(values)
        measures[0] = "absolute"
        measures[-1] = "total"

        fig = go.Figure(go.Waterfall(
            name="Status", orientation="v",
            measure=measures,
            x=labels,
            y=values,
            textposition="outside",
            text=[str(v) for v in values],
            connector=dict(line=dict(color="rgb(63, 63, 63)")),
            increasing=dict(marker=dict(color="green")),
            decreasing=dict(marker=dict(color="red")),
            totals=dict(marker=dict(color="blue")),
        ))
        fig.update_layout(title="受试者状态瀑布图", height=450)
        return json.loads(fig.to_json())

    @staticmethod
    def sankey_diagram(data: list[dict]) -> dict:
        """桑基图 — 受试者流向（筛选→随机化→中止）"""
        # 统计各阶段人数
        stages = {}
        for d in data:
            stage = d.get("stage", "Unknown")
            stages[stage] = stages.get(stage, 0) + 1

        labels = list(stages.keys())
        values = list(stages.values())

        fig = go.Figure(go.Sankey(
            node=dict(
                pad=20, thickness=20,
                label=labels,
                color="blue",
            ),
            link=dict(
                source=[0] * (len(labels) - 1),
                list=list(range(1, len(labels))),
                value=values[1:],
            ),
        ))
        fig.update_layout(title="受试者流向 (Sankey)", height=400)
        return json.loads(fig.to_json())

    @staticmethod
    def bar_chart(data: list[dict], x_field: str, y_field: str,
                  title: str = "Bar Chart", color_field: str = "") -> dict:
        """通用柱状图"""
        fig = px.bar(
            data, x=x_field, y=y_field,
            color=color_field if color_field else None,
            title=title,
        )
        fig.update_layout(height=400)
        return json.loads(fig.to_json())

    @staticmethod
    def box_plot(data: list[dict], x_field: str, y_field: str,
                 title: str = "Box Plot") -> dict:
        """箱线图 — 实验室指标分布"""
        fig = px.box(data, x=x_field, y=y_field, title=title)
        fig.update_layout(height=400)
        return json.loads(fig.to_json())

    @staticmethod
    def generate_r_script(data: list[dict], chart_type: str, output_path: str) -> str:
        """
        生成 R 脚本（用于需要 R 特有图表的场景）。
        调用方式: subprocess.run(["Rscript", script_path])
        """
        r_script = f"""
library(ggplot2)
library(jsonlite)

data <- fromJSON('{json.dumps(data)}')

p <- switch("{chart_type}",
  "histogram" = ggplot(data, aes(x=value)) + geom_histogram(bins=30, fill="steelblue") +
    labs(title="Distribution", x="Value", y="Count"),
  "scatter" = ggplot(data, aes(x=x, y=y)) + geom_point() + geom_smooth(method="lm") +
    labs(title="Scatter Plot"),
  "boxplot" = ggplot(data, aes(x=group, y=value, fill=group)) + geom_boxplot() +
    labs(title="Box Plot"),
  ggplot(data, aes(x=1)) + geom_histogram() + labs(title="Default")
)

ggsave("{output_path}", plot=p, width=8, height=6, dpi=150)
cat(toJSON(list(chart="{chart_type}", file="{output_path}")))
"""
        script_path = output_path.replace(".png", ".R")
        with open(script_path, "w") as f:
            f.write(r_script)
        return script_path

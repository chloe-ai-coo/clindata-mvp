# ClinData MVP — 临床数据智能决策舱

> SQL ETL + 可视化引擎，支持 R/Python 图表

## 快速启动

### 1. 安装 Python 3.10+

```bash
# macOS
brew install python@3.10

# Ubuntu/Debian
sudo apt install python3.10 python3.10-venv

# Windows: 下载 https://www.python.org/downloads/
```

### 2. 创建虚拟环境并安装依赖

```bash
cd clindata-mvp
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 3. 生成演示数据（可选）

```bash
python scripts/generate_demo_data.py
```

### 4. 启动服务

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. 访问

- **API 文档**: http://localhost:8000/docs
- **前端页面**: 打开 `frontend/index.html`

---

## 功能列表

| 功能 | API | 说明 |
|------|-----|------|
| 上传数据 | `POST /api/datasets/upload` | CSV/Excel/HTML 自动识别入库 |
| 列出表 | `GET /api/etl/tables` | 查看数据库中所有表 |
| SQL 查询 | `POST /api/etl/sql` | 直接执行 SELECT 查询 |
| ETL SQL 生成 | `POST /api/etl/generate` | JSON 配置 → SQL |
| 执行 ETL | `POST /api/etl/execute` | 生成 SQL 并运行 |
| 可视化 | `POST /api/viz/chart` | Plotly 图表生成 |
| R 脚本 | `POST /api/viz/r-script` | 生成 R 脚本文件 |

---

## 示例：上传 + 查询 + 可视化

```bash
# 上传 AE 数据
curl -X POST "http://localhost:8000/api/datasets/upload?project_id=1&source_type=ae" \
  -F "file=@demo_data/AE_不良事件.csv"

# 查询严重不良事件
curl -X POST http://localhost:8000/api/etl/sql \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM raw_xxx WHERE aesev='\''SEVERE'\'' LIMIT 10"}'

# 生成柱状图
curl -X POST http://localhost:8000/api/viz/chart \
  -H "Content-Type: application/json" \
  -d '{"chart_type": "bar", "table_name": "raw_xxx", "params": {"x": "aeterm", "y": "subjectid"}}'
```

---

## 技术栈

- **后端**: Python 3.10 + FastAPI + SQLAlchemy + SQLite
- **ETL**: 纯 SQL（关系型数据库）
- **可视化**: Python Plotly + R ggplot2（可选）
- **前端**: 原生 HTML/JS + Plotly.js

## 项目结构

```
clindata-mvp/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 入口
│   │   ├── api/             # REST API 路由
│   │   │   ├── datasets.py  # 数据上传/管理
│   │   │   ├── etl.py       # SQL ETL 引擎
│   │   │   └── visualize.py # 可视化
│   │   ├── core/            # 配置/数据库
│   │   ├── etl/             # ETL 引擎实现
│   │   ├── models/          # 数据模型
│   │   └── services/        # 可视化服务
│   └── requirements.txt
├── frontend/
│   └── index.html           # 前端页面
├── demo_data/               # 模拟数据
├── scripts/                 # 工具脚本
├── start.sh                 # 一键启动
└── README.md
```

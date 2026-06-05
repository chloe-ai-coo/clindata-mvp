"""ClinData — 临床数据智能决策舱 MVP"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.database import init_db
from app.api import datasets, etl, visualize

app = FastAPI(
    title="ClinData MVP",
    description="临床数据智能决策舱 — SQL ETL + 可视化引擎",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(datasets.router)
app.include_router(etl.router)
app.include_router(visualize.router)


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/")
async def root():
    return {
        "name": "ClinData MVP",
        "version": "0.1.0",
        "endpoints": {
            "docs": "/docs",
            "upload": "POST /api/datasets/upload",
            "etl": "POST /api/etl/execute",
            "sql": "POST /api/etl/sql",
            "chart": "POST /api/viz/chart",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}

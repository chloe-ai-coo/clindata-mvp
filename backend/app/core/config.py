"""ClinData 配置"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# 数据库
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DATA_DIR}/clindata.db")

# AI 模型（可选，用于自然语言查询）
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://token-plan-cn.xiaomimimo.com/anthropic")
AI_MODEL = os.getenv("AI_MODEL", "mimo-v2.5-pro")

# 文件上传限制
MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".html", ".json"}

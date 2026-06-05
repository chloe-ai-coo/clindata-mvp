#!/bin/bash
# ClinData MVP 启动脚本

set -e
cd "$(dirname "$0")/backend"

echo "🧬 ClinData MVP 启动中..."

# 检查 Python 环境
if ! command -v python3 &>/dev/null; then
    echo "❌ 需要 Python 3.10+"
    exit 1
fi

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate

# 安装依赖
echo "📦 安装依赖..."
pip install -q -r requirements.txt

# 生成演示数据（如果不存在）
if [ ! -f "../demo_data/DM_人口学.csv" ]; then
    echo "📊 生成演示数据..."
    cd .. && python3 scripts/generate_demo_data.py && cd backend
fi

# 启动服务
echo "🚀 启动 FastAPI 服务..."
echo "   API 文档: http://localhost:8000/docs"
echo "   前端页面: http://localhost:8000/static/index.html"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

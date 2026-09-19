#!/bin/bash
# 开发环境初始化脚本
set -e

echo "=========================================="
echo "  ZSVirt Observer - 开发环境初始化"
echo "=========================================="
echo ""

# 检查 Python
echo "📦 检查 Python 版本..."
python3 --version

# 创建虚拟环境
echo ""
echo "🔧 创建虚拟环境..."
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
echo ""
echo "📥 安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 复制环境变量
if [ ! -f .env ]; then
    echo ""
    echo "📝 复制 .env 配置..."
    cp .env.example .env
    echo "⚠️   请编辑 .env 文件填入 ZSvirt API 信息"
fi

echo ""
echo "=========================================="
echo "  ✅ 初始化完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "  1. 编辑 .env 配置 ZSvirt 连接信息"
echo "  2. 运行 docker-compose up -d"
echo "  3. 开发模式运行: uvicorn app.main:app --reload"
echo ""

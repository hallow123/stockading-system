#!/bin/bash

# 股票自动化交易系统 - 安装脚本
# 使用方法: bash install.sh

echo "========================================"
echo "  股票自动化交易系统 - 安装向导"
echo "========================================"
echo ""

# 1. 检查系统
echo "📋 检查系统要求..."
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ 本系统仅支持 macOS"
    exit 1
fi
echo "✅ 系统检查通过 (macOS)"

# 2. 检查Python
echo ""
echo "📋 检查 Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 未安装 Python 3，请先安装"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "✅ $PYTHON_VERSION"

# 3. 创建虚拟环境（可选）
echo ""
echo "📋 创建虚拟环境..."
cd "$(dirname "$0")"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ 虚拟环境已创建"
else
    echo "✅ 虚拟环境已存在"
fi

# 4. 激活虚拟环境
source venv/bin/activate

# 5. 安装依赖
echo ""
echo "📋 安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 6. 安装系统依赖
echo ""
echo "📋 安装系统依赖..."
if ! command -v cliclick &> /dev/null; then
    echo "安装 cliclick（鼠标控制）..."
    brew install cliclick
else
    echo "✅ cliclick 已安装"
fi

# 7. 配置检查
echo ""
echo "📋 检查配置文件..."
if [ ! -f "config.json" ]; then
    echo "⚠️ config.json 不存在，请编辑模板文件"
fi
if [ ! -f "stocks.json" ]; then
    echo "⚠️ stocks.json 不存在，请编辑模板文件"
fi

# 8. 权限检查
echo ""
echo "📋 检查权限..."
echo "请确保已在 系统设置 → 隐私与安全性 → 屏幕录制 中允许 Python/Terminal"

echo ""
echo "========================================"
echo "  ✅ 安装完成！"
echo "========================================"
echo ""
echo "下一步："
echo "1. 编辑 stocks.json 添加自选股"
echo "2. 编辑 config.json 配置参数"
echo "3. 登录同花顺模拟账户"
echo "4. 运行: source venv/bin/activate && cd scripts && python main.py --daily-report"
echo ""

#!/bin/bash
# 股票自动交易系统 - 启动脚本

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🚀 启动股票自动交易系统..."
echo "📁 工作目录: $SCRIPT_DIR"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查 tkinter
python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ tkinter 未安装，请运行: brew install python-tk"
    exit 1
fi

# 创建必要目录
mkdir -p "$SCRIPT_DIR/data"
mkdir -p "$SCRIPT_DIR/logs"

# 启动应用
exec python3 "$SCRIPT_DIR/app.py"

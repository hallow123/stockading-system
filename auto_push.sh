#!/bin/bash

# 自动推送脚本 - 股票自动化交易系统
cd ~/Desktop/股票自动化交易系统

echo "========== $(date) 开始执行 =========="

# 检查是否有未提交的更改
if [ -n "$(git status --porcelain)" ]; then
    echo "发现更改，正在提交..."
    git add .
    git commit -m "Auto update: $(date '+%Y-%m-%d %H:%M')"
    
    # 尝试推送，设置超时
    echo "正在推送到GitHub..."
    
    # 使用expect处理交互式认证（如果需要）
    # 或者直接推送，带超时
    if git push origin main --timeout=60 2>&1; then
        echo "✅ 已推送到GitHub"
    else
        echo "⚠️ 推送失败，尝试重新推送..."
        sleep 5
        git push origin main --timeout=60 2>&1 || echo "❌ 推送仍然失败"
    fi
else
    echo "没有需要提交的更改"
fi

echo "========== 执行完成 =========="

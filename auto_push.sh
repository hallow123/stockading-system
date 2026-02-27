#!/bin/bash

# 自动推送脚本 - 股票自动化交易系统
cd ~/Desktop/股票自动化交易系统

echo "========== $(date) 开始执行 =========="

# 检查是否有未提交的更改
if [ -n "$(git status --porcelain)" ]; then
    echo "发现更改，正在提交..."
    git add .
    git commit -m "Auto update: $(date '+%Y-%m-%d %H:%M')"
    
    # 尝试推送
    echo "正在推送到GitHub..."
    git push origin main
    
    if [ $? -eq 0 ]; then
        echo "✅ 已推送到GitHub"
    else
        echo "⚠️ 推送失败，尝试重新推送..."
        sleep 3
        git push origin main
        
        if [ $? -eq 0 ]; then
            echo "✅ 重试成功"
        else
            echo "❌ 推送失败"
        fi
    fi
else
    echo "没有需要提交的更改"
fi

echo "========== 执行完成 =========="

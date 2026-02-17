#!/bin/bash

# 自动推送脚本 - 股票自动化交易系统
cd ~/Desktop/股票自动化交易系统

# 检查是否有未提交的更改
if [ -n "$(git status --porcelain)" ]; then
    echo "发现更改，正在提交..."
    git add .
    git commit -m "Auto update: $(date '+%Y-%m-%d %H:%M')"
    git push origin main
    echo "✅ 已推送到GitHub"
else
    echo "没有需要提交的更改"
fi

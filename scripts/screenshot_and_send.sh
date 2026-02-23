#!/bin/bash
# 屏幕截图并通过飞书发送

# 截图保存路径
SCREENSHOT_PATH="/tmp/screenshot.png"

# 1. 截取屏幕
echo "📸 正在截取屏幕..."
/usr/sbin/screencapture -x "$SCREENSHOT_PATH" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "❌ 截图失败！请确保已授权屏幕录制权限"
    echo ""
    echo "授权方法："
    echo "1. 打开 系统设置 → 隐私与安全性 → 屏幕录制"
    echo "2. 添加 Terminal 或 Python 到列表中"
    exit 1
fi

echo "✅ 截图成功: $SCREENSHOT_PATH"

# 2. 通过飞书发送
# 注意：需要飞书Webhook或OpenClaw配置好
echo "📤 发送图片到飞书..."

# 方法A：使用OpenClaw发送（当前环境）
if command -v message &> /dev/null; then
    # 这里需要通过Python调用OpenClaw的API发送
    echo "请通过OpenClaw发送图片"
fi

echo "完成！"

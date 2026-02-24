#!/bin/bash
# 股票自动化交易系统启动脚本

cd "/Users/wangmaofu/Desktop/股票自动化交易系统/scripts"

/opt/homebrew/bin/python3 main.py -r 10 > /dev/null 2>&1 &

# 发送飞书通知
PYTHON3=/opt/homebrew/bin/python3
$PYTHON3 -c "
import requests
import os

# 飞书机器人Webhook（个人Access Token）
WEBHOOK_URL = 'https://open.feishu.cn/open-apis/bot/v2/hook/4ecc5158-0f6e-479d-b3bb-05d226c5c667'

message = {
    'msg_type': 'text',
    'content': {
        'text': '📈 股票自动化交易系统已启动！\n⏰ 监控间隔: 10分钟/次\n💼 自选股: 4只（积成电子、恒邦股份、兴业银行、大华股份）'
    }
}

try:
    requests.post(WEBHOOK_URL, json=message, timeout=10)
except:
    pass
"

echo "股票交易系统已启动 $(date)"

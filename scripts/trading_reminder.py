#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易日提醒脚本
每天晚上8点检查，如果明天是交易日，则发送飞书提醒
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from notification import Notification

def check_and_notify():
    """检查明天是否交易日，如果是则发送提醒"""
    
    try:
        # 获取交易日历
        df = ak.tool_trade_date_hist_sina()
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        
        # 获取所有交易日
        trading_days = set(df['trade_date'].dt.strftime('%Y-%m-%d').tolist())
        
        # 计算明天的日期
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        print(f"今天: {datetime.now().strftime('%Y-%m-%d')}")
        print(f"明天: {tomorrow}")
        
        if tomorrow in trading_days:
            print(f"✅ 明天({tomorrow})是交易日，发送提醒...")
            
            # 发送飞书通知
            notifier = Notification()
            notifier.send_message(f"""
📅 **明日交易提醒**

明天({tomorrow})是交易日！

请启动自动监控：
```bash
cd "/Users/wangmaofu/Desktop/股票自动化交易系统/scripts"
nohup python3 main.py --realtime-monitor 15 > /tmp/trading.log 2>&1 &
```

交易时段: 9:30-11:30, 13:00-15:00
            """)
            print("✅ 提醒已发送")
        else:
            print(f"❌ 明天({tomorrow})不是交易日，无需提醒")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        # 备用：发送错误通知
        try:
            notifier = Notification()
            notifier.send_message(f"❌ 交易日检查失败: {e}")
        except:
            pass

if __name__ == "__main__":
    check_and_notify()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知模块
负责发送交易信号、告警、报告到飞书/微信
"""

import json
import requests
from datetime import datetime
from pathlib import Path

from config import config
from logger import Logger


class Notification:
    """通知管理类"""
    
    def __init__(self):
        self.logger = Logger.get_logger("notification")
        
        # 通知配置
        notif_config = config.get_notification_config()
        self.feishu_webhook = notif_config.get('feishu_webhook', '')
        self.feishu_user_id = notif_config.get('feishu_user_id', '')
        self.enable_realtime_alert = notif_config.get('enable_realtime_alert', True)
        self.enable_daily_report = notif_config.get('enable_daily_report', True)
    
    def send_feishu_message(self, message: str, msg_type: str = "text") -> bool:
        """
        发送飞书消息
        msg_type: "text" 或 "post"
        """
        if not self.feishu_webhook:
            self.logger.warning("飞书Webhook未配置")
            # 打印到控制台作为备选
            print(f"\n{'='*50}")
            print("📢 通知消息:")
            print(message)
            print(f"{'='*50}\n")
            return True  # 返回成功，避免阻塞
        
        try:
            if msg_type == "text":
                payload = {
                    "msg_type": "text",
                    "content": {
                        "text": message
                    }
                }
            else:
                payload = {
                    "msg_type": "post",
                    "content": {
                        "post": {
                            "zh_cn": {
                                "title": "股票交易系统通知",
                                "content": [[{"tag": "text", "text": message}]]
                            }
                        }
                    }
                }
            
            response = requests.post(
                self.feishu_webhook,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    self.logger.info("飞书消息发送成功")
                    return True
                else:
                    self.logger.error(f"飞书消息发送失败: {result.get('msg')}")
                    return False
            else:
                self.logger.error(f"飞书HTTP请求失败: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            self.logger.error(f"发送飞书消息失败: {e}")
            return False
    
    def send_buy_signal(self, stock_info: dict, signals: list, confidence: int) -> bool:
        """
        发送买入信号通知
        """
        message = f"""
🟢 买入信号提醒

股票: {stock_info.get('name', '')}({stock_info.get('code', '')})
当前价格: {stock_info.get('price', 0):.2f}
涨跌幅: {stock_info.get('change_pct', 0):+.2f}%

买入理由:
"""
        for sig in signals:
            message += f"  • {sig}\n"
        
        message += f"""
置信度: {confidence}%

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return self.send_feishu_message(message)
    
    def send_sell_signal(self, stock_info: dict, signals: list) -> bool:
        """
        发送卖出信号通知
        """
        message = f"""
🔴 卖出信号提醒

股票: {stock_info.get('name', '')}({stock_info.get('code', '')})
当前价格: {stock_info.get('price', 0):.2f}
涨跌幅: {stock_info.get('change_pct', 0):+.2f}%

卖出原因:
"""
        for sig in signals:
            message += f"  • {sig}\n"
        
        message += f"""
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return self.send_feishu_message(message)
    
    def send_price_query_result(self, prices: dict, success_count: int, failed_count: int, failed_stocks: list = None) -> bool:
        """
        发送股价查询结果通知
        """
        message = f"""
📊 股价查询完成

查询成功: {success_count}只
查询失败: {failed_count}只
"""
        
        if failed_stocks:
            message += f"失败股票: {', '.join(failed_stocks)}\n"
        
        message += "\n📈 自选股行情:\n"
        for code, info in prices.items():
            name = info.get('name', code)
            price = info.get('price', 0)
            change = info.get('change_pct', 0)
            signal = info.get('signal', '观望')
            message += f"  • {name}({code}): ¥{price:.2f} {change:+.2f}% [{signal}]\n"
        
        message += f"\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return self.send_feishu_message(message)
    
    def send_trade_result(self, trade_type: str, stock_name: str, stock_code: str, price: float, quantity: int, success: bool, error: str = None) -> bool:
        """
        发送交易结果通知
        """
        emoji = "✅" if success else "❌"
        direction = "买入" if trade_type == "BUY" else "卖出"
        
        message = f"""
{emoji} 交易{'成功' if success else '失败'}

方向: {direction}
股票: {stock_name}({stock_code})
价格: ¥{price:.2f}
数量: {quantity}股
金额: ¥{price * quantity:,.2f}
"""
        
        if not success and error:
            message += f"\n错误: {error}"
        
        message += f"\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return self.send_feishu_message(message)
    
    def send_trade_confirmation(self, trade_info: dict) -> bool:
        """
        发送交易确认请求
        """
        trade_type = trade_info.get('type', '')
        message = f"""
⚡ 交易确认请求

{'🟢 买入' if trade_type == 'BUY' else '🔴 卖出'}

股票: {trade_info.get('stock_name', '')}({trade_info.get('stock_code', '')})
价格: {trade_info.get('price', 0):.2f}
数量: {trade_info.get('quantity', 0)}

请在30秒内确认是否执行交易。

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return self.send_feishu_message(message)
    
    def send_trade_result_from_dict(self, trade_result: dict) -> bool:
        """
        发送交易结果通知
        """
        success = trade_result.get('success', False)
        trade_type = trade_result.get('type', '')
        
        if success:
            message = f"""
✅ 交易执行成功

{'🟢 买入' if trade_type == 'BUY' else '🔴 卖出'}

股票: {trade_result.get('stock_name', '')}({trade_result.get('stock_code', '')})
价格: {trade_result.get('price', 0):.2f}
数量: {trade_result.get('quantity', 0)}
"""
            if 'profit_loss' in trade_result:
                profit = trade_result.get('profit_loss', 0)
                message += f"盈亏: {profit:+.2f}\n"
            
            message += f"""
时间: {trade_result.get('timestamp', '')}
"""
        else:
            message = f"""
❌ 交易执行失败

股票: {trade_result.get('stock_name', '')}({trade_result.get('stock_code', '')})
原因: {trade_result.get('error', '未知错误')}

时间: {trade_result.get('timestamp', '')}
"""
        
        return self.send_feishu_message(message)
    
    def send_daily_report(self, report_content: str) -> bool:
        """
        发送每日报告
        """
        message = f"""
📊 每日股票分析报告

{report_content}

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return self.send_feishu_message(message)
    
    def send_alert(self, alerts: list) -> bool:
        """
        发送实时告警
        """
        if not alerts:
            return True
        
        message = f"""
🚨 实时告警

"""
        for alert in alerts:
            message += f"""
股票: {alert.get('name', '')}({alert.get('code', '')})
价格: {alert.get('price', 0):.2f}
原因: {alert.get('reason', '')}
"""
        
        message += f"""
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return self.send_feishu_message(message)
    
    def send_system_status(self, status: str) -> bool:
        """
        发送系统状态
        """
        message = f"""
🔔 系统状态

{status}

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return self.send_feishu_message(message)


# 测试代码
if __name__ == "__main__":
    notifier = Notification()
    
    # 测试发送买入信号
    stock_info = {
        'code': '002339',
        'name': '积成电子',
        'price': 10.50,
        'change_pct': -1.5
    }
    signals = ["均线多头排列", "当日跌幅1.5%", "换手率3.5%"]
    
    notifier.send_buy_signal(stock_info, signals, 75)

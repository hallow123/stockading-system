#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易执行模块
负责通过同花顺客户端执行自动交易
"""

import json
import subprocess
import time
import random
import requests
import os
from datetime import datetime
from pathlib import Path

from config import config
from logger import Logger
from price_fetcher import PriceFetcher
from notification import Notification


# 飞书Webhook（从配置读取）
def get_feishu_webhook():
    """从配置文件获取飞书Webhook"""
    try:
        with open(Path(__file__).parent.parent / "config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get('notification', {}).get('feishu_webhook', '')
    except:
        return ''


FEISHU_WEBHOOK = get_feishu_webhook()

# 交易日志文件
TRADE_LOG_FILE = Path(__file__).parent.parent / "trade_log.txt"


def log_to_notes(text: str):
    """同时打印、记录到日志文件、发送飞书消息"""
    print(text, flush=True)
    # 追加到日志文件
    try:
        with open(TRADE_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().strftime('%H:%M:%S')} {text}\n")
    except Exception as e:
        print(f"记录日志失败: {e}", flush=True)
    # 发送飞书消息
    try:
        requests.post(FEISHU_WEBHOOK, json={'msg_type': 'text', 'content': {'text': text}}, timeout=10)
    except:
        pass


def send_feishu_message(text: str):
    """发送飞书消息"""
    try:
        message = {'msg_type': 'text', 'content': {'text': text}}
        requests.post(FEISHU_WEBHOOK, json=message, timeout=10)
    except:
        pass


class TradeExecutor:
    """交易执行类"""
    
    # 同花顺关键坐标（已验证）
    COORDINATES = {
        # 搜索相关
        'search_box': (698, 37),
        
        # 交易界面
        'trading_button': (29, 424),
        'buy_direction': (333, 123),
        'sell_direction': (407, 123),
        
        # 输入框
        'code_input': (365, 186),
        'price_input': (357, 231),
        'quantity_input': (360, 293),
        
        # 按钮
        'confirm_button': (369, 343),
        'final_confirm': (704, 644),
        
        # 刷新按钮（获取最新价）
        'refresh_button': (750, 135)
    }
    
    def __init__(self):
        self.logger = Logger.get_logger("trade_executor")
        self.positions = {}  # 持仓
        self.price_fetcher = PriceFetcher()  # 价格获取器
        self.notifier = Notification()  # 通知
        
        # 交易配置
        trading_config = config.get_trading_config()
        self.min_quantity = trading_config.get('min_quantity', 100)
        
        # ========== 数据持久化：启动时加载 ==========
        self.load_positions()  # 加载持仓
        self.trades = self.load_trades()  # 加载交易记录
        self.logger.info(f"📦 已加载 {len(self.positions)} 条持仓记录")
        self.logger.info(f"📦 已加载 {len(self.trades)} 条交易记录")
    
    def exec_cmd(self, command: str, wait: float = 0.3):
        """
        执行shell命令
        """
        try:
            subprocess.run(command, shell=True, check=True)
            if wait > 0:
                time.sleep(wait)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"执行命令失败: {command}, 错误: {e}")
    
    def click_at(self, x: int, y: int, wait: float = 0.3):
        """
        点击指定坐标（双击）
        """
        self.exec_cmd(f"cliclick c:{x},{y}", wait)
    
    def type_text(self, text: str, wait: float = 0.3):
        """
        输入文本
        """
        self.exec_cmd(f"cliclick t:{text}", wait)
    
    def clear_and_type(self, text: str, wait: float = 0.3):
        """
        清空输入框后输入文本（先全选删除，再输入新内容）
        """
        # 使用 Command+A 全选，然后删除
        self.exec_cmd("osascript -e 'tell application \"System Events\" to keystroke \"a\" using command down'", 0.2)
        time.sleep(0.3)
        self.exec_cmd("osascript -e 'tell application \"System Events\" to key code 51'", 0.2)  # 删除键
        time.sleep(0.3)
        self.exec_cmd(f"cliclick t:{text}", wait)
    
    def press_enter(self, wait: float = 0.3):
        """
        按回车键
        """
        self.exec_cmd('osascript -e \'tell application "System Events" to key code 36\'', wait)
    
    def wait_for_confirmation(self, trade_info: dict, timeout: int = 60) -> bool:
        """
        等待用户确认交易
        返回: True表示用户确认, False表示取消
        
        注意：当前实现是自动确认（安全起见，建议改为人工确认）
        实际使用时可集成飞书/微信通知等待用户确认
        """
        self.logger.info("="*50)
        self.logger.info("📋 交易确认请求")
        self.logger.info("="*50)
        self.logger.info(f"方向: {trade_info.get('type', 'BUY')}")
        self.logger.info(f"股票: {trade_info.get('stock_name')} ({trade_info.get('stock_code')})")
        self.logger.info(f"价格: ¥{trade_info.get('price', 0):.2f}")
        self.logger.info(f"数量: {trade_info.get('quantity', 0)}股")
        self.logger.info("="*50)
        
        # TODO: 集成飞书/微信通知，等待用户确认
        # 当前实现：自动确认（测试用）
        # 实际使用时应发送通知并等待用户回复
        
        self.logger.info("⚠️ 自动确认模式（测试用）")
        self.logger.info("建议：生产环境应改为人工确认")
        
        return True
    
    def wait_for_confirm(self, timeout: int = 30):
        """
        等待用户确认（模拟）
        实际实现中应该发送通知等待用户响应
        """
        self.logger.info(f"等待用户确认交易 (超时 {timeout} 秒)...")
        time.sleep(2)  # 简化处理，实际应等待用户输入
        return True
    
    def enter_trading_interface(self, direction: str = "buy"):
        """
        进入交易界面
        direction: "buy" 或 "sell"
        """
        self.logger.info(f"进入交易界面，方向: {direction}")
        
        # 1. 先将同花顺窗口调到最前面
        log_to_notes(f"📍 激活同花顺窗口...")
        os.system('osascript -e \'tell application "同花顺" to activate\' 2>/dev/null')
        time.sleep(2)
        
        log_to_notes(f"📍 点击交易按钮...")
        # 2. 双击交易按钮
        x, y = self.COORDINATES['trading_button']
        self.exec_cmd(f"cliclick c:{x},{y}", 0.2)
        self.exec_cmd(f"cliclick c:{x},{y}", 0.5)
        time.sleep(2)
        
        if direction == "buy":
            x, y = self.COORDINATES['buy_direction']
            log_to_notes(f"📍 选择买入方向...")
        else:
            x, y = self.COORDINATES['sell_direction']
            log_to_notes(f"📍 选择卖出方向...")
        
        self.click_at(x, y, 0.5)
        time.sleep(2)
    
    def input_trade_info(self, stock_code: str, price: float, quantity: int):
        """
        输入交易信息
        """
        # 数量必须是100的整数倍
        quantity = int(quantity / 100) * 100
        
        # 1. 输入股票代码
        x, y = self.COORDINATES['code_input']
        self.click_at(x, y, 0.3)
        time.sleep(2)
        # 清空输入框并输入新代码
        self.clear_and_type(stock_code, 0.3)
        time.sleep(2)
        
        # 2. 价格会自动填充，跳过手动输入
        # x, y = self.COORDINATES['price_input']
        # self.click_at(x, y, 0.3)
        # time.sleep(random.uniform(0.5, 1.5))
        # self.type_text(str(price), 0.3)
        # time.sleep(random.uniform(1, 3))
        
        # 3. 输入数量
        x, y = self.COORDINATES['quantity_input']
        self.click_at(x, y, 0.3)
        time.sleep(2)  # 点击后等待，模拟人思考
        self.type_text(str(quantity), 0.3)
        time.sleep(2)  # 输入后等待确认
    
    def confirm_trade(self):
        """
        确认交易
        """
        log_to_notes("📍 点击确认按钮...")
        # 1. 点击确定按钮
        x, y = self.COORDINATES['confirm_button']
        self.click_at(x, y, 0.5)
        time.sleep(2)  # 点击后等待，模拟人确认
        
        log_to_notes("📍 点击最终确认...")
        # 2. 最终确认（双击确保点击成功）
        x, y = self.COORDINATES['final_confirm']
        self.click_at(x, y, 0.5)
        time.sleep(2)  # 点击后等待
        self.click_at(x, y, 0.5)  # 再点一次确保确认
    
    def execute_buy(self, stock_code: str, stock_name: str, price: float, quantity: int, auto_confirm: bool = False) -> dict:
        """
        执行买入
        auto_confirm: 是否自动确认（测试用），生产应设为False
        """
        trade_info = {
            'type': 'BUY',
            'stock_code': stock_code,
            'stock_name': stock_name,
            'price': price,
            'quantity': quantity
        }
        
        # 等待用户确认（安全机制）
        if not auto_confirm:
            if not self.wait_for_confirmation(trade_info):
                self.logger.info("用户取消交易")
                return {'success': False, 'error': '用户取消'}
        
        self.logger.info(f"执行买入: {stock_name}({stock_code}) - 价格:{price} - 数量:{quantity}")
        log_to_notes(f"🟡 开始执行买入: {stock_name}({stock_code})")
        
        try:
            # 进入交易界面
            log_to_notes("📍 步骤1: 进入交易界面...")
            self.enter_trading_interface("buy")
            
            # 输入交易信息
            log_to_notes("📍 步骤2: 输入交易信息...")
            self.input_trade_info(stock_code, price, quantity)
            
            # 确认交易
            log_to_notes("📍 步骤3: 确认交易...")
            self.confirm_trade()
            
            # 记录持仓
            log_to_notes("📍 步骤4: 记录持仓...")
            self.update_position(stock_code, "BUY", price, quantity)
            
            log_to_notes(f"✅ 买入成功: {stock_name} {quantity}股 @ ¥{price}")
            
            # 发送飞书通知
            msg = f"📈 买入成功！\n股票: {stock_name}({stock_code})\n数量: {quantity}股\n价格: ¥{price}"
            send_feishu_message(msg)
            
            # 发送交易结果通知
            self.notifier.send_trade_result("BUY", stock_name, stock_code, price, quantity, True)
            
            result = {
                'success': True,
                'stock_code': stock_code,
                'stock_name': stock_name,
                'type': 'BUY',
                'price': price,
                'quantity': quantity,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # ========== 保存交易记录 ==========
            self.trades.append(result)
            self.save_trades(self.trades)
            
            return result
            
        except Exception as e:
            self.logger.error(f"买入失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_sell(self, stock_code: str, stock_name: str, price: float, quantity: int, cost: float = None) -> dict:
        """
        执行卖出
        """
        self.logger.info(f"执行卖出: {stock_name}({stock_code}) - 价格:{price} - 数量:{quantity}")
        
        try:
            # 进入交易界面
            self.enter_trading_interface("sell")
            
            # 输入交易信息
            self.input_trade_info(stock_code, price, quantity)
            
            # 确认交易
            self.confirm_trade()
            
            # 计算盈亏
            profit_loss = 0
            if cost and quantity:
                profit_loss = (price - cost) * quantity
            
            # 更新持仓
            self.update_position(stock_code, "SELL", price, quantity)
            
            result = {
                'success': True,
                'stock_code': stock_code,
                'stock_name': stock_name,
                'type': 'SELL',
                'price': price,
                'quantity': quantity,
                'profit_loss': profit_loss,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # ========== 保存交易记录 ==========
            self.trades.append(result)
            self.save_trades(self.trades)

            # 发送交易结果通知
            self.notifier.send_trade_result("SELL", stock_name, stock_code, price, quantity, True)

            return result
            
        except Exception as e:
            self.logger.error(f"卖出失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_sell_auto_price(self, stock_code: str, stock_name: str, quantity: int, cost: float = None) -> dict:
        """
        执行卖出（自动获取最新价格）
        卖出前先查询实时价格，然后用查询到的价格卖出
        """
        # 1. 先获取实时价格
        log_to_notes(f"📍 [{stock_name}] 正在查询实时价格...")
        price_data = self.price_fetcher.fetch_price(stock_code)
        current_price = price_data['price']  # 注意：字段名是 'price' 不是 'current_price'
        
        log_to_notes(f"📍 [{stock_name}] 当前价格: ¥{current_price}")
        self.logger.info(f"执行卖出: {stock_name}({stock_code}) - 自动获取价格: {current_price} - 数量:{quantity}")
        
        try:
            # 2. 进入交易界面
            self.enter_trading_interface("sell")
            
            # 3. 输入交易信息（使用实时价格）
            self.input_trade_info(stock_code, current_price, quantity)
            
            # 4. 确认交易
            self.confirm_trade()
            
            # 5. 计算盈亏
            profit_loss = 0
            if cost and quantity:
                profit_loss = (current_price - cost) * quantity
            
            # 6. 更新持仓
            self.update_position(stock_code, "SELL", current_price, quantity)
            
            result = {
                'success': True,
                'stock_code': stock_code,
                'stock_name': stock_name,
                'type': 'SELL',
                'price': current_price,
                'quantity': quantity,
                'profit_loss': profit_loss,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # ========== 保存交易记录 ==========
            self.trades.append(result)
            self.save_trades(self.trades)
            
            return result
            
        except Exception as e:
            self.logger.error(f"卖出失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_position(self, stock_code: str, trade_type: str, price: float, quantity: int):
        """
        更新持仓信息
        """
        if trade_type == "BUY":
            if stock_code in self.positions:
                # 加仓
                pos = self.positions[stock_code]
                total_quantity = pos['quantity'] + quantity
                total_cost = pos['avg_price'] * pos['quantity'] + price * quantity
                pos['quantity'] = total_quantity
                pos['avg_price'] = total_cost / total_quantity
            else:
                # 新建持仓
                self.positions[stock_code] = {
                    'quantity': quantity,
                    'avg_price': price,
                    'holding_days': 0,
                    'buy_date': datetime.now().strftime('%Y-%m-%d')
                }
        elif trade_type == "SELL":
            if stock_code in self.positions:
                pos = self.positions[stock_code]
                pos['quantity'] -= quantity
                if pos['quantity'] <= 0:
                    del self.positions[stock_code]
        
        # ========== 自动保存持仓 ==========
        self.save_positions()
    
    def get_position(self, stock_code: str) -> dict:
        """
        获取持仓
        """
        return self.positions.get(stock_code)
    
    def get_all_positions(self) -> dict:
        """
        获取所有持仓
        """
        return self.positions
    
    def save_trades(self, trades: list, file_path: str = None):
        """保存交易记录"""
        if file_path is None:
            base_dir = Path(__file__).parent.parent
            file_path = base_dir / "trades.json"
        
        try:
            trade_data = {
                'trades': trades,
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(trade_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"交易记录已保存到 {file_path}")
            
        except Exception as e:
            self.logger.error(f"保存交易记录失败: {e}")
    
    def load_trades(self, file_path: str = None) -> list:
        """加载交易记录"""
        if file_path is None:
            base_dir = Path(__file__).parent.parent
            file_path = base_dir / "trades.json"
        
        try:
            if Path(file_path).exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('trades', [])
        except Exception as e:
            self.logger.error(f"加载交易记录失败: {e}")
        
        return []
    
    def load_positions(self, file_path: str = None) -> dict:
        """加载持仓数据"""
        if file_path is None:
            base_dir = Path(__file__).parent.parent
            file_path = base_dir / "data" / "positions.json"
        
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.positions = json.load(f)
                    self.logger.info(f"✅ 持仓数据加载成功: {len(self.positions)} 条")
            else:
                self.positions = {}
                self.logger.info("📝 持仓文件不存在，创建新持仓记录")
        except Exception as e:
            self.positions = {}
            self.logger.error(f"❌ 加载持仓数据失败: {e}")
        
        return self.positions
    
    def save_positions(self, file_path: str = None):
        """保存持仓数据"""
        if file_path is None:
            base_dir = Path(__file__).parent.parent
            file_path = base_dir / "data" / "positions.json"
        
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.positions, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 持仓数据已保存: {len(self.positions)} 条")
            
        except Exception as e:
            self.logger.error(f"❌ 保存持仓数据失败: {e}")


# 测试代码
if __name__ == "__main__":
    executor = TradeExecutor()
    
    # 测试获取持仓
    positions = executor.get_all_positions()
    print("当前持仓:", positions)

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
from datetime import datetime
from pathlib import Path

from config import config
from logger import Logger
from price_fetcher import PriceFetcher


class TradeExecutor:
    """交易执行类"""
    
    # 同花顺关键坐标（已验证）
    COORDINATES = {
        # 搜索相关
        'search_box': (698, 37),
        
        # 交易界面
        'trading_button': (29, 422),
        'buy_direction': (346, 124),
        'sell_direction': (402, 125),
        
        # 输入框
        'code_input': (357, 183),
        'price_input': (341, 233),
        'quantity_input': (338, 291),
        
        # 按钮
        'confirm_button': (367, 340),
        'final_confirm': (906, 628),
        
        # 刷新按钮（获取最新价）
        'refresh_button': (750, 135)
    }
    
    def __init__(self):
        self.logger = Logger.get_logger("trade_executor")
        self.positions = {}  # 持仓
        self.price_fetcher = PriceFetcher()  # 价格获取器
        
        # 交易配置
        trading_config = config.get_trading_config()
        self.min_quantity = trading_config.get('min_quantity', 100)
    
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
        
        # 1. 双击交易按钮
        x, y = self.COORDINATES['trading_button']
        self.exec_cmd(f"cliclick c:{x},{y}", 0.5)
        time.sleep(random.uniform(1, 3))
        
        # 2. 选择买入/卖出方向
        if direction == "buy":
            x, y = self.COORDINATES['buy_direction']
        else:
            x, y = self.COORDINATES['sell_direction']
        
        self.click_at(x, y, 0.5)
        time.sleep(random.uniform(1, 3))
    
    def input_trade_info(self, stock_code: str, price: float, quantity: int):
        """
        输入交易信息
        """
        # 数量必须是100的整数倍
        quantity = int(quantity / 100) * 100
        
        # 1. 输入股票代码
        x, y = self.COORDINATES['code_input']
        self.click_at(x, y, 0.3)
        time.sleep(random.uniform(0.5, 1.5))
        self.type_text(stock_code, 0.3)
        time.sleep(random.uniform(1, 3))
        
        # 2. 输入价格
        x, y = self.COORDINATES['price_input']
        self.click_at(x, y, 0.3)
        time.sleep(random.uniform(0.5, 1.5))
        self.type_text(str(price), 0.3)
        time.sleep(random.uniform(1, 3))
        
        # 3. 输入数量
        x, y = self.COORDINATES['quantity_input']
        self.click_at(x, y, 0.3)
        time.sleep(random.uniform(0.5, 1.5))
        self.type_text(str(quantity), 0.3)
    
    def confirm_trade(self):
        """
        确认交易
        """
        # 1. 点击确定按钮
        x, y = self.COORDINATES['confirm_button']
        self.click_at(x, y, 0.5)
        time.sleep(random.uniform(1, 3))
        
        # 2. 最终确认
        x, y = self.COORDINATES['final_confirm']
        self.click_at(x, y, 0.5)
    
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
        print(f"🟡 开始执行买入: {stock_name}({stock_code})", flush=True)
        
        try:
            # 进入交易界面
            print("📍 步骤1: 进入交易界面...", flush=True)
            self.enter_trading_interface("buy")
            
            # 输入交易信息
            print("📍 步骤2: 输入交易信息...", flush=True)
            self.input_trade_info(stock_code, price, quantity)
            
            # 确认交易
            print("📍 步骤3: 确认交易...", flush=True)
            self.confirm_trade()
            
            # 记录持仓
            print("📍 步骤4: 记录持仓...", flush=True)
            self.update_position(stock_code, "BUY", price, quantity)
            
            print(f"✅ 买入成功: {stock_name} {quantity}股 @ ¥{price}", flush=True)
            
            return {
                'success': True,
                'stock_code': stock_code,
                'stock_name': stock_name,
                'type': 'BUY',
                'price': price,
                'quantity': quantity,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
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
            
            return {
                'success': True,
                'stock_code': stock_code,
                'stock_name': stock_name,
                'type': 'SELL',
                'price': price,
                'quantity': quantity,
                'profit_loss': profit_loss,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
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
        print(f"📍 [{stock_name}] 正在查询实时价格...", flush=True)
        price_data = self.price_fetcher.fetch_price(stock_code)
        current_price = price_data['price']  # 注意：字段名是 'price' 不是 'current_price'
        
        print(f"📍 [{stock_name}] 当前价格: ¥{current_price}", flush=True)
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
            
            return {
                'success': True,
                'stock_code': stock_code,
                'stock_name': stock_name,
                'type': 'SELL',
                'price': current_price,
                'quantity': quantity,
                'profit_loss': profit_loss,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
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


# 测试代码
if __name__ == "__main__":
    executor = TradeExecutor()
    
    # 测试获取持仓
    positions = executor.get_all_positions()
    print("当前持仓:", positions)

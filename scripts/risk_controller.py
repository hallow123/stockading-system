#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险控制模块
负责仓位管理、止损止盈检查、交易安全检查
"""

import json
from datetime import datetime
from pathlib import Path

from config import config
from logger import Logger


class RiskController:
    """风险控制类"""
    
    def __init__(self):
        self.logger = Logger.get_logger("risk_controller")
        
        # 交易配置
        trading_config = config.get_trading_config()
        self.max_position_ratio = trading_config.get('max_position_ratio', 0.5)  # 最大仓位50%
        self.max_daily_loss = trading_config.get('max_daily_loss', 0.1)  # 最大日亏损10%
        self.stop_loss_ratio = trading_config.get('stop_loss_ratio', 0.05)  # 止损线5%
        self.take_profit_ratio = trading_config.get('take_profit_ratio', 0.10)  # 止盈线10%
        
        # 持仓 - 加载数据
        self.positions = self.load_positions()
        
        # 账户余额（模拟）
        self.account_balance = 100000.0  # 初始10万
    
    def is_trading_hours(self) -> bool:
        """
        检查是否在交易时间
        """
        now = datetime.now()
        
        # 周末不交易
        if now.weekday() >= 5:
            return False
        
        # A股交易时间: 9:30-11:30, 13:00-15:00
        current_time = now.hour * 60 + now.minute
        
        morning_start = 9 * 60 + 30
        morning_end = 11 * 60 + 30
        afternoon_start = 13 * 60
        afternoon_end = 15 * 60
        
        return (morning_start <= current_time <= morning_end) or \
               (afternoon_start <= current_time <= afternoon_end)
    
    def check_position_risk(self, stock_code: str, quantity: int, price: float) -> tuple:
        """
        检查仓位风险
        返回: (是否通过, 消息)
        """
        position_value = quantity * price
        total_value = self.get_total_value()
        
        if total_value > 0:
            position_ratio = position_value / total_value
            
            if position_ratio > self.max_position_ratio:
                return False, f"❌ 单只股票仓位超过{int(self.max_position_ratio*100)}%限制 ({position_ratio:.1%})"
        
        return True, "✅ 仓位检查通过"
    
    def check_total_position(self) -> tuple:
        """
        检查总仓位
        返回: (仓位比例, 消息)
        """
        total_value = self.get_total_value()
        position_ratio = total_value / self.account_balance if self.account_balance > 0 else 0
        
        if position_ratio >= self.max_position_ratio:
            return position_ratio, f"⚠️ 总仓位已满 ({position_ratio:.1%})"
        
        return position_ratio, f"当前仓位: {position_ratio:.1%}"
    
    def check_stop_loss(self, stock_code: str, current_price: float) -> tuple:
        """
        检查是否触发止损
        返回: (是否触发, 消息)
        """
        if stock_code not in self.positions:
            return False, ""
        
        position = self.positions[stock_code]
        cost = position.get('avg_price', 0)
        
        if not cost or cost == 0:
            return False, ""
        
        loss_ratio = (current_price - cost) / cost
        
        if loss_ratio <= -self.stop_loss_ratio:
            return True, f"⚠️ 触发{int(self.stop_loss_ratio*100)}%止损线 (当前亏损{loss_ratio:.1%})"
        
        return False, ""
    
    def check_take_profit(self, stock_code: str, current_price: float) -> tuple:
        """
        检查是否触发止盈
        返回: (是否触发, 消息)
        """
        if stock_code not in self.positions:
            return False, ""
        
        position = self.positions[stock_code]
        cost = position.get('avg_price', 0)
        
        if not cost or cost == 0:
            return False, ""
        
        profit_ratio = (current_price - cost) / cost
        
        if profit_ratio >= self.take_profit_ratio:
            return True, f"🎯 触发{int(self.take_profit_ratio*100)}%止盈线 (当前盈利{profit_ratio:.1%})"
        
        return False, ""
    
    def should_trade(self, trade_type: str, stock_code: str, price: float, quantity: int) -> tuple:
        """
        综合判断是否允许交易
        返回: (是否允许, 消息列表)
        """
        messages = []
        can_trade = True
        
        # 1. 检查是否交易时间
        if not self.is_trading_hours():
            messages.append("❌ 非交易时间")
            can_trade = False
        
        # 2. 检查总仓位
        position_ratio, msg = self.check_total_position()
        messages.append(msg)
        
        if position_ratio >= self.max_position_ratio and trade_type == "BUY":
            can_trade = False
        
        # 3. 对于买入，检查单只仓位
        if trade_type == "BUY":
            passed, msg = self.check_position_risk(stock_code, quantity, price)
            messages.append(msg)
            if not passed:
                can_trade = False
        
        # 4. 对于卖出，检查是否持仓
        if trade_type == "SELL":
            if stock_code not in self.positions:
                messages.append("⚠️ 当前无持仓")
                can_trade = False
            else:
                # 5. T+1检查：当日买入不能当日卖出
                position = self.positions[stock_code]
                buy_date = position.get('buy_date', '')
                today = datetime.now().strftime('%Y-%m-%d')
                
                if buy_date == today:
                    messages.append(f"⚠️ T+1规则：{buy_date}买入，今天不能卖出")
                    can_trade = False
        
        # 6. 止损止盈检查（针对卖出）
        if trade_type == "SELL":
            stop_loss_triggered, msg = self.check_stop_loss(stock_code, price)
            if stop_loss_triggered:
                messages.append(msg)
            
            take_profit_triggered, msg = self.check_take_profit(stock_code, price)
            if take_profit_triggered:
                messages.append(msg)
        
        return can_trade, messages
    
    def get_total_value(self) -> float:
        """
        计算持仓总价值
        """
        total = 0
        for pos in self.positions.values():
            total += pos['quantity'] * pos.get('current_price', pos['avg_price'])
        return total
    
    def get_available_balance(self) -> float:
        """
        获取可用资金
        """
        return self.account_balance - self.get_total_value()
    
    def update_position_price(self, stock_code: str, current_price: float):
        """
        更新持仓的当前价格
        """
        if stock_code in self.positions:
            self.positions[stock_code]['current_price'] = current_price
    
    def add_position(self, stock_code: str, quantity: int, price: float):
        """
        添加持仓
        """
        if stock_code in self.positions:
            pos = self.positions[stock_code]
            total_quantity = pos['quantity'] + quantity
            total_cost = pos['avg_price'] * pos['quantity'] + price * quantity
            pos['quantity'] = total_quantity
            pos['avg_price'] = total_cost / total_quantity
            pos['current_price'] = price
        else:
            self.positions[stock_code] = {
                'quantity': quantity,
                'avg_price': price,
                'current_price': price,
                'holding_days': 0,
                'buy_date': datetime.now().strftime('%Y-%m-%d')
            }
    
    def remove_position(self, stock_code: str, quantity: int):
        """
        减少持仓
        """
        if stock_code in self.positions:
            pos = self.positions[stock_code]
            pos['quantity'] -= quantity
            
            if pos['quantity'] <= 0:
                del self.positions[stock_code]
    
    def get_positions(self) -> dict:
        """
        获取所有持仓
        """
        return self.positions
    
    def load_positions(self, file_path: str = None):
        """从文件加载持仓"""
        if file_path is None:
            base_dir = Path(__file__).parent.parent
            file_path = base_dir / "data" / "positions.json"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.positions = json.load(f)
                return self.positions
        except Exception as e:
            self.logger.warning(f"加载持仓失败: {e}")
            return {}
    
    def save_positions(self, file_path: str = None):
        """保存持仓到文件"""
        if file_path is None:
            base_dir = Path(__file__).parent.parent
            file_path = base_dir / "data" / "positions.json"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.positions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存持仓失败: {e}")
    
    def generate_risk_report(self) -> str:
        """
        生成风险报告
        """
        report_lines = []
        report_lines.append("=" * 40)
        report_lines.append("🛡️ 风险控制报告")
        report_lines.append("=" * 40)
        
        # 账户信息
        total_value = self.get_total_value()
        available = self.get_available_balance()
        position_ratio = total_value / self.account_balance if self.account_balance > 0 else 0
        
        report_lines.append(f"\n💰 账户概况:")
        report_lines.append(f"  总资金: {self.account_balance:.2f}")
        report_lines.append(f"  持仓市值: {total_value:.2f}")
        report_lines.append(f"  可用资金: {available:.2f}")
        report_lines.append(f"  仓位比例: {position_ratio:.1%}")
        
        # 持仓详情
        if self.positions:
            report_lines.append(f"\n📊 持仓明细:")
            
            for code, pos in self.positions.items():
                current_price = pos.get('current_price', pos['avg_price'])
                cost = pos['avg_price']
                profit_ratio = (current_price - cost) / cost if cost > 0 else 0
                
                report_lines.append(f"  {code}:")
                report_lines.append(f"    数量: {pos['quantity']}")
                report_lines.append(f"    成本: {cost:.2f}")
                report_lines.append(f"    当前: {current_price:.2f}")
                report_lines.append(f"    盈亏: {profit_ratio:.1%}")
                
                # 检查止损止盈
                stop_loss, _ = self.check_stop_loss(code, current_price)
                take_profit, _ = self.check_take_profit(code, current_price)
                
                if stop_loss:
                    report_lines.append(f"    ⚠️ 触发止损!")
                if take_profit:
                    report_lines.append(f"    🎯 触发止盈!")
        else:
            report_lines.append("\n📊 当前无持仓")
        
        # 风险提示
        report_lines.append(f"\n⚠️ 风险限制:")
        report_lines.append(f"  最大仓位: {int(self.max_position_ratio*100)}%")
        report_lines.append(f"  止损线: {int(self.stop_loss_ratio*100)}%")
        report_lines.append(f"  止盈线: {int(self.take_profit_ratio*100)}%")
        
        report_lines.append("\n" + "=" * 40)
        
        return "\n".join(report_lines)


# 测试代码
if __name__ == "__main__":
    risk = RiskController()
    
    # 测试交易时间检查
    print("交易时间:", risk.is_trading_hours())
    
    # 测试买入检查
    can_trade, messages = risk.should_trade("BUY", "002339", 10.5, 1000)
    print("\n买入检查:")
    for msg in messages:
        print(f"  {msg}")
    
    # 测试添加持仓
    risk.add_position("002339", 1000, 10.0)
    print("\n添加持仓后:", risk.get_positions())
    
    # 生成风险报告
    print(risk.generate_risk_report())

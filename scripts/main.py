#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票自动化盯盘交易系统 - 主程序
负责协调各模块完成每日任务和实时监控
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加scripts目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from logger import Logger
from price_fetcher import PriceFetcher
from trend_analyzer import TrendAnalyzer
from trade_executor import TradeExecutor
from risk_controller import RiskController
from notification import Notification


class TradingSystem:
    """交易系统主控类"""
    
    def __init__(self):
        """初始化系统"""
        self.logger = Logger.get_logger("trading_system")
        self.logger.info("=" * 50)
        self.logger.info("股票自动化盯盘交易系统启动")
        self.logger.info("=" * 50)
        
        # 初始化各模块
        self.price_fetcher = PriceFetcher()
        self.trend_analyzer = TrendAnalyzer()
        self.trade_executor = TradeExecutor()
        self.risk_controller = RiskController()
        self.notifier = Notification()
        
        # 交易记录
        self.trades = []
    
    def load_stocks(self) -> list:
        """加载自选股列表"""
        return self.price_fetcher.load_stocks()
    
    def daily_task(self):
        """
        每日收盘后任务
        1. 获取所有自选股价格
        2. 分析趋势和信号
        3. 生成报告并发送
        """
        self.logger.info("=" * 50)
        self.logger.info("开始执行每日任务")
        self.logger.info("=" * 50)
        
        # 1. 加载自选股
        stocks = self.load_stocks()
        if not stocks:
            self.logger.warning("自选股列表为空")
            return
        
        self.logger.info(f"加载了 {len(stocks)} 只自选股")
        
        # 2. 获取实时价格
        self.logger.info("正在获取股票价格...")
        prices = self.price_fetcher.fetch_all(stocks)
        
        # 保存价格数据
        self.price_fetcher.save_prices(prices)
        
        # 3. 分析每只股票
        analysis_results = []
        
        for stock_code, price_info in prices.items():
            if 'error' in price_info:
                self.logger.warning(f"股票{stock_code}价格获取失败")
                continue
            
            # 获取历史数据（使用akshare）
            current_price = price_info.get('price', 0)
            history_prices = self.trend_analyzer.get_history_with_current(
                stock_code, current_price, days=30
            )
            
            # 获取持仓信息
            position = self.risk_controller.get_positions().get(stock_code)
            
            # 更新持仓价格
            if position:
                self.risk_controller.update_position_price(stock_code, current_price)
            
            # 综合分析
            result = self.trend_analyzer.analyze_stock(price_info, history_prices, position)
            analysis_results.append(result)
            
            # 记录日志
            self.logger.info(f"分析 {result['stock_name']}({result['stock_code']}): "
                           f"趋势={result['trend']}, "
                           f"买入信号={result['buy_signal']['has_signal']}, "
                           f"卖出信号={result['sell_signal']['has_signal']}")
        
        # 4. 生成报告
        report = self.trend_analyzer.generate_report(analysis_results)
        
        # 5. 发送通知
        if self.notifier.enable_daily_report:
            self.notifier.send_daily_report(report)
        
        self.logger.info("每日任务执行完成")
        print(report)
    
    def realtime_monitor(self, interval: int = 15):
        """
        实时监控任务（只在交易时段执行）
        interval: 检查间隔（分钟）
        """
        from datetime import time as dt_time
        import akshare as ak
        
        # 交易时段
        MORNING_START = dt_time(9, 30)
        MORNING_END = dt_time(11, 30)
        AFTERNOON_START = dt_time(13, 0)
        AFTERNOON_END = dt_time(15, 0)
        
        def is_trading_day():
            """检查是否为A股交易日"""
            import pandas as pd
            try:
                # 使用akshare获取交易日历
                df = ak.tool_trade_date_hist_sina()
                # 转换日期列
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                today = datetime.now().strftime('%Y-%m-%d')
                # 判断今天是否在交易日列表中
                trading_days = df['trade_date'].dt.strftime('%Y-%m-%d').tolist()
                return today in trading_days
            except Exception as e:
                # 如果获取失败，默认不是交易日（保守）
                self.logger.warning(f"获取交易日历失败: {e}，默认认为今天非交易日")
                return False
        
        def is_trading_hours():
            """检查是否在交易时段"""
            now = datetime.now()
            
            # 先检查是否为交易日
            if not is_trading_day():
                return False
            
            current_time = now.time()
            
            # 上午时段
            if MORNING_START <= current_time <= MORNING_END:
                return True
            # 下午时段
            if AFTERNOON_START <= current_time <= AFTERNOON_END:
                return True
            
            return False
        
        self.logger.info("=" * 50)
        self.logger.info(f"开始实时监控 (间隔 {interval} 分钟)")
        self.logger.info("交易时段: 9:30-11:30, 13:00-15:00")
        self.logger.info("仅在A股交易日执行")
        self.logger.info("=" * 50)
        
        stocks = self.load_stocks()
        if not stocks:
            self.logger.warning("自选股列表为空")
            return
        
        # 持续监控
        try:
            while True:
                now = datetime.now()
                
                # 检查是否在交易时段
                if is_trading_hours():
                    self.logger.info(f"\n[{now.strftime('%H:%M:%S')}] 🔍 检查信号...")
                    
                    # 获取最新价格
                    prices = self.price_fetcher.fetch_all(stocks)
                    
                    alerts = []
                    
                    for stock_code, price_info in prices.items():
                        if 'error' in price_info:
                            continue
                        
                        # 获取持仓
                        position = self.risk_controller.get_positions().get(stock_code)
                        current_price = price_info.get('price', 0)
                        
                        # 更新持仓价格
                        if position:
                            self.risk_controller.update_position_price(stock_code, current_price)
                            
                            # 检查卖出信号
                            sell_signal = self.trend_analyzer.check_sell_signal(price_info, position)
                            
                            if sell_signal['has_signal']:
                                self.logger.warning(f"股票{stock_code}触发卖出信号: {sell_signal['signals']}")
                                
                                # 自动卖出
                                result = self.trade_executor.execute_sell(
                                    stock_code, 
                                    price_info.get('name', ''),
                                    current_price,
                                    position.get('quantity', 0)
                                )
                                
                                # 通知卖出
                                if result.get('success'):
                                    self.notifier.send_trade_result(result)
                                
                                alerts.append({
                                    'code': stock_code,
                                    'name': price_info.get('name', ''),
                                    'price': current_price,
                                    'type': 'SELL',
                                    'reason': ', '.join(sell_signal['signals'])
                                })
                        
                        # 检查买入信号（针对观察列表）
                        else:
                            # 获取历史数据
                            history_prices = self.trend_analyzer.get_history_with_current(
                                stock_code, current_price, days=30
                            )
                            
                            buy_signal = self.trend_analyzer.check_buy_signal(price_info, history_prices)
                            
                            if buy_signal['has_signal']:
                                self.logger.info(f"✅ 股票{stock_code}触发买入信号: {buy_signal['signals']}")
                                
                                # 自动买入（不等待确认）
                                quantity = 1000  # 默认买1000股，可配置
                                result = self.trade_executor.execute_buy(
                                    stock_code,
                                    price_info.get('name', ''),
                                    current_price,
                                    quantity,
                                    auto_confirm=True  # 自动确认
                                )
                                
                                # 通知买入
                                if result.get('success'):
                                    self.notifier.send_trade_result(result)
                                
                                alerts.append({
                                    'code': stock_code,
                                    'name': price_info.get('name', ''),
                                    'price': current_price,
                                    'type': 'BUY',
                                    'reason': ', '.join(buy_signal['signals'])
                                })
                    
                    # 发送告警汇总
                    if alerts and self.notifier.enable_realtime_alert:
                        self.notifier.send_alert(alerts)
                else:
                    # 非交易时段
                    if is_trading_day():
                        self.logger.info(f"[{now.strftime('%H:%M:%S')}] 💤 非交易时段，跳过检查")
                    else:
                        self.logger.info(f"[{now.strftime('%H:%M:%S')}] 🎉 节假日，不执行")
                
                # 等待下一次检查
                self.logger.info(f"等待 {interval} 分钟...")
                time.sleep(interval * 60)
                
        except KeyboardInterrupt:
            self.logger.info("实时监控已停止")
    
    def execute_trade(self, trade_signal: dict) -> dict:
        """
        执行交易（需人工确认）
        trade_signal: 包含 type, stock_code, stock_name, price, quantity
        """
        trade_type = trade_signal.get('type', 'BUY')
        stock_code = trade_signal.get('stock_code')
        stock_name = trade_signal.get('stock_name')
        price = trade_signal.get('price')
        quantity = trade_signal.get('quantity')
        
        # 1. 安全检查
        can_trade, messages = self.risk_controller.should_trade(
            trade_type, stock_code, price, quantity
        )
        
        if not can_trade:
            self.logger.warning(f"交易安全检查未通过: {messages}")
            for msg in messages:
                self.logger.warning(f"  {msg}")
            return {'success': False, 'error': '安全检查未通过', 'messages': messages}
        
        # 2. 发送人工确认请求
        self.notifier.send_trade_confirmation(trade_signal)
        
        # 3. 等待确认（这里简化处理，实际应该等待用户响应）
        # 在实际实现中，可以使用消息队列或Web接口等待用户确认
        confirmed = True  # 简化：直接确认
        
        if not confirmed:
            self.logger.info("用户取消交易")
            return {'success': False, 'error': '用户取消'}
        
        # 4. 执行交易
        if trade_type == "BUY":
            result = self.trade_executor.execute_buy(stock_code, stock_name, price, quantity)
            
            if result.get('success'):
                # 更新持仓
                self.risk_controller.add_position(stock_code, quantity, price)
        else:
            position = self.risk_controller.get_positions().get(stock_code)
            cost = position.get('avg_price', 0) if position else 0
            
            result = self.trade_executor.execute_sell(stock_code, stock_name, price, quantity, cost)
            
            if result.get('success'):
                # 更新持仓
                self.risk_controller.remove_position(stock_code, quantity)
        
        # 5. 记录交易
        if result.get('success'):
            self.trades.append(result)
            self.trade_executor.save_trades(self.trades)
            self.logger.log_trade(result)
        
        # 6. 发送交易结果
        self.notifier.send_trade_result(result)
        
        return result
    
    def show_positions(self):
        """显示当前持仓"""
        positions = self.risk_controller.get_positions()
        
        if not positions:
            print("\n当前无持仓")
            return
        
        print("\n" + "=" * 40)
        print("📊 当前持仓")
        print("=" * 40)
        
        for code, pos in positions.items():
            current_price = pos.get('current_price', pos['avg_price'])
            cost = pos['avg_price']
            profit_ratio = (current_price - cost) / cost if cost > 0 else 0
            
            print(f"\n{code}:")
            print(f"  数量: {pos['quantity']}")
            print(f"  成本: {cost:.2f}")
            print(f"  当前: {current_price:.2f}")
            print(f"  盈亏: {profit_ratio:+.2%}")
            print(f"  持仓天数: {pos.get('holding_days', 0)}")
    
    def show_status(self):
        """显示系统状态"""
        print("\n" + "=" * 50)
        print("📈 股票自动化盯盘交易系统")
        print("=" * 50)
        
        # 加载股票信息
        stocks = self.load_stocks()
        print(f"\n自选股数量: {len(stocks)}")
        
        for stock in stocks:
            print(f"  - {stock.get('name')}({stock.get('code')}) - {stock.get('industry')}")
        
        # 显示持仓
        self.show_positions()
        
        # 显示风险报告
        print("\n" + self.risk_controller.generate_risk_report())


def main():
    """主函数"""
    system = TradingSystem()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == '--daily-report' or command == '-d':
            # 每日报告任务
            system.daily_task()
        
        elif command == '--realtime-monitor' or command == '-r':
            # 实时监控任务
            interval = 30  # 默认30分钟
            if len(sys.argv) > 2:
                try:
                    interval = int(sys.argv[2])
                except ValueError:
                    pass
            system.realtime_monitor(interval)
        
        elif command == '--status' or command == '-s':
            # 显示状态
            system.show_status()
        
        elif command == '--fetch':
            # 使用同花顺查询股价
            stock_code = None
            for i, arg in enumerate(sys.argv):
                if arg.startswith('--code='):
                    stock_code = arg.split('=')[1]
                    break
            
            if stock_code:
                price = system.price_fetcher.fetch_price(stock_code)
                if price:
                    print(f"\n{'=' * 40}")
                    print(f"查询结果 (数据来源: {price.get('source', '未知')})")
                    print(f"{'=' * 40}")
                    print(f"股票代码: {price.get('code', stock_code)}")
                    print(f"股票名称: {price.get('name', '未知')}")
                    print(f"当前价格: ¥{price.get('price', 0):.2f}")
                    print(f"涨跌: {price.get('change', 0):+.2f}")
                    print(f"涨跌幅: {price.get('change_pct', 0):+.2f}%")
                    print(f"更新时间: {price.get('timestamp', '')}")
                else:
                    print("查询失败，未能获取到价格数据")
            else:
                print("请指定股票代码，例如: python main.py --fetch --code=002237")
        
        elif command == '--fetch-all':
            # 批量查询所有自选股
            stocks = system.load_stocks()
            if not stocks:
                print("自选股列表为空")
            else:
                print(f"开始批量查询 {len(stocks)} 只股票...")
                results = system.price_fetcher.fetch_all(stocks)
                
                print(f"\n{'=' * 60}")
                print("批量查询结果")
                print(f"{'=' * 60}")
                
                for code, info in results.items():
                    if 'error' in info:
                        print(f"{code}: 查询失败")
                    else:
                        print(f"{info.get('name', code)}({code}): ¥{info.get('price', 0):.2f} "
                              f"{info.get('change_pct', 0):+.2f}%")
                
                print(f"\n共查询 {len(results)} 只股票")
        
        elif command == '--execute-trade':
            # 执行交易（测试用）
            trade_signal = {
                'type': 'BUY',
                'stock_code': '002339',
                'stock_name': '积成电子',
                'price': 10.50,
                'quantity': 1000
            }
            result = system.execute_trade(trade_signal)
            print("\n交易结果:", result)
        
        else:
            print(f"未知命令: {command}")
            print_help()
    
    else:
        # 默认显示状态
        system.show_status()


def print_help():
    """打印帮助信息"""
    print("\n用法:")
    print("  python main.py [选项]")
    print("\n选项:")
    print("  -d, --daily-report      执行每日报告任务")
    print("  -r, --realtime-monitor [分钟]  执行实时监控")
    print("  -s, --status           显示系统状态")
    print("  --fetch --code=CODE     使用同花顺查询单只股票价格")
    print("  --fetch-all             批量查询所有自选股价格")
    print("  --execute-trade         执行测试交易")
    print("  -h, --help              显示帮助信息")


if __name__ == "__main__":
    if len(sys.argv) > 1 and (sys.argv[1] == '-h' or sys.argv[1] == '--help'):
        print_help()
    else:
        main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票自动化盯盘交易系统 - 主程序
负责协调各模块完成每日任务和实时监控
"""

import json
import sys
import time
import requests
from datetime import datetime
from pathlib import Path

# 添加scripts目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from logger import Logger
from price_fetcher import PriceFetcher

# 飞书Webhook地址
FEISHU_WEBHOOK = 'https://www.feishu.cn/flow/api/trigger-webhook/3c8f0cee02e74bbfd2206ebadb44c27d'

# 拦截print函数，同时发送飞书
_original_print = print
def print_with_notify(*args, **kwargs):
    text = ' '.join(str(arg) for arg in args)
    _original_print(*args, **kwargs)
    # 发送到飞书
    if text and len(text) > 2:
        try:
            requests.post(FEISHU_WEBHOOK, json={'msg_type': 'text', 'content': {'text': text}}, timeout=5)
        except:
            pass

import builtins
builtins.print = print_with_notify

# 拦截Logger
import logging
_logger_send_feishu = logging.getLogger().info
def log_to_feishu(msg, *args, **kwargs):
    _logger_send_feishu(msg, *args, **kwargs)
    text = str(msg) % args if args else str(msg)
    if text and len(text) > 2:
        try:
            requests.post(FEISHU_WEBHOOK, json={'msg_type': 'text', 'content': {'text': text}}, timeout=5)
        except:
            pass

# 不替换Logger，避免崩溃
from trend_analyzer import TrendAnalyzer


# 飞书Webhook
FEISHU_WEBHOOK = 'https://www.feishu.cn/flow/api/trigger-webhook/3c8f0cee02e74bbfd2206ebadb44c27d'


def send_feishu(text):
    try:
        requests.post(FEISHU_WEBHOOK, json={'msg_type': 'text', 'content': {'text': text}}, timeout=10)
    except:
        pass
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
    
    def load_position_stocks(self) -> list:
        """加载持仓股票列表"""
        positions = self.risk_controller.get_positions()
        stocks = []
        for code, pos in positions.items():
            # 获取股票名称
            name = pos.get('name', '')
            if not name:
                # 通过API获取名称
                try:
                    import requests
                    market = '1' if code.startswith('6') else '0'
                    url = 'https://push2.eastmoney.com/api/qt/stock/get'
                    params = {'fields': 'f58', 'secid': f'{market}.{code}'}
                    resp = requests.get(url, params=params, timeout=3)
                    name = resp.json().get('data', {}).get('f58', code)
                except:
                    name = code
            
            stocks.append({
                'code': code,
                'name': name
            })
        return stocks
    
    def _save_watch_list(self, stocks: list):
        """保存观察列表（自动剔除机制）"""
        import json
        from pathlib import Path
        from datetime import datetime, timedelta
        
        # 读取现有数据
        stocks_file = Path(__file__).parent.parent / "stocks.json"
        if stocks_file.exists():
            with open(stocks_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"watchlist": []}
        
        # ===== 自动剔除：观察超过5天且未买入的股票 =====
        today = datetime.now()
        max_observed_days = 5  # 最多观察5天
        removed_count = 0
        
        original_count = len(data.get('watchlist', []))
        data['watchlist'] = [
            s for s in data.get('watchlist', [])
            if s.get('status') == '已买入' or  # 保留已买入的
            (today - datetime.strptime(s.get('added_date', '2020-01-01'), '%Y-%m-%d')).days <= max_observed_days  # 保留5天内的
        ]
        removed_count = original_count - len(data['watchlist'])
        
        if removed_count > 0:
            self.logger.info(f"  🗑️ 自动剔除 {removed_count} 只观察超过{max_observed_days}天的股票")
        
        # ===== 添加新股票 =====
        existing_codes = {s['code'] for s in data.get('watchlist', [])}
        
        for stock in stocks:
            code = stock.get('code', '')

            # 限制观察列表最多15只（剔除后如果超限，再剔除最老的）
            if len(data['watchlist']) >= 15:
                # 按加入日期排序，移除最老的
                data['watchlist'].sort(key=lambda x: x.get('added_date', '2020-01-01'))
                removed = data['watchlist'].pop(0)
                self.logger.info(f"  🗑️ 观察列表已满，剔除最老股票: {removed.get('name')}")
            
            if code and code not in existing_codes:
                data['watchlist'].append({
                    'code': code,
                    'name': stock.get('name', ''),
                    'industry': stock.get('industry', ''),
                    'added_date': today.strftime('%Y-%m-%d'),
                    'status': '观察',
                    'notes': f"入选原因：{stock.get('reason', '系统选股')}"
                })
        
        # 保存
        with open(stocks_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"  ✅ 观察列表已更新，共 {len(data['watchlist'])} 只")
    
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
            self.logger.warning("自选股列表为空，跳过本次检查")
            # 不退出，等待下次检查
        
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
        
        def get_time_period():
            """获取当前时间段
            
            Returns:
                str: 盘前/上午/午间/下午/盘后/夜间
            """
            now = datetime.now()
            if not is_trading_day():
                return "非交易日"
            
            current_time = now.time()
            
            if current_time < MORNING_START:
                return "盘前"  # 9:30前
            elif MORNING_START <= current_time <= MORNING_END:
                return "上午"  # 9:30-11:30
            elif MORNING_END < current_time < AFTERNOON_START:
                return "午间"  # 11:30-13:00
            elif AFTERNOON_START <= current_time <= AFTERNOON_END:
                return "下午"  # 13:00-15:00
            elif current_time > AFTERNOON_END:
                return "盘后"  # 15:00后
            else:
                return "其他"
                return True
            
            return False
        
        self.logger.info("=" * 50)
        self.logger.info(f"开始实时监控 (间隔 {interval} 分钟)")
        self.logger.info("交易时段: 9:30-11:30, 13:00-15:00")
        self.logger.info("仅在A股交易日执行")
        self.logger.info("=" * 50)
        
        stocks = self.load_stocks()
        if not stocks:
            self.logger.warning("自选股列表为空，跳过本次检查")
            # 不退出，等待下次检查
        
        # 记录上次发送提醒的时间
        import time
        last_alert_time = time.time()
        last_summary_time = time.time()  # 上次发送总结的时间
        
        # 持续监控
        try:
            while True:
                now = datetime.now()
                
                # 检查是否在交易时段
                if is_trading_hours():
                    # 检查自选股是否为空
                    stocks = self.load_stocks()
                    if not stocks:
                        self.logger.warning("自选股列表为空，跳过本次检查")
                        time.sleep(interval * 60)
                        continue
                    
                    self.logger.info(f"\n[{now.strftime('%H:%M:%S')}] 🔍 检查信号...")
                    
                    # 获取最新价格
                    prices = self.price_fetcher.fetch_all(stocks)
                    
                    # 记录所有自选股价格到Excel
                    self.logger.info("📊 记录股价到Excel...")
                    # from price_logger import PriceLogger
                    # price_logger = PriceLogger()
                    for stock_code, price_info in prices.items():
                        if price_info and 'error' not in price_info:
                            try:
                                # price_logger.log_price(price_info, "定时监控")
                                self.logger.info(f"  ✅ {price_info.get('name')}: ¥{price_info.get('price')}")
                            except Exception as e:
                                self.logger.warning(f"  ❌ 记录失败: {e}")
                    
                    # 记录持仓股票价格（额外记录）
                    position_stocks = self.load_position_stocks()
                    for pos_stock in position_stocks:
                        try:
                            pos_price = self.price_fetcher.fetch_price(pos_stock['code'])
                            if pos_price:
                                # 加入prices字典，用于后续信号检测
                                prices[pos_stock['code']] = pos_price
                                self.logger.info(f"  📦 持仓: {pos_price.get('name')}: ¥{pos_price.get('price')}")
                        except Exception as e:
                            self.logger.warning(f"  ❌ 持仓记录失败: {e}")
                    
                    alerts = []
                    failed_stocks = []  # 获取价格失败的股票
                    
                    for stock_code, price_info in prices.items():
                        if price_info is None or 'error' in price_info:
                            # 获取价格失败，记录并通知
                            stock_name = next((s.get('name', '') for s in stocks if s.get('code') == stock_code), stock_code)
                            failed_stocks.append(f"{stock_name}({stock_code})")
                            continue
                        
                        # 获取持仓
                        position = self.risk_controller.get_positions().get(stock_code)
                        current_price = price_info.get('price', 0)
                        
                        # 更新持仓价格
                        if position:
                            self.risk_controller.update_position_price(stock_code, current_price)
                            
                            # 获取历史数据用于技术指标计算
                            history_prices = self.trend_analyzer.get_history_with_current(
                                stock_code, current_price, days=30
                            )
                            price_list = [p['close'] for p in history_prices] if history_prices else []
                            
                            # 检查卖出信号（带历史数据）
                            sell_signal = self.trend_analyzer.check_sell_signal(
                                price_info, price_list, position
                            )
                            
                            if sell_signal['has_signal']:
                                self.logger.warning(f"股票{stock_code}触发卖出信号: {sell_signal['signals']}")
                                
                                # 判断卖出数量
                                total_qty = position.get('quantity', 0)
                                
                                # 检查是否是"达到10%止盈"信号
                                is_takeprofit = any("止盈" in s for s in sell_signal['signals'])
                                
                                if is_takeprofit and total_qty > 200:
                                    # 止盈信号：卖一半，留一半
                                    sell_qty = total_qty // 2
                                    self.logger.info(f"💰 止盈信号，卖出数量: {sell_qty} (持仓剩余: {total_qty - sell_qty})")
                                else:
                                    # 其他信号（止损/死叉等）：全卖
                                    sell_qty = total_qty
                                    self.logger.info(f"🛡️ 止损/破位信号，全量卖出: {sell_qty}")
                                
                                # 自动卖出
                                result = self.trade_executor.execute_sell(
                                    stock_code, 
                                    price_info.get('name', ''),
                                    current_price,
                                    sell_qty
                                )
                                
                                # 通知卖出
                                if result.get('success'):
                                    # 更新持仓
                                    self.risk_controller.remove_position(stock_code, sell_qty)
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
                                    # 更新持仓
                                    self.risk_controller.add_position(stock_code, quantity, current_price)
                                    self.notifier.send_trade_result(result)
                                
                                alerts.append({
                                    'code': stock_code,
                                    'name': price_info.get('name', ''),
                                    'price': current_price,
                                    'type': 'BUY',
                                    'reason': ', '.join(buy_signal['signals'])
                                })
                    
                    # 发送告警汇总（买卖信号时立即发送）
                    if alerts:
                        self.logger.info(f"📢 发现买卖信号，发送提醒...")
                        if self.notifier.enable_realtime_alert:
                            self.notifier.send_alert(alerts)
                        last_alert_time = time.time()
                    
                    # 发送价格获取失败通知
                    if failed_stocks:
                        self.logger.warning(f"⚠️ 以下股票获取价格失败: {', '.join(failed_stocks)}")
                        if self.notifier.enable_realtime_alert:
                            self.notifier.send_alert([{
                                'code': 'SYSTEM',
                                'name': '系统',
                                'price': 0,
                                'type': 'ERROR',
                                'reason': f"获取价格失败: {', '.join(failed_stocks)}"
                            }])
                    
                    # 每小时发送一次总结
                    current_time = time.time()
                    if current_time - last_summary_time >= 3600:  # 1小时
                        self.logger.info("📢 发送定时总结...")
                        if self.notifier.enable_realtime_alert:
                            # 发送持仓总结
                            summary = self._generate_summary(prices)
                            self.notifier.send_alert(summary)
                        last_summary_time = current_time
                    
                    # ===== 每日18点执行多因子选股 =====
                    now = datetime.now()
                    current_hour = now.hour
                    current_minute = now.minute
                    
                    # 检查是否18:00-18:05（执行窗口）
                    if current_hour == 18 and current_minute < 5:
                        # 记录今天是否已执行过选股
                        today_str = now.strftime('%Y-%m-%d')
                        last_select_date = getattr(self, '_last_select_date', '')
                        
                        if last_select_date != today_str:
                            self.logger.info("⏰ 执行每日多因子选股...")
                            try:
                                from multi_factor_selector import MultiFactorSelector
                                selector = MultiFactorSelector()
                                
                                selected = selector.select_by_factors(
                                    min_score=0.6,
                                    max_stocks=10,
                                    exclude_st=True,
                                    exclude_new=True
                                )
                                
                                self.logger.info(f"  📋 多因子筛选出 {len(selected)} 只股票")
                                
                                if selected:
                                    self._save_watch_list(selected)
                                    self.logger.info(f"  ✅ 观察列表已更新")
                                
                                # 记录今天已执行
                                self._last_select_date = today_str
                            except Exception as e:
                                self.logger.warning(f"  ❌ 选股失败: {e}")
                        last_summary_time = time.time()
                else:
                    # 非交易时段 - 静默等待，减少日志输出
                    if not getattr(self, '_non_trading_warning_shown', False):
                        self.logger.info("⏰ 当前非交易时段，10分钟后再次检查...")
                        self._non_trading_warning_shown = True
                
                # 等待下一次检查
                if not is_trading_hours():
                    # 非交易时段，减少等待频率（30分钟检查一次）
                    sleep_interval = 30
                else:
                    sleep_interval = interval
                    
                self.logger.info(f"等待 {sleep_interval} 分钟...")
                time.sleep(sleep_interval * 60)
                
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
    
    def _run_pre_market_tasks(self, stocks: list):
        """盘前任务
        
        - 股价更新（获取最新收盘价/开盘价）
        - 记录到Excel（强制获取）
        """
        self.logger.info("📊 执行盘前任务: 更新股价数据")
        
        # 盘前时段强制获取价格
        for stock in stocks:
            stock_code = stock.get('code')
            try:
                price_info = self.price_fetcher.fetch_price(stock_code, force=True)
                if price_info:
                    self.logger.info(f"  ✅ {price_info.get('name')}: ¥{price_info.get('price')}")
            except Exception as e:
                self.logger.warning(f"  ❌ 获取{stock_code}价格失败: {e}")
    
    def _generate_summary(self, prices: dict) -> list:
        """生成定时总结"""
        alerts = []
        positions = self.risk_controller.get_positions()
        
        for code, pos in positions.items():
            price_info = prices.get(code)
            if not price_info:
                continue
            
            current_price = price_info.get('price', 0)
            cost = pos.get('avg_price', 0)
            if current_price > 0 and cost > 0:
                profit_pct = (current_price - cost) / cost * 100
                alerts.append({
                    'code': code,
                    'name': price_info.get('name', code),
                    'price': current_price,
                    'type': '持仓',
                    'reason': f'成本:{cost:.2f} 盈亏:{profit_pct:+.1f}%'
                })
        
        return alerts
    
    def _run_lunch_tasks(self, stocks: list):
        """午间任务
        
        - 午间选股
        - 持仓检查
        """
        self.logger.info("📊 执行午间任务")
        
        # 可以在这里添加午间选股逻辑
        self.logger.info("  💤 午间休息中，可手动执行选股")
    
    def _run_after_market_tasks(self, stocks: list):
        """盘后任务
        
        - 执行全市场选股
        - 生成每日报告
        - 更新股价记录（强制获取收盘价）
        """
        self.logger.info("📊 执行盘后任务: 选股 & 生成报告")
        
        # 盘后时段强制获取价格（不跳过）
        self.logger.info("  📈 获取收盘价...")
        for stock in stocks:
            stock_code = stock.get('code')
            try:
                # 强制获取价格（force=True 忽略交易时段判断）
                price_info = self.price_fetcher.fetch_price(stock_code, force=True)
                if price_info:
                    self.logger.info(f"  ✅ {price_info.get('name')}: ¥{price_info.get('price')} (收盘)")
            except Exception as e:
                self.logger.warning(f"  ❌ 获取{stock_code}价格失败: {e}")
        
        self.logger.info("  📝 股价数据已记录到Excel")
        
        # 执行全市场选股（多因子选股）
        self.logger.info("  🔍 执行多因子选股...")
        try:
            from multi_factor_selector import MultiFactorSelector
            selector = MultiFactorSelector()
            
            # 多因子综合选股
            selected = selector.select_by_factors(
                min_score=0.6,    # 最低评分0.6
                max_stocks=10,    # 最多10只
                exclude_st=True,   # 排除ST股
                exclude_new=True   # 排除次新股
            )
            
            self.logger.info(f"  📋 多因子筛选出 {len(selected)} 只股票")
            
            # 保存到观察列表
            if selected:
                self._save_watch_list(selected)
                self.logger.info(f"  ✅ 已保存到观察列表")
        except Exception as e:
            self.logger.warning(f"  ❌ 多因子选股失败: {e}")
            # 备用：简单条件筛选
            try:
                from stock_selector import StockSelector
                selector = StockSelector()
                selected = selector.select_by_criteria({
                    'min_turnover': 3.0,
                    'change_pct_range': (-3, 3),
                    'min_price': 5,
                    'max_price': 100
                })
                if selected:
                    self._save_watch_list(selected)
                    self.logger.info(f"  📋 备用筛选出 {len(selected)} 只股票")
            except Exception as e2:
                self.logger.warning(f"  ❌ 备用选股也失败: {e2}")
    
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
    # 使用print发送启动通知，显示资金和仓位
    from trade_executor import TradeExecutor
    executor = TradeExecutor()
    positions = executor.get_all_positions()
    position_count = len(positions)
    total_value = executor.get_position_value()
    available = executor.get_available_capital()
    position_ratio = (total_value / executor.capital * 100) if executor.capital > 0 else 0
    
    # 加载关注列表
    import json
    with open(Path(__file__).parent.parent / "stocks.json", 'r', encoding='utf-8') as f:
        watchlist = len(json.load(f).get('watchlist', []))
    
    print(f"📈 股票自动化交易系统已启动！\n\n⏰ 监控间隔: 5分钟\n💰 总资金: ¥{executor.capital:,.0f}\n📦 持仓: {position_count}只\n👀 关注: {watchlist}只")
    
    system = TradingSystem()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == '--daily-report' or command == '-d':
            # 每日报告任务
            system.daily_task()
        
        elif command == '--realtime-monitor' or command == '-r':
            # 实时监控任务
            interval = 15  # 默认15分钟
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
        
        elif command == '--select-stocks':
            # 执行多因子选股
            print("\n🔍 执行多因子选股...")
            from multi_factor_selector import MultiFactorSelector
            selector = MultiFactorSelector()
            selected = selector.select_by_factors(
                min_score=0.6,
                max_stocks=10,
                exclude_st=True,
                exclude_new=True
            )
            print(f"\n📋 选出 {len(selected)} 只股票:")
            for s in selected:
                score = s.get('composite_score') or s.get('score', 0)
                print(f"  - {s.get('name')}({s.get('code')}): {s.get('industry', '未知')} - 评分:{score:.2f} - 现价:¥{s.get('price', 0):.2f} - 涨幅:{s.get('change_pct', 0):+.2f}%")
            
            # 保存到观察列表
            system._save_watch_list(selected)
            print(f"\n✅ 已保存到观察列表")
        
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

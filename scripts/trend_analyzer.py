#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势分析模块
负责计算技术指标、判断趋势方向、生成交易信号
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from config import config
from logger import Logger

# 尝试导入akshare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("⚠️ akshare未安装，将使用模拟数据")


class TrendAnalyzer:
    """趋势分析类"""
    
    def __init__(self):
        self.logger = Logger.get_logger("trend_analyzer")
        
        # 策略配置
        strategy_config = config.get_strategy_config()
        self.ma_periods = strategy_config.get('ma_periods', [5, 10, 20])
        self.buy_conditions = strategy_config.get('buy_conditions', {})
        self.sell_conditions = config.get('trading.sell_conditions', {})
        
        # 交易配置
        trading_config = config.get_trading_config()
        self.stop_loss_ratio = trading_config.get('stop_loss_ratio', 0.05)
        self.take_profit_ratio = trading_config.get('take_profit_ratio', 0.10)
        self.max_holding_days = trading_config.get('max_holding_days', 12)
        
        # 历史数据缓存
        self.history_cache = {}
    
    def get_stock_code_with_market(self, stock_code: str) -> tuple:
        """
        获取带市场的股票代码
        返回: (市场代码, 完整代码)
        上海: sh6xxxxxx
        深圳: sz0xxxxxx / sz3xxxxxx
        """
        if stock_code.startswith('6'):
            return "sh", f"sh{stock_code}"
        else:
            return "sz", f"sz{stock_code}"
    
    def fetch_history_data(self, stock_code: str, days: int = 30) -> list:
        """
        获取历史收盘价数据
        使用akshare获取
        """
        # 检查缓存
        cache_key = f"{stock_code}_{days}"
        if cache_key in self.history_cache:
            cached_time, cached_data = self.history_cache[cache_key]
            # 缓存5分钟内有效
            if (datetime.now() - cached_time).seconds < 300:
                self.logger.info(f"使用缓存的历史数据: {stock_code}")
                return cached_data
        
        if not AKSHARE_AVAILABLE:
            self.logger.warning(f"akshare不可用，生成模拟数据: {stock_code}")
            return self._generate_mock_data(stock_code, days)
        
        try:
            market, full_code = self.get_stock_code_with_market(stock_code)
            
            self.logger.info(f"从akshare获取历史数据: {stock_code}")
            
            # 使用akshare获取日K数据
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                   start_date=(datetime.now() - timedelta(days=days+10)).strftime('%Y%m%d'),
                                   end_date=datetime.now().strftime('%Y%m%d'),
                                   adjust="qfq")
            
            if df is None or df.empty:
                self.logger.warning(f"无法获取{stock_code}的历史数据")
                return self._generate_mock_data(stock_code, days)
            
            # 提取收盘价
            close_prices = df['收盘'].tolist()
            
            # 按日期排序（从旧到新）
            close_prices = close_prices[-days:]
            
            # 缓存结果
            self.history_cache[cache_key] = (datetime.now(), close_prices)
            
            self.logger.info(f"成功获取{stock_code} {len(close_prices)}天历史数据")
            return close_prices
            
        except Exception as e:
            self.logger.error(f"获取{stock_code}历史数据失败: {e}")
            return self._generate_mock_data(stock_code, days)
    
    def _generate_mock_data(self, stock_code: str, days: int) -> list:
        """
        生成模拟历史数据（用于测试或无法获取数据时）
        """
        import random
        random.seed(hash(stock_code) % 10000)
        
        # 基础价格
        base_price = 10.0 + random.random() * 10
        
        prices = []
        for i in range(days):
            # 随机波动
            change = random.uniform(-0.03, 0.03)
            base_price = base_price * (1 + change)
            prices.append(round(base_price, 2))
        
        return prices
    
    def get_history_with_current(self, stock_code: str, current_price: float, days: int = 30) -> list:
        """
        获取完整的历史+当前价格数据
        用于MA计算
        """
        history = self.fetch_history_data(stock_code, days)
        
        if not history:
            return []
        
        # 追加当前价格到列表末尾（最新价格）
        full_prices = history + [current_price]
        
        return full_prices
    
    def calculate_ma(self, prices: list, period: int) -> float:
        """
        计算移动平均线
        prices: 价格列表，最新价格在最后
        """
        if len(prices) < period:
            return None
        
        return sum(prices[-period:]) / period
    
    def calculate_ma_all(self, prices: list) -> dict:
        """
        计算所有周期的MA
        """
        ma_values = {}
        
        for period in self.ma_periods:
            ma_values[f'ma{period}'] = self.calculate_ma(prices, period)
        
        return ma_values
    
    def calculate_volume_ratio(self, current_volume: float, avg_volume: float) -> float:
        """
        计算量比
        """
        if not avg_volume or avg_volume == 0:
            return 1.0
        return current_volume / avg_volume
    
    def get_trend_direction(self, price_info: dict, history_prices: list = None) -> str:
        """
        判断趋势方向
        返回: "上升趋势" / "下降趋势" / "震荡"
        """
        # 如果有历史数据，使用MA判断
        if history_prices and len(history_prices) >= 20:
            ma5 = self.calculate_ma(history_prices, 5)
            ma20 = self.calculate_ma(history_prices, 20)
            
            if ma5 and ma20:
                if ma5 > ma20 * 1.02:  # 2%以上视为明显上升
                    return "上升趋势"
                elif ma5 < ma20 * 0.98:  # 2%以上视为明显下降
                    return "下降趋势"
                else:
                    return "震荡"
        
        # 否则使用涨跌幅快速判断
        change_pct = price_info.get('change_pct', 0)
        
        if change_pct > 1:
            return "上升趋势"
        elif change_pct < -1:
            return "下降趋势"
        
        return "震荡"
    
    def check_buy_signal(self, price_info: dict, history_prices: list = None) -> dict:
        """
        检查买入信号
        返回: {"has_signal": bool, "signals": list, "confidence": int}
        """
        signals = []
        confidence = 0
        
        # 条件1: MA5 > MA10 > MA20 (多头排列)
        if history_prices and len(history_prices) >= 20:
            ma5 = self.calculate_ma(history_prices, 5)
            ma10 = self.calculate_ma(history_prices, 10)
            ma20 = self.calculate_ma(history_prices, 20)
            
            if ma5 and ma10 and ma20:
                if ma5 > ma10 > ma20:
                    signals.append("均线多头排列")
                    confidence += 30
        
        # 条件2: 当日跌幅 > 1%（提供足够安全边际）
        change_pct = price_info.get('change_pct', 0)
        if change_pct < -1.0:
            signals.append(f"当日跌幅{abs(change_pct):.2f}%")
            confidence += 20
        
        # 条件3: 收盘价 > MA5 (短期趋势未破)
        if history_prices and len(history_prices) >= 5:
            ma5 = self.calculate_ma(history_prices, 5)
            current_price = price_info.get('price', 0)
            if ma5 and current_price > ma5:
                signals.append("收盘价在MA5上方")
                confidence += 20
        
        # 条件4: 换手率合适
        turnover_rate = price_info.get('turnover_rate', 0)
        if turnover_rate >= 2.0:
            signals.append(f"换手率{turnover_rate:.2f}%")
            confidence += 15
        
        # 条件5: 振幅足够
        price = price_info.get('price', 0)
        high = price_info.get('high', 0)
        low = price_info.get('low', 0)
        if price and high and low:
            amplitude = (high - low) / price * 100
            if amplitude >= 3.0:
                signals.append(f"振幅{amplitude:.2f}%")
                confidence += 15
        
        has_signal = len(signals) >= 2 and confidence >= 40
        
        return {
            'has_signal': has_signal,
            'signals': signals,
            'confidence': confidence,
            'stock_code': price_info.get('code'),
            'stock_name': price_info.get('name')
        }
    
    def check_sell_signal(self, price_info: dict, position: dict = None) -> dict:
        """
        检查卖出信号
        返回: {"has_signal": bool, "signals": list, "reason": str}
        """
        signals = []
        
        # 条件1: 涨幅达到止盈线
        if position:
            cost = position.get('avg_price', 0)
            current_price = price_info.get('price', 0)
            
            if cost and current_price:
                profit_ratio = (current_price - cost) / cost
                
                if profit_ratio >= self.take_profit_ratio:
                    signals.append(f"达到{self.take_profit_ratio*100:.0f}%止盈线")
                
                # 条件2: 跌幅达到止损线
                if profit_ratio <= -self.stop_loss_ratio:
                    signals.append(f"触发{abs(self.stop_loss_ratio)*100:.0f}%止损线")
        
        # 条件3: 涨幅达到10%（硬止盈）
        change_pct = price_info.get('change_pct', 0)
        if change_pct >= 10.0:
            signals.append("达到10%止盈线")
        
        # 条件4: 持有超过最大天数
        if position:
            holding_days = position.get('holding_days', 0)
            if holding_days >= self.max_holding_days:
                signals.append(f"持有超过{self.max_holding_days}天")
        
        has_signal = len(signals) > 0
        
        return {
            'has_signal': has_signal,
            'signals': signals,
            'stock_code': price_info.get('code'),
            'stock_name': price_info.get('name')
        }
    
    def analyze_stock(self, price_info: dict, history_prices: list = None, position: dict = None) -> dict:
        """
        综合分析股票
        """
        trend = self.get_trend_direction(price_info, history_prices)
        buy_signal = self.check_buy_signal(price_info, history_prices)
        sell_signal = self.check_sell_signal(price_info, position)
        
        return {
            'stock_code': price_info.get('code'),
            'stock_name': price_info.get('name'),
            'current_price': price_info.get('price'),
            'change_pct': price_info.get('change_pct'),
            'trend': trend,
            'buy_signal': buy_signal,
            'sell_signal': sell_signal,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def generate_report(self, analysis_results: list) -> str:
        """
        生成分析报告
        """
        report_lines = []
        report_lines.append("=" * 50)
        report_lines.append(f"📊 股票分析报告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report_lines.append("=" * 50)
        
        # 统计
        total = len(analysis_results)
        buy_signals = sum(1 for r in analysis_results if r['buy_signal']['has_signal'])
        sell_signals = sum(1 for r in analysis_results if r['sell_signal']['has_signal'])
        uptrend = sum(1 for r in analysis_results if r['trend'] == '上升趋势')
        
        report_lines.append(f"\n📈 总体统计:")
        report_lines.append(f"  - 自选股数量: {total}")
        report_lines.append(f"  - 上升趋势: {uptrend}")
        report_lines.append(f"  - 买入信号: {buy_signals}")
        report_lines.append(f"  - 卖出信号: {sell_signals}")
        
        # 详细分析
        for result in analysis_results:
            report_lines.append(f"\n{'─' * 40}")
            code = result.get('stock_code', '')
            name = result.get('stock_name', '')
            price = result.get('current_price', 0)
            change = result.get('change_pct', 0)
            trend = result.get('trend', '未知')
            
            report_lines.append(f"📌 {name}({code})")
            report_lines.append(f"   价格: {price:.2f} ({change:+.2f}%)")
            report_lines.append(f"   趋势: {trend}")
            
            # 买入信号
            if result['buy_signal']['has_signal']:
                report_lines.append(f"   🟢 买入信号:")
                for sig in result['buy_signal']['signals']:
                    report_lines.append(f"      - {sig}")
                report_lines.append(f"   置信度: {result['buy_signal']['confidence']}%")
            
            # 卖出信号
            if result['sell_signal']['has_signal']:
                report_lines.append(f"   🔴 卖出信号:")
                for sig in result['sell_signal']['signals']:
                    report_lines.append(f"      - {sig}")
        
        report_lines.append("\n" + "=" * 50)
        
        return "\n".join(report_lines)


# 测试代码
if __name__ == "__main__":
    analyzer = TrendAnalyzer()
    
    # 模拟价格数据
    test_price = {
        'code': '002339',
        'name': '积成电子',
        'price': 10.50,
        'change_pct': -1.5,
        'high': 10.80,
        'low': 10.30,
        'turnover_rate': 3.5
    }
    
    # 模拟历史数据
    test_history = [10.0 + i * 0.05 for i in range(30)]
    
    # 测试买入信号
    buy_signal = analyzer.check_buy_signal(test_price, test_history)
    print("买入信号:", buy_signal)
    
    # 测试卖出信号
    position = {'avg_price': 10.0, 'holding_days': 5}
    sell_signal = analyzer.check_sell_signal(test_price, position)
    print("卖出信号:", sell_signal)
    
    # 综合分析
    result = analyzer.analyze_stock(test_price, test_history, position)
    print("\n综合分析:", json.dumps(result, ensure_ascii=False, indent=2))

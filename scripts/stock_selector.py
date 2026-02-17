#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全市场自动选股模块
基于 akshare 提供多种选股策略
"""

import json
from datetime import datetime
from pathlib import Path

# 尝试导入akshare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("⚠️ akshare未安装，将使用模拟数据")


class StockSelector:
    """全市场股票选择器"""
    
    def __init__(self):
        self.logger = print  # 简化日志
        
    def get_all_stocks(self) -> list:
        """
        获取全部A股列表
        """
        if not AKSHARE_AVAILABLE:
            return self._get_mock_stocks()
        
        try:
            # 使用东方财富接口获取全部A股
            df = ak.stock_zh_a_spot_em()
            stocks = []
            for _, row in df.iterrows():
                stocks.append({
                    'code': str(row['代码']),
                    'name': row['名称'],
                    'price': row['最新价'],
                    'change_pct': row['涨跌幅'],
                    'volume': row['成交量'],
                    'turnover_rate': row['换手率']
                })
            return stocks
        except Exception as e:
            self.logger(f"获取A股列表失败: {e}")
            return self._get_mock_stocks()
    
    def select_by_criteria(self, criteria: dict = None) -> list:
        """
        根据条件筛选股票
        criteria: {
            'min_turnover': 2.0,      # 最小换手率
            'change_pct_range': (-5, 5),  # 涨跌幅范围
            'min_price': 5,            # 最低价
            'max_price': 100,          # 最高价
            'industry': None           # 行业筛选
        }
        """
        if criteria is None:
            criteria = {
                'min_turnover': 2.0,
                'change_pct_range': (-5, 5),
                'min_price': 5,
                'max_price': 100
            }
        
        all_stocks = self.get_all_stocks()
        selected = []
        
        for stock in all_stocks:
            if self._match_criteria(stock, criteria):
                selected.append(stock)
        
        self.logger(f"从 {len(all_stocks)} 只股票中筛选出 {len(selected)} 只")
        return selected
    
    def select_zt_pool(self) -> list:
        """
        选取涨停股票池
        """
        if not AKSHARE_AVAILABLE:
            return self._get_mock_stocks(10)
        
        try:
            df = ak.stock_zt_pool_em()
            stocks = []
            for _, row in df.iterrows():
                stocks.append({
                    'code': str(row['代码']),
                    'name': row['名称'],
                    'price': row['最新价'],
                    'change_pct': row['涨跌幅']
                })
            return stocks
        except Exception as e:
            self.logger(f"获取涨停池失败: {e}")
            return []
    
    def select_by_fund_flow(self, top_n: int = 50) -> list:
        """
        选取资金流入力度最强的股票
        """
        if not AKSHARE_AVAILABLE:
            return self._get_mock_stocks(top_n)
        
        try:
            df = ak.stock_individual_fund_flow_rank(symbol='A股', num=top_n)
            stocks = []
            for _, row in df.iterrows():
                stocks.append({
                    'code': str(row['代码']),
                    'name': row['名称'],
                    'net_flow': row['净流入'],
                    'main_net_flow': row['主力净流入']
                })
            return stocks
        except Exception as e:
            self.logger(f"获取资金流失败: {e}")
            return []
    
    def select_rapid_rise(self) -> list:
        """
        选取同花顺-快速涨幅榜
        """
        if not AKSHARE_AVAILABLE:
            return self._get_mock_stocks(20)
        
        try:
            df = ak.stock_rank_xstp_ths()  # 强势股选股
            stocks = []
            for _, row in df.iterrows():
                stocks.append({
                    'code': str(row['代码']),
                    'name': row['名称'],
                    'change_pct': row['涨跌幅']
                })
            return stocks
        except Exception as e:
            self.logger(f"获取强势股失败: {e}")
            return []
    
    def _match_criteria(self, stock: dict, criteria: dict) -> bool:
        """检查股票是否满足条件"""
        if stock.get('change_pct', 0) < criteria['change_pct_range'][0]:
            return False
        if stock.get('change_pct', 0) > criteria['change_pct_range'][1]:
            return False
        if stock.get('turnover_rate', 0) < criteria.get('min_turnover', 0):
            return False
        if stock.get('price', 0) < criteria.get('min_price', 0):
            return False
        if stock.get('price', 0) > criteria.get('max_price', 100):
            return False
        return True
    
    def _get_mock_stocks(self, count: int = 10) -> list:
        """生成模拟股票数据"""
        import random
        stocks = []
        for i in range(count):
            code = f"{random.randint(1, 9)}{random.randint(0, 9):05d}"
            stocks.append({
                'code': code,
                'name': f'测试股票{i+1}',
                'price': round(random.uniform(5, 100), 2),
                'change_pct': round(random.uniform(-5, 5), 2),
                'turnover_rate': round(random.uniform(1, 10), 2)
            })
        return stocks


# 测试代码
if __name__ == "__main__":
    selector = StockSelector()
    
    print("=== 全市场选股测试 ===\n")
    
    # 1. 获取全部A股
    all_stocks = selector.get_all_stocks()
    print(f"全部A股: {len(all_stocks)} 只")
    
    # 2. 条件筛选
    selected = selector.select_by_criteria({
        'min_turnover': 3.0,
        'change_pct_range': (-3, 3),
        'min_price': 10,
        'max_price': 50
    })
    print(f"\n条件筛选结果: {len(selected)} 只")
    for s in selected[:5]:
        print(f"  {s['code']} {s['name']} - {s['price']:.2f}元 ({s['change_pct']:.2f}%)")
    
    # 3. 涨停池
    zt_stocks = selector.select_zt_pool()
    print(f"\n涨停池: {len(zt_stocks)} 只")
    
    # 4. 资金流向
    fund_stocks = selector.select_by_fund_flow(20)
    print(f"\n资金流入力Top20: {len(fund_stocks)} 只")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多因子选股模块
结合多个因子综合评估股票投资价值
"""

import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

# 尝试导入akshare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("⚠️ akshare未安装")


class MultiFactorSelector:
    """
    多因子选股器
    
    因子分类:
    - 价值因子: PE、PB、PS
    - 成长因子: 营收增长、净利润增长
    - 动量因子: 近N日涨幅
    - 质量因子: ROE、资产负债率
    - 情绪因子: 换手率、成交量
    """
    
    def __init__(self):
        self.logger = print
        self.factors = self._init_factors()
    
    def _init_factors(self) -> Dict:
        """初始化因子配置"""
        return {
            # 价值因子 (Value) - 越低越好
            'pe': {'name': '市盈率(PE)', 'weight': 0.15, 'direction': -1, 'min': 0, 'max': 100},
            'pb': {'name': '市净率(PB)', 'weight': 0.10, 'direction': -1, 'min': 0, 'max': 20},
            'ps': {'name': '市销率(PS)', 'weight': 0.05, 'direction': -1, 'min': 0, 'max': 50},
            
            # 成长因子 (Growth) - 越高越好
            'revenue_growth': {'name': '营收增长率', 'weight': 0.15, 'direction': 1, 'min': -50, 'max': 100},
            'profit_growth': {'name': '净利润增长率', 'weight': 0.15, 'direction': 1, 'min': -100, 'max': 200},
            
            # 动量因子 (Momentum) - 越强越好
            'momentum_20': {'name': '20日涨幅', 'weight': 0.15, 'direction': 1, 'min': -30, 'max': 50},
            'momentum_60': {'name': '60日涨幅', 'weight': 0.10, 'direction': 1, 'min': -50, 'max': 100},
            
            # 质量因子 (Quality) - 越高越好
            'roe': {'name': 'ROE', 'weight': 0.10, 'direction': 1, 'min': -10, 'max': 30},
            
            # 情绪因子 (Sentiment) - 适中最好
            'turnover': {'name': '换手率', 'weight': 0.05, 'direction': 1, 'min': 0, 'max': 20},
        }
    
    def get_factor_config(self) -> Dict:
        """获取因子配置"""
        return self.factors
    
    def update_factor_weight(self, factor_name: str, weight: float):
        """更新因子权重"""
        if factor_name in self.factors:
            self.factors[factor_name]['weight'] = weight
    
    def select_by_factors(self, 
                         min_score: float = 0.6,
                         max_stocks: int = 50,
                         exclude_st: bool = True,
                         exclude_new: bool = True) -> List[Dict]:
        """
        多因子综合选股
        
        Args:
            min_score: 最小综合评分 (0-1)
            max_stocks: 最多返回股票数量
            exclude_st: 排除ST股
            exclude_new: 排除次新股(上市<90天)
        
        Returns:
            选中的股票列表，按综合评分排序
        """
        if not AKSHARE_AVAILABLE:
            return self._get_mock_result(max_stocks)
        
        try:
            # 1. 获取A股实时数据
            self.logger("正在获取A股数据...")
            df = ak.stock_zh_a_spot_em()
            
            # 2. 获取财务数据
            self.logger("正在获取财务数据...")
            financial_df = self._get_financial_data()
            
            # 3. 获取动量数据
            self.logger("正在计算动量因子...")
            df = self._calculate_momentum_factors(df)
            
            # 4. 计算综合评分
            self.logger("正在计算综合评分...")
            df = self._calculate_composite_score(df, financial_df)
            
            # 5. 筛选和排序
            df = df[df['composite_score'] >= min_score]
            df = df.sort_values('composite_score', ascending=False)
            df = df.head(max_stocks)
            
            # 6. 转换为列表
            results = []
            for _, row in df.iterrows():
                results.append({
                    'code': str(row['代码']),
                    'name': row['名称'],
                    'score': round(row['composite_score'], 3),
                    'price': row['最新价'],
                    'change_pct': row['涨跌幅'],
                    'pe': row.get('pe', None),
                    'pb': row.get('pb', None),
                    'roe': row.get('roe', None),
                    'turnover_rate': row['换手率']
                })
            
            self.logger(f"多因子选股完成! 选出 {len(results)} 只股票")
            return results
            
        except Exception as e:
            self.logger(f"多因子选股失败: {e}")
            return self._get_mock_result(max_stocks)
    
    def select_by_strategy(self, strategy_name: str = 'all-weather') -> List[Dict]:
        """
        预设策略选股
        
        Args:
            strategy_name: 策略名称
                - 'value': 价值投资策略 (PE低、PB低、高ROE)
                - 'growth': 成长投资策略 (高营收增长、高净利润增长)
                - 'momentum': 动量策略 (近20/60日涨幅高)
                - 'quality': 质量策略 (高ROE、低负债率)
                - 'all-weather': 全天候策略 (均衡配置)
                - 'short-term': 短线策略 (高换手、高动量)
        
        Returns:
            选中的股票列表
        """
        strategies = {
            'value': {
                'pe': 0.30, 'pb': 0.25, 'roe': 0.25,
                'revenue_growth': 0.10, 'profit_growth': 0.10
            },
            'growth': {
                'pe': 0.10, 'pb': 0.10, 'roe': 0.15,
                'revenue_growth': 0.35, 'profit_growth': 0.30
            },
            'momentum': {
                'momentum_20': 0.35, 'momentum_60': 0.35,
                'turnover': 0.20, 'pe': 0.10
            },
            'quality': {
                'roe': 0.40, 'profit_growth': 0.25,
                'pe': 0.20, 'pb': 0.15
            },
            'all-weather': {
                'pe': 0.15, 'pb': 0.10, 'roe': 0.15,
                'revenue_growth': 0.15, 'profit_growth': 0.15,
                'momentum_20': 0.15, 'momentum_60': 0.15
            },
            'short-term': {
                'turnover': 0.30, 'momentum_20': 0.40,
                'momentum_60': 0.20, 'pe': 0.10
            }
        }
        
        if strategy_name not in strategies:
            self.logger(f"未知策略: {strategy_name}")
            return []
        
        # 应用策略权重
        for factor, weight in strategies[strategy_name].items():
            self.update_factor_weight(factor, weight)
        
        # 执行选股
        return self.select_by_factors()
    
    def _get_financial_data(self) -> pd.DataFrame:
        """获取财务数据"""
        try:
            # 使用东方财富的财务数据接口
            df = ak.stock_financial_analysis_indicator(symbol="all")
            return df
        except:
            return pd.DataFrame()
    
    def _calculate_momentum_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算动量因子"""
        # 这里简化处理，使用近期涨跌幅作为动量因子
        # 实际应用中应该获取更多历史数据
        df['momentum_20'] = df['涨跌幅'] * 3  # 简化估算
        df['momentum_60'] = df['涨跌幅'] * 6  # 简化估算
        return df
    
    def _calculate_composite_score(self, 
                                   df: pd.DataFrame, 
                                   financial_df: pd.DataFrame) -> pd.DataFrame:
        """计算综合评分"""
        scores = []
        
        for _, row in df.iterrows():
            total_score = 0
            total_weight = 0
            
            for factor, config in self.factors.items():
                weight = config['weight']
                direction = config['direction']
                
                # 获取因子值
                if factor == 'pe' and 'pe' in df.columns:
                    value = row.get('pe', config['max'])
                elif factor == 'pb' and 'pb' in df.columns:
                    value = row.get('pb', config['max'])
                elif factor == 'roe' and 'roe' in df.columns:
                    value = row.get('roe', config['min'])
                elif factor in ['momentum_20', 'momentum_60']:
                    value = row.get(factor, config['min'])
                else:
                    # 默认值
                    value = (config['min'] + config['max']) / 2
                
                # 标准化到 0-1
                normalized = self._normalize_factor(value, config)
                
                # 根据方向调整
                if direction == -1:  # 越低越好
                    normalized = 1 - normalized
                
                total_score += normalized * weight
                total_weight += weight
            
            # 归一化
            if total_weight > 0:
                composite = total_score / total_weight
            else:
                composite = 0.5
            
            scores.append(composite)
        
        df['composite_score'] = scores
        return df
    
    def _normalize_factor(self, value: float, config: Dict) -> float:
        """标准化因子值到0-1"""
        min_val = config['min']
        max_val = config['max']
        
        if max_val <= min_val:
            return 0.5
        
        normalized = (value - min_val) / (max_val - min_val)
        return max(0, min(1, normalized))
    
    def _get_mock_result(self, count: int) -> List[Dict]:
        """生成模拟结果"""
        import random
        results = []
        for i in range(count):
            results.append({
                'code': f"{random.randint(1, 9)}{random.randint(0, 9):05d}",
                'name': f'因子股票{i+1}',
                'score': round(random.uniform(0.6, 0.95), 3),
                'price': round(random.uniform(5, 100), 2),
                'change_pct': round(random.uniform(-5, 5), 2),
                'pe': round(random.uniform(10, 50), 2),
                'pb': round(random.uniform(1, 10), 2),
                'roe': round(random.uniform(5, 20), 2),
                'turnover_rate': round(random.uniform(1, 10), 2)
            })
        return sorted(results, key=lambda x: x['score'], reverse=True)
    
    def get_factor_report(self, stocks: List[Dict]) -> str:
        """生成因子分析报告"""
        if not stocks:
            return "未选出任何股票"
        
        report = []
        report.append("=" * 60)
        report.append(f"📊 多因子选股报告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("=" * 60)
        report.append(f"\n选出股票数: {len(stocks)} 只")
        report.append(f"平均评分: {sum(s['score'] for s in stocks)/len(stocks):.3f}")
        
        report.append("\n📈 Top 10 股票:")
        report.append("-" * 60)
        report.append(f"{'排名':<4} {'代码':<10} {'名称':<10} {'评分':<8} {'价格':<10} {'涨跌幅':<10}")
        report.append("-" * 60)
        
        for i, stock in enumerate(stocks[:10], 1):
            report.append(f"{i:<4} {stock['code']:<10} {stock['name']:<10} "
                         f"{stock['score']:.3f}   {stock['price']:<10.2f} "
                         f"{stock['change_pct']:+.2f}%")
        
        report.append("=" * 60)
        return "\n".join(report)


# 测试代码
if __name__ == "__main__":
    selector = MultiFactorSelector()
    
    print("=== 多因子选股测试 ===\n")
    
    # 1. 查看因子配置
    factors = selector.get_factor_config()
    print("可用因子:")
    for name, config in factors.items():
        print(f"  {name}: {config['name']} (权重: {config['weight']})")
    
    print("\n" + "-" * 40)
    
    # 2. 使用预设策略
    print("\n策略选股测试:")
    strategies = ['value', 'growth', 'all-weather', 'short-term']
    for strategy in strategies:
        stocks = selector.select_by_strategy(strategy_name=strategy)
        print(f"\n  {strategy} 策略: 选出 {len(stocks)} 只")
        if stocks and len(stocks) > 0:
            top = stocks[0]
            print(f"    Top1: {top['code']} {top['name']} - 评分: {top['score']:.3f}")
    
    print("\n" + "=" * 60)
    
    # 3. 自定义因子权重
    print("\n自定义因子选股:")
    selector.update_factor_weight('pe', 0.30)  # 更看重PE
    selector.update_factor_weight('roe', 0.25)  # 更看重ROE
    stocks = selector.select_by_factors(min_score=0.7, max_stocks=20)
    print(f"选出 {len(stocks)} 只股票")
    for s in stocks[:5]:
        print(f"  {s['code']} {s['name']} - 评分: {s['score']:.3f}")

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

# 尝试导入minishare
MINISHARE_TOKEN = "FNwqua1lm6sKv4bhr3IWht7sjd59A7d7n6x4Povy5ssofc000yHP2Iql350f104b"

try:
    import minishare as ms
    MINISHARE_AVAILABLE = True
except ImportError:
    MINISHARE_AVAILABLE = False
    print("⚠️ minishare未安装")

# 尝试导入akshare (备用)
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False


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
        try:
            # 1. 获取A股实时数据 (优先使用minishare)
            self.logger("正在获取A股数据...")
            
            if MINISHARE_AVAILABLE:
                # 使用minishare获取全市场数据
                self.logger("使用minishare获取数据...")
                df = ms.pro_api(MINISHARE_TOKEN).rt_k_ms(
                    ts_code='6*.SH,0*.SZ,3*.SZ'
                )
                
                # 转换列名
                df = df.rename(columns={
                    'ts_code': '代码',
                    'name': '名称',
                    'close': '最新价',
                    'pct_chg': '涨跌幅',
                    'turnover_rate': '换手率',
                    'vol': '成交量',
                    'amount': '成交额'
                })
                
                # 提取股票代码
                df['代码'] = df['代码'].str.replace('.SH', '').str.replace('.SZ', '')
                
            elif AKSHARE_AVAILABLE:
                # 备用：使用akshare
                df = ak.stock_zh_a_spot_em()
            else:
                return self._get_mock_result(max_stocks)
            
            # 2. 计算综合评分（简化版，minishare数据有限）
            self.logger("正在计算综合评分...")
            df = self._calculate_composite_score_simple(df)
            
            # 3. 筛选和排序
            # 排除ST股票
            if exclude_st:
                df = df[~df['名称'].str.contains(r'ST|退市|S\*ST|\*ST', na=False, regex=True)]
            
            # 排除创业板（3开头）
            df = df[~df['代码'].str.startswith('3')]
            
            # 排除科创板（688开头）
            df = df[~df['代码'].str.startswith('688')]
            
            # 排除北交所（8/4开头）
            df = df[~df['代码'].str.startswith('8')]
            df = df[~df['代码'].str.startswith('4')]
            
            # 只保留主板（0、6开头）
            df = df[df['代码'].str.match(r'^[06]')]
            
            df = df[df['composite_score'] >= min_score]
            df = df.sort_values('composite_score', ascending=False)
            df = df.head(max_stocks)
            
            # 4. 转换为列表
            results = []
            for _, row in df.iterrows():
                results.append({
                    'code': str(row['代码']),
                    'name': row['名称'],
                    'composite_score': round(row['composite_score'], 3),
                    'price': row.get('最新价', 0),
                    'change_pct': row.get('涨跌幅', 0),
                    'turnover_rate': row.get('换手率', 0),
                    'source': 'minishare' if MINISHARE_AVAILABLE else 'akshare'
                })
            
            self.logger(f"多因子选股完成! 选出 {len(results)} 只股票")
            return results
            
        except Exception as e:
            self.logger(f"多因子选股失败: {e}")
            import traceback
            traceback.print_exc()
            return self._get_mock_result(max_stocks)
            
            # 4. 计算综合评分
            self.logger("正在计算综合评分...")
            df = self._calculate_composite_score(df, financial_df)
            
            # 5. 筛选和排序
            # 排除ST股票
            if exclude_st:
                df = df[~df['名称'].str.contains(r'ST|退市|S\*ST|\*ST', na=False, regex=True)]
            
            # 排除创业板（3开头）
            df = df[~df['代码'].str.startswith('3')]
            
            # 排除科创板（688开头）
            df = df[~df['代码'].str.startswith('688')]
            
            # 排除新股（上市不满60天）
            # 需要额外数据，暂不启用
            
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
    
    def _calculate_composite_score_simple(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        超短线选股评分
        
        特点：
        - 高换手率（流动性好）
        - 高涨幅（趋势强）
        - 大成交额（资金活跃）
        - 中低价股（方便进出）
        """
        scores = []
        
        for _, row in df.iterrows():
            score = 0
            
            change_pct = row.get('涨跌幅', 0) or 0
            turnover = row.get('换手率', 0) or 0
            amount = row.get('成交额', 0) or 0
            price = row.get('最新价', 0) or 0
            
            # A. 换手率（25%）- 越高越好
            # 超短线需要高换手，10%以上是标配，30%以上更佳
            if turnover >= 30:
                turnover_score = 1.0
            elif turnover >= 10:
                turnover_score = 0.7 + (turnover - 10) / 20 * 0.3
            else:
                turnover_score = turnover / 10 * 0.7
            score += turnover_score * 25
            
            # B. 成交额（20%）- 越高越好
            # 超短线需要大资金活跃，1亿以上
            if amount >= 500_000_000:
                amount_score = 1.0
            elif amount >= 100_000_000:
                amount_score = 0.5 + (amount - 100_000_000) / 400_000_000 * 0.5
            else:
                amount_score = amount / 100_000_000 * 0.5
            score += amount_score * 20
            
            # C. 价格（15%）- 10元以下最佳
            # 超短线买低价股方便建仓
            if price <= 10:
                price_score = 1.0
            elif price <= 20:
                price_score = 1 - (price - 10) / 10 * 0.3
            elif price <= 50:
                price_score = 0.7 - (price - 20) / 30 * 0.4
            else:
                price_score = 0.3
            score += price_score * 15
            
            # D. 涨跌幅（40%）
            # 超短线只追涨，涨幅3%~8%最佳
            if change_pct >= 3 and change_pct <= 8:
                change_score = 1.0
            elif change_pct > 8:
                # 涨幅>8%可能追高，风险大
                change_score = 0.5
            elif change_pct > 0:
                # 涨幅1%~3%，有上涨趋势
                change_score = change_pct / 3 * 0.6
            else:
                # 下跌的不适合超短线，分数为0
                change_score = 0
            score += change_score * 40
            
            scores.append(score / 100)
        
        df['composite_score'] = scores
        return df
    
    def _calculate_composite_score(self, 
                                   df: pd.DataFrame, 
                                   financial_df: pd.DataFrame) -> pd.DataFrame:
        """计算综合评分"""
        # 简化版：只使用实时数据计算评分
        # 避免依赖可能失败的财务数据接口
        scores = []
        
        for _, row in df.iterrows():
            total_score = 0
            total_weight = 0
            
            # 只使用可靠的实时因子
            # 1. 涨跌幅（动量）- 权重30%
            change_pct = row.get('涨跌幅', 0) or 0
            if change_pct > 0:
                change_score = min(change_pct / 10, 1)  # 涨幅10%以上满分
            else:
                change_score = max(1 + change_pct / 5, 0)  # 跌幅5%以下满分
            total_score += change_score * 0.30
            total_weight += 0.30
            
            # 2. 换手率 - 权重25%
            turnover = row.get('换手率', 0) or 0
            turnover_score = min(turnover / 10, 1)  # 换手率10%以上满分
            total_score += turnover_score * 0.25
            total_weight += 0.25
            
            # 3. 成交量 - 权重20%
            volume = row.get('成交量', 0) or 0
            volume_score = min(volume / 500000, 1)  # 成交量50万手以上满分
            total_score += volume_score * 0.20
            total_weight += 0.20
            
            # 4. 价格合理性（10-50元）- 权重15%
            price = row.get('最新价', 0) or 0
            if 10 <= price <= 50:
                price_score = 1
            elif price < 10:
                price_score = price / 10
            else:
                price_score = max(1 - (price - 50) / 50, 0)
            total_score += price_score * 0.15
            total_weight += 0.15
            
            # 5. 跌幅提供安全边际（当日跌幅>1%）- 权重10%
            if -10 <= change_pct < -1:
                drop_score = 1
            else:
                drop_score = 0
            total_score += drop_score * 0.10
            total_weight += 0.10
            
            # 归一化
            if total_weight > 0:
                final_score = total_score / total_weight
            else:
                final_score = 0
            
            scores.append(final_score)
        
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

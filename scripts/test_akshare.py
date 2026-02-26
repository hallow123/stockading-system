#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试akshare是否能正常工作
"""
import sys
import os

# 添加脚本目录到路径
sys.path.insert(0, '/Users/wangmaofu/Desktop/股票自动化交易系统/scripts')

print("=" * 60)
print("测试 akshare 是否可用")
print("=" * 60)

# 测试1: 检查akshare是否安装
print("\n[1] 检查akshare是否安装...")
try:
    import akshare as ak
    print(f"   ✅ akshare已安装，版本: {ak.__version__}")
except ImportError as e:
    print(f"   ❌ akshare未安装: {e}")
    sys.exit(1)

# 测试2: 获取实时行情
print("\n[2] 测试获取实时行情 (stock_zh_a_spot_em)...")
try:
    df = ak.stock_zh_a_spot_em()
    print(f"   ✅ 成功! 获取到 {len(df)} 只股票")
    # 显示前5只
    print(df[['代码', '名称', '最新价']].head())
except Exception as e:
    print(f"   ❌ 失败: {e}")

# 测试3: 获取历史K线
print("\n[3] 测试获取历史K线 (stock_zh_a_hist)...")
try:
    import datetime
    end_date = datetime.datetime.now().strftime('%Y%m%d')
    start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d')
    
    df = ak.stock_zh_a_hist(
        symbol="600410",
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust="qfq"
    )
    print(f"   ✅ 成功! 获取到 {len(df)} 条数据")
    print(df[['日期', '开盘', '收盘', '涨跌幅']].tail())
except Exception as e:
    print(f"   ❌ 失败: {e}")

# 测试4: 获取指数数据
print("\n[4] 测试获取指数数据 (index_zh_a_hist)...")
try:
    df = ak.index_zh_a_hist(symbol="000001", period="daily")
    print(f"   ✅ 成功! 获取到 {len(df)} 条数据")
    print(df[['日期', '开盘', '收盘']].tail())
except Exception as e:
    print(f"   ❌ 失败: {e}")

# 测试5: 获取资金流向
print("\n[5] 测试获取资金流向 (stock_individual_fund_flow_rank)...")
try:
    df = ak.stock_individual_fund_flow_rank(symbol='A股', num=5)
    print(f"   ✅ 成功! 获取到 {len(df)} 条数据")
    print(df[['代码', '名称', '今日涨跌幅', '主力净流入-净额']].head())
except Exception as e:
    print(f"   ❌ 失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)

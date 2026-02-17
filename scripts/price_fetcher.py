#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
价格获取模块
从多个数据源获取股票价格数据
优先级：腾讯API > 百度搜索
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests

from config import config
from logger import Logger
from tonghuashun import TonghuashunFetcher


class PriceFetcher:
    """价格获取类"""
    
    # 腾讯股票API
    TENCENT_API_URL = "https://qt.gtimg.cn/q="
    
    # 请求头
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    }
    
    def __init__(self):
        self.logger = Logger.get_logger("price_fetcher")
        self.cache = {}  # 价格缓存
        self.tonghuashun = TonghuashunFetcher()
    
    def get_stock_code_with_market(self, stock_code: str) -> str:
        """
        获取带市场的股票代码
        上海: sh6xxxxxx
        深圳: sz0xxxxxx / sz3xxxxxx
        """
        if stock_code.startswith('6'):
            return f"sh{stock_code}"
        else:
            return f"sz{stock_code}"
    
    def fetch_price_from_tencent(self, stock_code: str) -> dict:
        """
        从腾讯API获取股票价格
        返回: 包含价格信息的字典
        """
        market_code = self.get_stock_code_with_market(stock_code)
        url = f"{self.TENCENT_API_URL}{market_code}"
        
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            response.raise_for_status()
            
            # 解析返回数据
            # 格式: v_sz002339="51~股票名~代码~当前价~涨跌~涨跌幅~..."
            # 或者: sz002339="51~股票名~代码~当前价~..."
            text = response.text.strip()
            
            if text == 'n/a' or not text or text == '""':
                self.logger.warning(f"股票{stock_code}未找到数据")
                return None
            
            # 找到等号后面的数据部分
            if '=' in text:
                text = text.split('=', 1)[1]
            
            # 去掉两边的引号
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1]
            
            if not text:
                self.logger.warning(f"股票{stock_code}数据为空")
                return None
            
            # 解析数据
            data = text.split('~')
            
            if len(data) < 10:
                self.logger.warning(f"股票{stock_code}数据格式异常")
                return None
            
            price_info = {
                'code': stock_code,
                'name': data[1],
                'price': float(data[3]),        # 当前价格
                'change': float(data[4]),       # 涨跌
                'change_pct': float(data[5]),   # 涨跌幅
                'open': float(data[6]),         # 今开
                'high': float(data[9]),         # 最高
                'low': float(data[10]),         # 最低
                'close': float(data[2]),        # 昨收（其实是当前价，用于计算）
                'volume': float(data[7]),       # 成交量(手)
                'amount': float(data[8]) * 1000 if len(data) > 8 else 0,  # 成交额(元)
                'turnover_rate': float(data[38]) if len(data) > 38 else 0,  # 换手率
                'pe': float(data[39]) if len(data) > 39 else 0,  # 市盈率
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.logger.info(f"获取到{price_info['name']}({stock_code})价格: {price_info['price']}")
            return price_info
            
        except requests.RequestException as e:
            self.logger.error(f"获取股票{stock_code}价格失败: {e}")
            return None
        except (ValueError, IndexError) as e:
            self.logger.error(f"解析股票{stock_code}数据失败: {e}")
            return None
    
    def fetch_price_from_xueqiu(self, stock_code: str) -> dict:
        """
        从雪球API获取股票价格（备用方案）
        """
        # 雪球需要cookie，这里作为备选
        pass
    
    def fetch_price(self, stock_code: str) -> dict:
        """
        获取股票价格（综合多种数据源）
        优先级：同花顺 > 腾讯API
        
        重要说明：
        - 优先使用同花顺APP进行价格提取
        - 腾讯API仅作为最后备选（可能会卡顿）
        """
        # ========== Step 1: 优先使用同花顺 ==========
        print(f"正在获取 {stock_code} 的价格（优先使用同花顺APP）...")
        try:
            ths_price = self.tonghuashun.fetch_price(stock_code)
            if ths_price and ths_price.price > 0:
                print(f"✅ 同花顺获取成功: ¥{ths_price.price}")
                return {
                    'code': stock_code,
                    'name': ths_price.name,
                    'price': ths_price.price,
                    'change': ths_price.change,
                    'change_pct': ths_price.change_pct,
                    'open': ths_price.open,
                    'high': ths_price.high,
                    'low': ths_price.low,
                    'close': ths_price.close,
                    'volume': ths_price.volume,
                    'amount': ths_price.amount,
                    'timestamp': ths_price.timestamp,
                    'source': '同花顺'
                }
            else:
                print(f"⚠️ 同花顺获取结果无效（价格: {ths_price.price if ths_price else 'None'}）")
        except Exception as e:
            print(f"❌ 同花顺查询失败: {e}")
        
        # ========== Step 2: 腾讯API仅作为最后备选 ==========
        print(f"\n⚠️ 警告：腾讯API仅作为最后备选，可能会卡顿...")
        print(f"正在通过腾讯API获取 {stock_code} 价格...")
        price_info = self.fetch_price_from_tencent(stock_code)
        
        if price_info:
            print(f"✅ 腾讯API获取成功: ¥{price_info['price']}")
            price_info['source'] = '腾讯API'
            return price_info
        
        # ========== Step 3: 所有数据源均失败 ==========
        print(f"❌ 股票{stock_code}所有数据源均获取失败")
        return None
    
    def fetch_all(self, stocks: list) -> dict:
        """
        批量获取多个股票价格
        stocks: [{"code": "002339", "name": "积成电子"}, ...]
        """
        results = {}
        
        for stock in stocks:
            stock_code = stock.get('code')
            if not stock_code:
                continue
            
            self.logger.info(f"正在获取 {stock.get('name', stock_code)} 的价格...")
            
            price_info = self.fetch_price(stock_code)
            
            if price_info:
                results[stock_code] = price_info
            else:
                # 如果获取失败，记录错误
                results[stock_code] = {
                    'code': stock_code,
                    'name': stock.get('name', ''),
                    'error': '获取价格失败',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            # 避免请求过快
            time.sleep(0.5)
        
        return results
    
    def save_prices(self, prices: dict, file_path: str = None):
        """保存价格数据到文件"""
        if file_path is None:
            base_dir = Path(__file__).parent.parent
            file_path = base_dir / "prices.json"
        
        try:
            # 读取现有数据
            existing_data = {}
            if Path(file_path).exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            
            # 合并新数据
            existing_data['prices'] = prices
            existing_data['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 保存
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"价格数据已保存到 {file_path}")
            
        except Exception as e:
            self.logger.error(f"保存价格数据失败: {e}")
    
    def load_prices(self, file_path: str = None) -> dict:
        """从文件加载价格数据"""
        if file_path is None:
            base_dir = Path(__file__).parent.parent
            file_path = base_dir / "prices.json"
        
        try:
            if Path(file_path).exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"加载价格数据失败: {e}")
        
        return {'prices': [], 'last_update': None}
    
    def load_stocks(self, file_path: str = None) -> list:
        """加载自选股列表"""
        if file_path is None:
            base_dir = Path(__file__).parent.parent
            file_path = base_dir / "stocks.json"
        
        try:
            if Path(file_path).exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('watchlist', [])
        except Exception as e:
            self.logger.error(f"加载自选股列表失败: {e}")
        
        return []


# 测试代码
if __name__ == "__main__":
    fetcher = PriceFetcher()
    
    # 测试获取单只股票
    # result = fetcher.fetch_price("002339")
    # print(result)
    
    # 测试批量获取
    stocks = [
        {"code": "002339", "name": "积成电子"},
        {"code": "002237", "name": "恒邦股份"},
        {"code": "601166", "name": "兴业银行"},
        {"code": "002236", "name": "大华股份"}
    ]
    
    results = fetcher.fetch_all(stocks)
    print(json.dumps(results, ensure_ascii=False, indent=2))

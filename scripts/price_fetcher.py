#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
价格获取模块
从多个数据源获取股票价格数据
优先级：东方财富API > 同花顺 > 腾讯API
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
from datetime import time as dt_time


# A股交易时段
TRADING_MORNING_START = dt_time(9, 30)
TRADING_MORNING_END = dt_time(11, 30)
TRADING_AFTERNOON_START = dt_time(13, 0)
TRADING_AFTERNOON_END = dt_time(15, 0)


def is_trading_hours() -> bool:
    """检查当前是否在A股交易时段（9:30-11:30, 13:00-15:00）"""
    now = datetime.now()
    current_time = now.time()
    
    # 上午时段 9:30-11:30
    if TRADING_MORNING_START <= current_time <= TRADING_MORNING_END:
        return True
    # 下午时段 13:00-15:00
    if TRADING_AFTERNOON_START <= current_time <= TRADING_AFTERNOON_END:
        return True
    
    return False


def is_price_monitoring_hours() -> bool:
    """检查当前是否可以获取价格（9:20开始监控，9:30可交易）"""
    now = datetime.now()
    current_time = now.time()
    PRICE_MONITORING_START = dt_time(9, 20)
    
    # 价格监控时段 9:20-11:30
    if PRICE_MONITORING_START <= current_time <= TRADING_MORNING_END:
        return True
    # 下午时段 13:00-15:00
    if TRADING_AFTERNOON_START <= current_time <= TRADING_AFTERNOON_END:
        return True
    
    return False


def is_trading_day() -> bool:
    """简单判断是否为交易日的辅助函数（周末不交易）"""
    now = datetime.now()
    # 周末不交易
    if now.weekday() >= 5:  # 5=Saturday, 6=Sunday
        return False
    return True


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
    
    def fetch_price_from_minishare(self, stock_code: str) -> dict:
        """
        从minishare获取股票价格
        返回: 包含价格信息的字典
        """
        # 获取token
        token = config.get('data', {}).get('minishare_token', '')
        if not token:
            print("未配置minishare_token")
            return None
        
        # 转换股票代码格式
        if stock_code.startswith('6'):
            ts_code = f"{stock_code}.SH"
        elif stock_code.startswith('0') or stock_code.startswith('3'):
            ts_code = f"{stock_code}.SZ"
        else:
            ts_code = f"{stock_code}.SZ"
        
        try:
            import minishare as ms
            df = ms.pro_api(token).rt_k_ms(ts_code=ts_code)
            
            if df is not None and len(df) > 0:
                row = df.iloc[0]
                return {
                    'code': stock_code,
                    'name': row.get('name', ''),
                    'price': float(row.get('close', 0)),
                    'change': float(row.get('change', 0)),
                    'change_pct': float(row.get('pct_chg', 0)),
                    'open': float(row.get('open', 0)),
                    'high': float(row.get('high', 0)),
                    'low': float(row.get('low', 0)),
                    'close': float(row.get('close', 0)),
                    'prev': float(row.get('pre_close', 0)),
                    'volume': float(row.get('vol', 0)),
                    'amount': float(row.get('amount', 0)),
                    'turnover_rate': float(row.get('turnover_rate', 0)),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'source': 'minishare'
                }
        except Exception as e:
            print(f"minishare错误: {e}")
        
        return None
        
        return None
    
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
    
    def fetch_price_from_eastmoney(self, stock_code: str) -> dict:
        """
        从东方财富API获取股票价格
        """
        # 沪深股票代码转换
        if stock_code.startswith('6'):
            market = '1'  # 上海
        else:
            market = '0'  # 深圳
        
        url = 'https://push2.eastmoney.com/api/qt/stock/get'
        params = {
            'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
            'invt': '2',
            'fltt': '2',
            'fields': 'f43,f44,f45,f46,f47,f48,f57,f58,f60,f170,f171',
            'secid': f'{market}.{stock_code}'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('data'):
                d = data['data']
                return {
                    'code': stock_code,
                    'name': d.get('f58', ''),
                    'price': d.get('f43', 0) / 1000 if d.get('f43') else 0,  # f43需要除以1000
                    'change': d.get('f170', 0) / 100 if d.get('f170') else 0,
                    'change_pct': d.get('f171', 0) / 100 if d.get('f171') else 0,
                    'open': d.get('f44', 0) / 1000 if d.get('f44') else 0,
                    'high': d.get('f46', 0) / 1000 if d.get('f46') else 0,
                    'low': d.get('f45', 0) / 1000 if d.get('f45') else 0,
                    'close': d.get('f60', 0) / 1000 if d.get('f60') else 0,
                    'volume': d.get('f47', 0),
                    'amount': d.get('f48', 0),
                    'turnover_rate': d.get('f57', 0) / 100 if d.get('f57') else 0,
                    'pe': d.get('f162', 0) / 1000 if d.get('f162') else 0,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
        except Exception as e:
            self.logger.warning(f"东方财富API获取{stock_code}失败: {e}")
            return None
    
    def fetch_price(self, stock_code: str, force: bool = False) -> dict:
        """
        获取股票价格（综合多种数据源）
        优先级：minishare > 东方财富API
        
        重要说明：
        - 只返回实时价格，获取失败返回None
        - 不使用缓存，避免误判
        
        参数:
            force: 是否强制查询（非交易时段也查询）
        """
        # 非交易时段且不强制查询时，返回None
        if not force and not is_price_monitoring_hours():
            # 不打印，避免频繁输出
            return None
        
        # ========== minishare API（唯一数据源）==========
        print(f"正在获取 {stock_code} 的价格（minishare）...")
        price_info = self.fetch_price_from_minishare(stock_code)
        
        if price_info and price_info.get('price', 0) > 0:
            print(f"✅ minishare获取成功: ¥{price_info['price']}")
            return price_info
        else:
            # minishare失败，返回None（不适用其他数据源）
            print(f"❌ 股票{stock_code} minishare获取失败")
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
            
            # 避免请求过快，间隔5秒
            time.sleep(5)
        
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

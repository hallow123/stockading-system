#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同花顺价格查询模块

功能：
- 通过同花顺Mac应用获取实时股价
- 支持单只股票查询和批量查询
"""

import subprocess
import time
import re
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class StockPrice:
    """股价数据结构"""
    code: str
    name: str
    price: float
    change: float
    change_pct: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    timestamp: str


class TonghuashunFetcher:
    """同花顺价格查询器"""

    # 界面坐标
    SEARCH_BOX = (698, 37)  # 搜索框坐标

    def __init__(self):
        pass

    def _execute_cmd(self, cmd: str) -> bool:
        """执行shell命令"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return True
        except Exception as e:
            print(f"命令执行失败: {e}")
            return False

    def _click(self, x: int, y: int) -> bool:
        """点击指定坐标"""
        cmd = f"cliclick m:{x},{y}"
        return self._execute_cmd(cmd)

    def _type_text(self, text: str) -> bool:
        """输入文本"""
        cmd = f"cliclick t:{text}"
        return self._execute_cmd(cmd)

    def _press_enter(self) -> bool:
        """按回车键"""
        cmd = 'osascript -e \'tell application "System Events" to key code 36\''
        return self._execute_cmd(cmd)

    def _wait(self, seconds: float):
        """等待"""
        time.sleep(seconds)

    def _run_apple_script(self, script: str) -> Optional[str]:
        """执行AppleScript并返回结果"""
        
        print(f"执行AppleScript...")
        print(f"脚本长度: {len(script)} 字符")
        
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=10  # 添加超时
            )
            
            print(f"AppleScript返回码: {result.returncode}")
            print(f"stdout长度: {len(result.stdout)}")
            print(f"stderr: {result.stderr}")
            
            if result.stdout:
                print(f"原始输出: {result.stdout[:200]}...")
                return result.stdout.strip()
            else:
                print("无stdout输出")
                return None
                
        except subprocess.TimeoutExpired:
            print("❌ AppleScript执行超时")
            return None
        except Exception as e:
            print(f"❌ AppleScript执行异常: {e}")
            return None

    def _activate_window(self):
        """激活同花顺窗口"""
        script = '''
        tell application "System Events"
            tell process "同花顺"
                set frontmost to true
                delay 0.5
            end tell
        end tell
        '''
        self._run_apple_script(script)

    def _extract_price_with_apple_script(self) -> Optional[str]:
        """使用增强版AppleScript提取价格（多方案尝试）"""
        
        scripts = [
            # 方案1: 查询所有UI元素，查找包含价格和"元"的文本
            '''
            tell application "System Events"
                tell process "同花顺"
                    set results to {}
                    try
                        set allElements to every UI element
                        repeat with anElement in allElements
                            try
                                set elemValue to value of anElement as text
                                if elemValue contains "元" and elemValue contains "." then
                                    return elemValue
                                end if
                            end try
                        end repeat
                    end try
                    return ""
                end tell
            end tell
            ''',
            
            # 方案2: 查询所有静态文本
            '''
            tell application "System Events"
                tell process "同花顺"
                    set results to {}
                    try
                        set allText to every static text
                        repeat with aText in allText
                            try
                                set textValue to value of aText as text
                                if textValue contains "元" and textValue contains "." then
                                    return textValue
                                end if
                            end try
                        end repeat
                    end try
                    return ""
                end tell
            end tell
            ''',
            
            # 方案3: 获取整个窗口文本
            '''
            tell application "System Events"
                tell process "同花顺"
                    try
                        return entire contents of window 1
                    on error
                        return ""
                    end try
                end tell
            end tell
            ''',
            
            # 方案4: 查找价格显示区域（更精确的匹配）
            '''
            tell application "System Events"
                tell process "同花顺"
                    set results to {}
                    try
                        set allText to every static text
                        repeat with aText in allText
                            try
                                set textValue to value of aText as text
                                -- 匹配价格模式: 数字.数字元
                                if textValue matches "^[0-9]+\\\\.[0-9]+元" then
                                    return textValue
                                end if
                                -- 匹配涨跌幅: 数字.数字%
                                if textValue contains "%" then
                                    set end of results to textValue
                                end if
                            end try
                        end repeat
                    end try
                    return ""
                end tell
            end tell
            '''
        ]
        
        for i, script in enumerate(scripts, 1):
            print(f"尝试提取方案 {i}...")
            result = self._run_apple_script(script)
            if result and len(result) > 0:
                print(f"方案 {i} 获取到结果: {result[:100]}...")
                return result
            print(f"方案 {i} 无结果")
        
        return None

    def _extract_all_data_with_apple_script(self) -> Optional[Dict]:
        """使用AppleScript提取所有股票数据"""
        script = '''
        tell application "System Events"
            tell process "同花顺"
                set allText to every static text
                set allData to {}
                repeat with aText in allText
                    try
                        set textValue to value of aText as text
                        set end of allData to textValue
                    end try
                end repeat
                return allData
            end tell
        end tell
        '''
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True
            )
            if result.stdout:
                return {'raw_text': result.stdout.strip()}
            return None
        except Exception as e:
            print(f"AppleScript执行失败: {e}")
            return None

    def _parse_price_text(self, stock_code: str, text: str) -> Optional[StockPrice]:
        """解析价格文本"""
        
        print(f"\n开始解析文本，长度: {len(text)}")
        print(f"文本内容:\n{text[:300]}\n...")
        
        try:
            print(f"正在解析价格文本: {text}")
            
            # 提取涨跌金额（可能在价格后面，如 "16.90↓ -0.36 -2.09%"）
            change = 0.0
            change_match = re.search(r'([+-]?\d+\.?\d*)\s*[-↓↑]', text)
            if change_match:
                change_str = change_match.group(1)
                # 去掉符号，只保留数字
                change_num = float(re.sub(r'^[+-]', '', change_str))
                # 根据符号确定正负
                if '-' in change_match.group(0) and '↑' not in change_match.group(0):
                    change = -change_num
                else:
                    change = change_num
                print(f"提取到涨跌: {change}")
            
            # 提取价格数字 (匹配 "16.91元" 或 "16.90" 或 "16.91↓")
            price_patterns = [
                r'(\d+\.\d+)\s*[-↓↑]',  # 带箭头符号的价格
                r'^(\d+\.\d+)',          # 开头就是价格
                r'(\d+\.\d+)\s*元',       # 带"元"的模式
            ]
            
            price = 0.0
            for pattern in price_patterns:
                price_match = re.search(pattern, text)
                if price_match:
                    price = float(price_match.group(1))
                    print(f"提取到价格: {price}")
                    break
            
            # 提取涨跌幅 (匹配 "-2.09%" 或 "+3.5%")
            pct_match = re.search(r'([+-]?\d+\.\d+)%', text)
            change_pct = float(pct_match.group(1)) if pct_match else 0.0
            print(f"提取到涨跌幅: {change_pct}%")
            
            # 验证数据有效性
            if price <= 0:
                print("价格无效（<=0）")
                return None
            if abs(change_pct) > 50:  # 涨跌幅超过50%视为异常
                print(f"涨跌幅异常: {change_pct}%")
                return None
            
            print(f"解析成功: 价格={price}, 涨跌={change}, 涨跌幅={change_pct}%")
            
            # 返回StockPrice对象
            return StockPrice(
                code=stock_code,
                name="",  # 需要从UI获取
                price=price,
                change=change,
                change_pct=change_pct,
                open=0.0,
                high=0.0,
                low=0.0,
                close=0.0,
                volume=0.0,
                amount=0.0,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
            )

        except Exception as e:
            print(f"❌ 解析异常: {e}")
            import traceback
            traceback.print_exc()
            return None

    def debug_extract(self):
        """调试提取 - 打印所有可获取的文本"""
        
        print("\n" + "="*60)
        print("🔍 调试提取")
        print("="*60)
        
        # 打印所有静态文本
        script = '''
        tell application "System Events"
            tell process "同花顺"
                set output to ""
                try
                    set allText to every static text
                    repeat with i from 1 to count of allText
                        set aText to item i of allText
                        try
                            set txtValue to value of aText as text
                            if txtValue contains "元" or txtValue contains "." then
                                set output to output & "[" & i & "] " & txtValue & "\n"
                            end if
                        end try
                    end repeat
                on error errMsg
                    set output to "ERROR: " & errMsg
                end try
                return output
            end tell
        end tell
        '''
        
        print("\n获取所有包含'元'或'.'的文本元素...")
        result = self._run_apple_script(script)
        
        if result:
            print(f"\n✅ 获取到 {len(result)} 字符")
            print("\n" + "-"*60)
            print(result)
            print("-"*60)
        else:
            print("❌ 未能获取任何数据")

    def fetch_price(self, stock_code: str, timeout_seconds: float = 15.0) -> Optional[StockPrice]:
        """
        获取单只股票价格

        Args:
            stock_code: 股票代码，如 '002237'
            timeout_seconds: 超时时间（秒），默认15秒

        Returns:
            StockPrice对象，失败返回None
        """
        
        print(f"\n{'='*50}")
        print(f"开始查询 {stock_code} (超时: {timeout_seconds}秒)")
        print(f"{'='*50}")

        # 记录开始时间
        start_time = time.time()

        try:
            # Step 1: 激活窗口
            remaining = timeout_seconds - (time.time() - start_time)
            if remaining <= 0:
                print(f"❌ 超时，跳过 {stock_code}")
                return None
            
            print(f"\n[1/5] 激活窗口... (剩余 {remaining:.1f}秒)")
            self._activate_window()
            self._wait(0.3)

            # Step 2: 点击搜索框
            remaining = timeout_seconds - (time.time() - start_time)
            if remaining <= 0:
                print(f"❌ 超时，跳过 {stock_code}")
                return None
            
            print(f"[2/5] 点击搜索框... (剩余 {remaining:.1f}秒)")
            self._click(*self.SEARCH_BOX)
            self._wait(0.3)

            # Step 3: 输入股票代码
            remaining = timeout_seconds - (time.time() - start_time)
            if remaining <= 0:
                print(f"❌ 超时，跳过 {stock_code}")
                return None
            
            print(f"[3/5] 输入股票代码: {stock_code}")
            self._type_text(stock_code)
            self._wait(0.3)

            # Step 4: 按回车键搜索
            remaining = timeout_seconds - (time.time() - start_time)
            if remaining <= 0:
                print(f"❌ 超时，跳过 {stock_code}")
                return None
            
            print(f"[4/5] 按回车键... (剩余 {remaining:.1f}秒)")
            self._press_enter()
            self._wait(1)  # 减少等待时间：1秒足够

            # Step 5: 提取价格（减少重试次数）
            remaining = timeout_seconds - (time.time() - start_time)
            if remaining <= 0:
                print(f"❌ 超时，跳过 {stock_code}")
                return None
            
            print(f"[5/5] 提取价格数据... (剩余 {remaining:.1f}秒)")
            
            # 只重试1次（减少等待）
            price_text = self._extract_price_with_apple_script()
            
            if price_text:
                print(f"✅ 获取到价格文本: {price_text}")
                result = self._parse_price_text(stock_code, price_text)
                if result and result.price > 0:
                    elapsed = time.time() - start_time
                    print(f"\n✅ 提取成功! (耗时 {elapsed:.1f}秒)")
                    return result
                else:
                    print("❌ 解析结果无效")
            else:
                print("❌ 未能获取到价格数据")
            
            elapsed = time.time() - start_time
            print(f"\n⚠️ 查询 {stock_code} 完成 (耗时 {elapsed:.1f}秒) - 结果: 失败")
            return None

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n❌ 异常: {e} (耗时 {elapsed:.1f}秒)")
            import traceback
            traceback.print_exc()
            return None

    def fetch_all_prices(self, stock_list: List[Dict]) -> Dict[str, Optional[StockPrice]]:
        """
        批量获取多只股票价格

        Args:
            stock_list: 股票列表 [{'code': '002237', 'name': '恒邦股份'}, ...]

        Returns:
            {股票代码: StockPrice对象}
        """
        results = {}
        total = len(stock_list)
        
        for idx, stock in enumerate(stock_list, 1):
            code = stock['code']
            name = stock.get('name', '')
            
            print(f"\n{'🔍'*20}")
            print(f"查询 {idx}/{total}: {name}({code})")
            
            # 每只股票最多15秒超时
            price = self.fetch_price(code, timeout_seconds=15.0)
            
            if price:
                price.name = name
                results[code] = price
                print(f"✅ {name}: ¥{price.price}")
            else:
                results[code] = None
                print(f"❌ {name}: 查询失败")
            
            # 减少间隔时间：0.5秒足够
            if idx < total:  # 最后一只不需要等待
                time.sleep(0.5)
        
        print(f"\n{'='*50}")
        print(f"批量查询完成: 成功 {sum(1 for v in results.values() if v)}/{total}")
        print(f"{'='*50}")
        
        return results


# 测试代码
if __name__ == "__main__":
    fetcher = TonghuashunFetcher()
    
    # 测试获取单只股票
    price = fetcher.fetch_price("002237")
    if price:
        print(f"\n恒邦股份当前价格: ¥{price.price}")
        print(f"涨跌幅: {price.change_pct}%")
    else:
        print("查询失败")

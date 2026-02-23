#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票自动交易系统 - macOS App
版本: 1.0
日期: 2026-02-23
"""

import os
import sys
import json
import subprocess
import threading
import time
from datetime import datetime

# 添加 scripts 目录到路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# 导入原有模块
try:
    from scripts.tonghuashun import TonghuashunFetcher
    from scripts.trade_executor import TradeExecutor
    from scripts.trend_analyzer import TrendAnalyzer
    from scripts.notification import send_feishu_message
    MODULES_AVAILABLE = True
except ImportError as e:
    MODULES_AVAILABLE = False
    print(f"⚠️ 模块导入失败: {e}")

# ========== GUI 框架 ==========
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# ========== 配置 ==========
APP_NAME = "股票自动交易"
VERSION = "1.0"
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
LOG_FILE = os.path.join(SCRIPT_DIR, "logs", f"app_{datetime.now().strftime('%Y%m%d')}.log")

# 确保目录存在
os.makedirs(os.path.join(SCRIPT_DIR, "logs"), exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


class StockTraderApp:
    """股票交易 macOS App 主类"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # 状态变量
        self.is_monitoring = False
        self.monitor_thread = None
        self.stocks_to_watch = []
        
        # 加载配置
        self.load_config()
        
        # 构建界面
        self.create_menu()
        self.create_widgets()
        self.load_watch_list()
        
        # 日志
        self.log("🚀 股票自动交易系统启动")
        self.log(f"📁 工作目录: {SCRIPT_DIR}")
        
    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = {
                    "stocks": [],
                    "max_position": 5,
                    "stop_loss_pct": -5,
                    "take_profit_pct": 10
                }
                self.save_config()
        except Exception as e:
            self.log(f"⚠️ 配置加载失败: {e}")
            self.config = {}
    
    def save_config(self):
        """保存配置"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"⚠️ 配置保存失败: {e}")
    
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="刷新自选股", command=self.refresh_stocks)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit_app)
        
        # 交易菜单
        trade_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="交易", menu=trade_menu)
        trade_menu.add_command(label="买入", command=self.show_buy_dialog)
        trade_menu.add_command(label="卖出", command=self.show_sell_dialog)
        trade_menu.add_separator()
        trade_menu.add_command(label="开始监控", command=self.start_monitoring)
        trade_menu.add_command(label="停止监控", command=self.stop_monitoring)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ===== 顶部状态栏 =====
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="🟢 就绪", font=("SF Pro", 12))
        self.status_label.pack(side=tk.LEFT)
        
        self.time_label = ttk.Label(status_frame, text="", font=("SF Pro", 10))
        self.time_label.pack(side=tk.RIGHT)
        self.update_time()
        
        # ===== 标签页 =====
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 持仓页
        self.position_frame = ttk.Frame(notebook)
        notebook.add(self.position_frame, text="📊 持仓")
        self.create_position_tab()
        
        # 自选股页
        self.watch_frame = ttk.Frame(notebook)
        notebook.add(self.watch_frame, text="⭐ 自选股")
        self.create_watch_tab()
        
        # 交易记录页
        self.trade_frame = ttk.Frame(notebook)
        notebook.add(self.trade_frame, text="📜 交易记录")
        self.create_trade_tab()
        
        # 日志页
        self.log_frame = ttk.Frame(notebook)
        notebook.add(self.log_frame, text="📝 日志")
        self.create_log_tab()
        
        # ===== 底部按钮栏 =====
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="🔄 刷新价格", command=self.refresh_prices).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📈 买入", command=self.show_buy_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📉 卖出", command=self.show_sell_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🛑 停止监控", command=self.stop_monitoring).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="▶️ 开始监控", command=self.start_monitoring).pack(side=tk.RIGHT, padx=5)
    
    def create_position_tab(self):
        """持仓页面"""
        # 持仓表格
        columns = ("股票代码", "股票名称", "持仓量", "成本价", "当前价", "盈亏", "盈亏%")
        self.position_tree = ttk.Treeview(self.position_frame, columns=columns, show="headings")
        
        for col in columns:
            self.position_tree.heading(col, text=col)
            self.position_tree.column(col, width=100)
        
        self.position_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 加载持仓数据
        self.load_positions()
    
    def create_watch_tab(self):
        """自选股页面"""
        # 工具栏
        toolbar = ttk.Frame(self.watch_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="➕ 添加", command=self.add_stock).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="➖ 删除", command=self.remove_stock).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_prices).pack(side=tk.LEFT, padx=2)
        
        # 自选股表格
        columns = ("股票代码", "股票名称", "当前价", "涨跌", "涨跌幅%", "MA5", "MA20", "状态")
        self.watch_tree = ttk.Treeview(self.watch_frame, columns=columns, show="headings")
        
        for col in columns:
            self.watch_tree.heading(col, text=col)
            self.watch_tree.column(col, width=80)
        
        self.watch_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 加载自选股
        self.load_watch_list()
    
    def create_trade_tab(self):
        """交易记录页面"""
        columns = ("时间", "股票代码", "股票名称", "方向", "价格", "数量", "状态")
        self.trade_tree = ttk.Treeview(self.trade_frame, columns=columns, show="headings")
        
        for col in columns:
            self.trade_tree.heading(col, text=col)
            self.trade_tree.column(col, width=100)
        
        self.trade_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 加载交易记录
        self.load_trades()
    
    def create_log_tab(self):
        """日志页面"""
        self.log_text = scrolledtext.ScrolledText(self.log_frame, wrap=tk.WORD, font=("Menlo", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # ========== 数据加载 ==========
    def load_positions(self):
        """加载持仓数据"""
        try:
            # 清除现有数据
            for item in self.position_tree.get_children():
                self.position_tree.delete(item)
            
            # 尝试加载持仓文件
            positions_file = os.path.join(DATA_DIR, "positions.json")
            if os.path.exists(positions_file):
                with open(positions_file, 'r', encoding='utf-8') as f:
                    positions = json.load(f)
                
                for pos in positions:
                    pnl = (pos.get('current_price', 0) - pos.get('cost_price', 0)) * pos.get('quantity', 0)
                    pnl_pct = ((pos.get('current_price', 0) / pos.get('cost_price', 1)) - 1) * 100 if pos.get('cost_price', 0) > 0 else 0
                    
                    self.position_tree.insert("", tk.END, values=(
                        pos.get('code', ''),
                        pos.get('name', ''),
                        pos.get('quantity', 0),
                        f"{pos.get('cost_price', 0):.2f}",
                        f"{pos.get('current_price', 0):.2f}",
                        f"{pnl:.2f}",
                        f"{pnl_pct:.2f}%"
                    ))
        except Exception as e:
            self.log(f"⚠️ 持仓加载失败: {e}")
    
    def load_watch_list(self):
        """加载自选股列表"""
        try:
            # 清除现有数据
            for item in self.watch_tree.get_children():
                self.watch_tree.delete(item)
            
            # 加载自选股
            stocks_file = os.path.join(DATA_DIR, "stocks.json")
            if os.path.exists(stocks_file):
                with open(stocks_file, 'r', encoding='utf-8') as f:
                    stocks = json.load(f)
                
                for stock in stocks:
                    self.watch_tree.insert("", tk.END, values=(
                        stock.get('code', ''),
                        stock.get('name', ''),
                        stock.get('price', '--'),
                        stock.get('change', '--'),
                        stock.get('change_pct', '--'),
                        stock.get('ma5', '--'),
                        stock.get('ma20', '--'),
                        stock.get('signal', '🟡 观察')
                    ))
                    self.stocks_to_watch.append(stock.get('code', ''))
        except Exception as e:
            self.log(f"⚠️ 自选股加载失败: {e}")
    
    def load_trades(self):
        """加载交易记录"""
        try:
            # 清除现有数据
            for item in self.trade_tree.get_children():
                self.trade_tree.delete(item)
            
            # 加载交易记录
            trades_file = os.path.join(DATA_DIR, "trades.json")
            if os.path.exists(trades_file):
                with open(trades_file, 'r', encoding='utf-8') as f:
                    trades = json.load(f)
                
                for trade in trades:
                    direction = "📈 买入" if trade.get('direction') == 'buy' else "📉 卖出"
                    self.trade_tree.insert("", tk.END, values=(
                        trade.get('time', ''),
                        trade.get('code', ''),
                        trade.get('name', ''),
                        direction,
                        f"{trade.get('price', 0):.2f}",
                        trade.get('quantity', 0),
                        trade.get('status', '已完成')
                    ))
        except Exception as e:
            self.log(f"⚠️ 交易记录加载失败: {e}")
    
    # ========== 操作方法 ==========
    def refresh_stocks(self):
        """刷新自选股列表"""
        self.load_watch_list()
        self.log("📋 自选股列表已刷新")
    
    def refresh_prices(self):
        """刷新价格"""
        if not MODULES_AVAILABLE:
            messagebox.showwarning("警告", "交易模块不可用")
            return
        
        self.log("🔄 正在刷新价格...")
        
        def do_refresh():
            try:
                fetcher = TonghuashunFetcher()
                for stock in self.stocks_to_watch:
                    try:
                        price_data = fetcher.fetch_price(stock)
                        if price_data:
                            self.log(f"📊 {stock}: {price_data.get('price', '--')}元")
                    except Exception as e:
                        self.log(f"⚠️ {stock} 价格获取失败: {e}")
                
                self.log("✅ 价格刷新完成")
            except Exception as e:
                self.log(f"⚠️ 价格刷新失败: {e}")
        
        threading.Thread(target=do_refresh, daemon=True).start()
    
    def add_stock(self):
        """添加自选股"""
        dialog = tk.Toplevel(self.root)
        dialog.title("添加自选股")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text="股票代码:").pack(pady=5)
        code_entry = ttk.Entry(dialog)
        code_entry.pack(pady=5)
        
        ttk.Label(dialog, text="股票名称:").pack(pady=5)
        name_entry = ttk.Entry(dialog)
        name_entry.pack(pady=5)
        
        def confirm():
            code = code_entry.get().strip()
            name = name_entry.get().strip()
            if code and name:
                # 保存到文件
                stocks_file = os.path.join(DATA_DIR, "stocks.json")
                stocks = []
                if os.path.exists(stocks_file):
                    with open(stocks_file, 'r', encoding='utf-8') as f:
                        stocks = json.load(f)
                
                stocks.append({"code": code, "name": name})
                with open(stocks_file, 'w', encoding='utf-8') as f:
                    json.dump(stocks, f, ensure_ascii=False, indent=2)
                
                self.load_watch_list()
                self.log(f"➕ 已添加自选股: {name}({code})")
                dialog.destroy()
        
        ttk.Button(dialog, text="添加", command=confirm).pack(pady=10)
    
    def remove_stock(self):
        """删除自选股"""
        selection = self.watch_tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选择要删除的股票")
            return
        
        item = self.watch_tree.item(selection[0])
        code = item['values'][0]
        
        # 从文件删除
        stocks_file = os.path.join(DATA_DIR, "stocks.json")
        if os.path.exists(stocks_file):
            with open(stocks_file, 'r', encoding='utf-8') as f:
                stocks = json.load(f)
            
            stocks = [s for s in stocks if s.get('code') != code]
            
            with open(stocks_file, 'w', encoding='utf-8') as f:
                json.dump(stocks, f, ensure_ascii=False, indent=2)
        
        self.load_watch_list()
        self.log(f"➖ 已删除自选股: {code}")
    
    def show_buy_dialog(self):
        """显示买入对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("买入股票")
        dialog.geometry("350x250")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text="股票代码:").pack(pady=5)
        code_entry = ttk.Entry(dialog)
        code_entry.pack(pady=5)
        
        ttk.Label(dialog, text="股票名称:").pack(pady=5)
        name_entry = ttk.Entry(dialog)
        name_entry.pack(pady=5)
        
        ttk.Label(dialog, text="价格:").pack(pady=5)
        price_entry = ttk.Entry(dialog)
        price_entry.pack(pady=5)
        
        ttk.Label(dialog, text="数量(100的整数倍):").pack(pady=5)
        quantity_entry = ttk.Entry(dialog)
        quantity_entry.pack(pady=5)
        
        result_label = ttk.Label(dialog, text="")
        result_label.pack(pady=10)
        
        def execute_buy():
            code = code_entry.get().strip()
            name = name_entry.get().strip()
            try:
                price = float(price_entry.get().strip())
                quantity = int(quantity_entry.get().strip())
                
                if quantity % 100 != 0:
                    result_label.config(text="❌ 数量必须是100的整数倍")
                    return
                
                result_label.config(text="⏳ 正在执行买入...")
                dialog.update()
                
                # 执行买入
                executor = TradeExecutor()
                success = executor.execute_buy(code, name, price, quantity)
                
                if success:
                    result_label.config(text="✅ 买入成功!")
                    self.log(f"📈 买入成功: {name}({code}) {quantity}股 @ {price}元")
                else:
                    result_label.config(text="❌ 买入失败")
                    
            except ValueError:
                result_label.config(text="❌ 请输入有效的价格和数量")
        
        ttk.Button(dialog, text="执行买入", command=execute_buy).pack(pady=10)
    
    def show_sell_dialog(self):
        """显示卖出对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("卖出股票")
        dialog.geometry("350x250")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text="股票代码:").pack(pady=5)
        code_entry = ttk.Entry(dialog)
        code_entry.pack(pady=5)
        
        ttk.Label(dialog, text="股票名称:").pack(pady=5)
        name_entry = ttk.Entry(dialog)
        name_entry.pack(pady=5)
        
        ttk.Label(dialog, text="价格:").pack(pady=5)
        price_entry = ttk.Entry(dialog)
        price_entry.pack(pady=5)
        
        ttk.Label(dialog, text="数量(全部卖出填0):").pack(pady=5)
        quantity_entry = ttk.Entry(dialog)
        quantity_entry.pack(pady=5)
        
        result_label = ttk.Label(dialog, text="")
        result_label.pack(pady=10)
        
        def execute_sell():
            code = code_entry.get().strip()
            name = name_entry.get().strip()
            try:
                price = float(price_entry.get().strip())
                quantity = int(quantity_entry.get().strip())
                
                result_label.config(text="⏳ 正在执行卖出...")
                dialog.update()
                
                # 执行卖出
                executor = TradeExecutor()
                success = executor.execute_sell(code, name, price, quantity)
                
                if success:
                    result_label.config(text="✅ 卖出成功!")
                    self.log(f"📉 卖出成功: {name}({code}) {quantity}股 @ {price}元")
                else:
                    result_label.config(text="❌ 卖出失败")
                    
            except ValueError:
                result_label.config(text="❌ 请输入有效的价格和数量")
        
        ttk.Button(dialog, text="执行卖出", command=execute_sell).pack(pady=10)
    
    # ========== 监控功能 ==========
    def start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
            messagebox.showinfo("提示", "监控已在运行中")
            return
        
        if not MODULES_AVAILABLE:
            messagebox.showwarning("警告", "交易模块不可用")
            return
        
        self.is_monitoring = True
        self.status_label.config(text="🔴 监控中")
        self.log("🔴 开始自动监控...")
        
        self.monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        self.status_label.config(text="🟢 已停止")
        self.log("🟢 已停止监控")
    
    def monitoring_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                # 检查股票信号
                for stock_code in self.stocks_to_watch:
                    if not self.is_monitoring:
                        break
                    
                    # 获取价格
                    fetcher = TonghuashunFetcher()
                    price_data = fetcher.fetch_price(stock_code)
                    
                    if price_data:
                        # 分析趋势
                        analyzer = TrendAnalyzer()
                        signal = analyzer.analyze(stock_code)
                        
                        if signal.get('buy_signal'):
                            self.log(f"🟢 买入信号: {stock_code}")
                            self.send_notification(f"买入信号: {stock_code}")
                        elif signal.get('sell_signal'):
                            self.log(f"🔴 卖出信号: {stock_code}")
                            self.send_notification(f"卖出信号: {stock_code}")
                
                # 等待下次检查（5分钟）
                for _ in range(300):
                    if not self.is_monitoring:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                self.log(f"⚠️ 监控异常: {e}")
                time.sleep(60)
    
    def send_notification(self, message):
        """发送通知"""
        try:
            send_feishu_message(message)
            self.log(f"📨 通知已发送: {message}")
        except Exception as e:
            self.log(f"⚠️ 通知发送失败: {e}")
    
    # ========== 工具方法 ==========
    def update_time(self):
        """更新时间显示"""
        now = datetime.now()
        self.time_label.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self.update_time)
    
    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        # 写入日志文件
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_message + "\n")
        except:
            pass
        
        # 显示在日志窗口
        try:
            self.log_text.insert(tk.END, log_message + "\n")
            self.log_text.see(tk.END)
        except:
            pass
        
        print(log_message)
    
    def show_about(self):
        """显示关于"""
        messagebox.showinfo("关于", f"{APP_NAME}\n版本: {VERSION}\n\n股票自动化交易系统\n基于 Python + Tkinter")
    
    def quit_app(self):
        """退出应用"""
        if self.is_monitoring:
            if messagebox.askyesno("确认", "监控正在运行，确定要退出吗？"):
                self.stop_monitoring()
                self.root.quit()
        else:
            self.root.quit()


def main():
    """主函数"""
    root = tk.Tk()
    app = StockTraderApp(root)
    root.protocol("WM_DELETE_WINDOW", app.quit_app)
    root.mainloop()


if __name__ == "__main__":
    main()

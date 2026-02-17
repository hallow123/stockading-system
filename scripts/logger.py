#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志模块
负责记录系统运行日志和交易日志
"""

import logging
import os
from datetime import datetime
from pathlib import Path


class Logger:
    """日志管理类"""
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str = "trading_system", log_dir: str = None):
        """获取日志记录器"""
        if name in cls._loggers:
            return cls._loggers[name]
        
        # 创建日志目录
        if log_dir is None:
            base_dir = Path(__file__).parent.parent
            log_dir = base_dir / "logs"
        else:
            log_dir = Path(log_dir)
        
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建日志文件
        log_file = log_dir / f"trading_{datetime.now().strftime('%Y%m%d')}.log"
        
        # 创建logger
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
        # 避免重复添加handler
        if not logger.handlers:
            # 文件handler
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # 控制台handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # 格式化
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def log_trade(cls, trade_info: dict):
        """记录交易日志"""
        logger = cls.get_logger("trade")
        
        trade_type = trade_info.get('type', 'UNKNOWN')
        stock_code = trade_info.get('stock_code', '')
        stock_name = trade_info.get('stock_name', '')
        price = trade_info.get('price', 0)
        quantity = trade_info.get('quantity', 0)
        
        if trade_type == 'BUY':
            logger.info(f"🟢 买入 - {stock_name}({stock_code}) - 价格:{price} - 数量:{quantity}")
        elif trade_type == 'SELL':
            profit_loss = trade_info.get('profit_loss', 0)
            logger.info(f"🔴 卖出 - {stock_name}({stock_code}) - 价格:{price} - 数量:{quantity} - 盈亏:{profit_loss:.2f}")
        else:
            logger.info(f"📝 交易 - {stock_name}({stock_code}) - 类型:{trade_type}")
    
    @classmethod
    def log_signal(cls, signal_type: str, stock_info: dict, reason: str):
        """记录交易信号"""
        logger = cls.get_logger("signal")
        
        stock_code = stock_info.get('code', '')
        stock_name = stock_info.get('name', '')
        
        if signal_type == 'BUY':
            logger.info(f"📈 买入信号 - {stock_name}({stock_code}) - 原因: {reason}")
        elif signal_type == 'SELL':
            logger.info(f"📉 卖出信号 - {stock_name}({stock_code}) - 原因: {reason}")
    
    @classmethod
    def log_error(cls, error_msg: str, exc_info: Exception = None):
        """记录错误日志"""
        logger = cls.get_logger("error")
        
        if exc_info:
            logger.error(f"❌ 错误 - {error_msg}", exc_info=True)
        else:
            logger.error(f"❌ 错误 - {error_msg}")
    
    @classmethod
    def log_warning(cls, warning_msg: str):
        """记录警告日志"""
        logger = cls.get_logger("warning")
        logger.warning(f"⚠️ 警告 - {warning_msg}")
    
    @classmethod
    def log_info(cls, info_msg: str):
        """记录信息日志"""
        logger = cls.get_logger("info")
        logger.info(f"ℹ️ 信息 - {info_msg}")


# 全局日志实例
logger = Logger.get_logger()

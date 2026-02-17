#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
负责加载和管理系统配置
"""

import json
import os
from pathlib import Path


class Config:
    """配置管理类"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化配置"""
        if self._config is None:
            self.load()
    
    def load(self, config_file: str = None):
        """加载配置文件"""
        if config_file is None:
            # 默认使用项目根目录的config.json
            base_dir = Path(__file__).parent.parent
            config_file = base_dir / "config.json"
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            print(f"✅ 配置加载成功: {config_file}")
        except FileNotFoundError:
            print(f"⚠️ 配置文件未找到: {config_file}")
            self._config = self._get_default_config()
        except json.JSONDecodeError as e:
            print(f"⚠️ 配置文件解析错误: {e}")
            self._config = self._get_default_config()
        
        return self._config
    
    def _get_default_config(self) -> dict:
        """获取默认配置"""
        return {
            "system": {
                "name": "股票自动化盯盘交易系统",
                "version": "1.0.0",
                "encoding": "utf-8"
            },
            "trading": {
                "min_quantity": 100,
                "max_position_ratio": 0.5,
                "stop_loss_ratio": 0.05,
                "take_profit_ratio": 0.10,
                "max_holding_days": 12
            },
            "strategy": {
                "ma_periods": [5, 10, 20],
                "buy_conditions": {
                    "ma5_above_ma20": True,
                    "max_daily_loss": -1.0,
                    "volume_ratio_below": 1.0
                }
            },
            "notification": {
                "enable_realtime_alert": True,
                "enable_daily_report": True
            },
            "paths": {
                "data_dir": "data",
                "log_dir": "logs"
            }
        }
    
    def get(self, key: str, default=None):
        """获取配置项"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    def get_trading_config(self) -> dict:
        """获取交易配置"""
        return self._config.get('trading', {})
    
    def get_strategy_config(self) -> dict:
        """获取策略配置"""
        return self._config.get('strategy', {})
    
    def get_notification_config(self) -> dict:
        """获取通知配置"""
        return self._config.get('notification', {})
    
    def get_paths(self) -> dict:
        """获取路径配置"""
        return self._config.get('paths', {})
    
    def save(self, config_file: str = None):
        """保存配置到文件"""
        if config_file is None:
            base_dir = Path(__file__).parent.parent
            config_file = base_dir / "config.json"
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
            print(f"✅ 配置保存成功: {config_file}")
        except Exception as e:
            print(f"❌ 配置保存失败: {e}")


# 全局配置实例
config = Config()

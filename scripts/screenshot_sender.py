#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
屏幕截图并通过飞书发送
"""

import os
import subprocess
import time
from datetime import datetime

SCREENSHOT_PATH = "/tmp/screenshot.png"

def capture_screen():
    """截取屏幕"""
    # 使用macOS screencapture命令
    cmd = ["/usr/sbin/screencapture", "-x", SCREENSHOT_PATH]
    result = subprocess.run(cmd, capture_output=True)
    
    if result.returncode != 0:
        print("❌ 截图失败！")
        print("请确保已授权屏幕录制权限：")
        print("系统设置 → 隐私与安全性 → 屏幕录制")
        return False
    
    print(f"✅ 截图成功: {SCREENSHOT_PATH}")
    return True

def capture_with_apple_script():
    """使用AppleScript截图（保存到桌面）"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H.%M.%S")
    filename = f"截屏{timestamp}.png"
    filepath = os.path.expanduser(f"~/Desktop/{filename}")
    
    # 使用系统快捷键截图 (Cmd+Shift+4)
    script = '''
    tell application "System Events"
        keystroke "4" using {command down, shift down}
    end tell
    '''
    subprocess.run(["osascript", "-e", script])
    time.sleep(1)  # 等待截图完成
    
    # 查找最新的截图文件
    desktop = os.path.expanduser("~/Desktop")
    screenshots = [f for f in os.listdir(desktop) if f.startswith("截屏") and f.endswith(".png")]
    if screenshots:
        latest = sorted(screenshots)[-1]
        return os.path.join(desktop, latest)
    return None

def send_to_feishu(image_path, message="截图"):
    """通过飞书发送图片（使用OpenClaw message工具）"""
    if not os.path.exists(image_path):
        print(f"❌ 文件不存在: {image_path}")
        return False
    
    # 使用OpenClaw的message工具发送
    # 这里生成一个调用message工具的命令
    print(f"📤 发送图片到飞书: {image_path}")
    print(f"📝 消息: {message}")
    
    # 实际发送需要通过OpenClaw API
    # 这里打印命令，用户需要手动执行或在OpenClaw环境中运行
    print(f"\n请在OpenClaw环境中执行:")
    print(f'message action="send" filePath="{image_path}" message="{message}" target="ou_d3af34211d43e662f6d7029317a4c295"')
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("🖥️  屏幕截图 → 飞书发送")
    print("=" * 50)
    
    # 方法1: 直接截图
    print("\n📸 尝试直接截图...")
    if capture_screen():
        send_to_feishu(SCREENSHOT_PATH, "屏幕截图测试")
    else:
        # 方法2: 使用快捷键
        print("\n📸 使用快捷键截图...")
        path = capture_with_apple_script()
        if path:
            send_to_feishu(path, "屏幕截图")

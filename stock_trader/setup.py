"""
py2app 打包配置文件
用于将股票交易系统打包成 macOS App
"""

from setuptools import setup

APP_NAME = 'StockTrader'
APP_VERSION = '1.0'
APP = 'app.py'

setup(
    app=[
        {
            'script': APP,
        },
    ],
    name=APP_NAME,
    version=APP_VERSION,
    description='股票自动交易系统',
    author='StockTrader',
    options={
        'py2app': {
            'argv_emulation': True,
            'includes': [
                'tkinter',
                'tkinter.ttk',
                'tkinter.scrolledtext',
                'json',
                'threading',
                'time',
                'datetime',
                'os',
                'sys',
                'subprocess',
            ],
            'excludes': [
                'matplotlib',
                'numpy',
                'pandas',
                'scipy',
                'pywt',
                'bs4',
                'lxml',
            ],
            'optimize': 2,
            'resources': [
                'data',
                'logs',
            ],
            'plist': {
                'CFBundleName': APP_NAME,
                'CFBundleDisplayName': '股票自动交易',
                'CFBundleIdentifier': 'com.stocktrader.app',
                'CFBundleVersion': '1.0',
                'CFBundleShortVersionString': '1.0',
                'CFBundlePackageType': 'APPL',
                'CFBundleExecutable': APP_NAME,
                'LSMinimumSystemVersion': '10.13',
                'NSPrincipalClass': 'NSApplication',
                'NSHighResolutionCapable': True,
            },
        },
    },
    setup_requires=['py2app'],
)

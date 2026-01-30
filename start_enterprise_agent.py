#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enterprise Agent POC Startup Script
企業 Agent POC 啟動腳本
"""

import os
import sys
import shutil
from pathlib import Path


def check_env_file():
    """Check and create .env file if needed."""
    env_file = Path(".env")
    env_dev_file = Path(".env.dev")

    if not env_file.exists() and env_dev_file.exists():
        print("[INFO] 未找到 .env 檔案，正在從 .env.dev 複製...")
        shutil.copy(env_dev_file, env_file)
        print("[WARNING] 請編輯 .env 檔案設定 API Keys:")
        print("  - GOOGLE_API_KEY: 用於 Gemini API")
        print("  - TAVILY_API_KEY: 用於網路搜尋 (選用)")
        print()


def print_banner():
    """Print startup banner."""
    print("=" * 50)
    print("   企業 Agent POC - 啟動中...")
    print("=" * 50)
    print()
    print("[INFO] 預設帳號:")
    print("  - 管理員: admin / admin123")
    print("  - 使用者: user / user123")
    print()
    print("[INFO] 開啟瀏覽器: http://localhost:5050")
    print()


def start_ui(host="127.0.0.1", port=5050, admin_mode=True):
    """Start the UltraRAG UI server."""
    from ultrarag.client import launch_ui

    mode_str = "管理員模式" if admin_mode else "使用者模式"
    print(f"[INFO] 啟動 UI 服務 ({mode_str})...")
    print()

    launch_ui(host=host, port=port, admin_mode=admin_mode)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="企業 Agent POC 啟動腳本")
    parser.add_argument("--host", default="127.0.0.1", help="伺服器主機 (預設: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5050, help="伺服器埠號 (預設: 5050)")
    parser.add_argument("--user-mode", action="store_true", help="使用者模式 (預設為管理員模式)")

    args = parser.parse_args()

    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)

    # Check environment
    check_env_file()

    # Print banner
    print_banner()

    # Start UI
    start_ui(
        host=args.host,
        port=args.port,
        admin_mode=not args.user_mode
    )


if __name__ == "__main__":
    main()

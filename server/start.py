#!/usr/bin/env python3
"""
Script khởi động Willhaben Crawler Backend
==========================================

Script này giúp khởi động backend một cách dễ dàng với các tùy chọn khác nhau.
"""

import argparse
import sys
import subprocess
import os
from pathlib import Path


def check_dependencies():
    """Kiểm tra dependencies"""
    try:
        import fastapi
        import aiohttp
        import uvicorn
        import bs4
        import fake_useragent
        print("✅ Tất cả dependencies đã được cài đặt")
        return True
    except ImportError as e:
        print(f"❌ Thiếu dependency: {e}")
        print("Hãy chạy: pip install -r requirements.txt")
        return False


def install_dependencies():
    """Cài đặt dependencies"""
    print("📦 Đang cài đặt dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Cài đặt dependencies thành công")
        return True
    except subprocess.CalledProcessError:
        print("❌ Lỗi khi cài đặt dependencies")
        return False


def start_server(host="0.0.0.0", port=8000, reload=False, workers=1):
    """Khởi động server"""
    print(f"🚀 Khởi động Willhaben Crawler Backend...")
    print(f"📍 Server: http://{host}:{port}")
    print(f"🔗 WebSocket: ws://{host}:{port}/ws")
    print(f"🧪 Test page: http://{host}:{port}/test")
    print(f"❤️  Health check: http://{host}:{port}/health")
    print("-" * 50)
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "realtime_backend:app",
        "--host", host,
        "--port", str(port)
    ]
    
    if reload:
        cmd.append("--reload")
    
    if workers > 1:
        cmd.extend(["--workers", str(workers)])
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n🛑 Server đã dừng")


def main():
    """Hàm main"""
    parser = argparse.ArgumentParser(
        description="Willhaben Crawler Backend Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  python start.py                    # Khởi động với cài đặt mặc định
  python start.py --reload           # Khởi động với auto-reload
  python start.py --port 9000        # Khởi động trên port 9000
  python start.py --install          # Cài đặt dependencies trước
  python start.py --check            # Chỉ kiểm tra dependencies
        """
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host để bind server (mặc định: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port để chạy server (mặc định: 8000)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Bật auto-reload khi code thay đổi"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Số worker processes (mặc định: 1)"
    )
    
    parser.add_argument(
        "--install",
        action="store_true",
        help="Cài đặt dependencies trước khi khởi động"
    )
    
    parser.add_argument(
        "--check",
        action="store_true",
        help="Chỉ kiểm tra dependencies và thoát"
    )
    
    args = parser.parse_args()
    
    # Kiểm tra file requirements.txt
    if not Path("requirements.txt").exists():
        print("❌ Không tìm thấy file requirements.txt")
        print("Hãy đảm bảo bạn đang chạy script từ thư mục chứa project")
        sys.exit(1)
    
    # Kiểm tra file realtime_backend.py
    if not Path("realtime_backend.py").exists():
        print("❌ Không tìm thấy file realtime_backend.py")
        print("Hãy đảm bảo bạn đang chạy script từ thư mục chứa project")
        sys.exit(1)
    
    # Cài đặt dependencies nếu được yêu cầu
    if args.install:
        if not install_dependencies():
            sys.exit(1)
    
    # Kiểm tra dependencies
    if not check_dependencies():
        if not args.check:
            print("\n💡 Chạy với --install để tự động cài đặt dependencies")
        sys.exit(1)
    
    # Nếu chỉ kiểm tra dependencies
    if args.check:
        print("✅ Tất cả dependencies đã sẵn sàng!")
        sys.exit(0)
    
    # Khởi động server
    start_server(
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script tổng hợp để hiển thị kết quả tích hợp hệ thống crawl realtime
"""

import requests
import json
import time
from datetime import datetime

def check_server_status():
    """Kiểm tra trạng thái server"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        print(f"❌ Lỗi kết nối server: {e}")
        return None

def get_cars_list():
    """Lấy danh sách xe đã crawl"""
    try:
        response = requests.get("http://localhost:8000/cars", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        print(f"❌ Lỗi lấy danh sách xe: {e}")
        return None

def display_integration_results():
    """Hiển thị kết quả tích hợp"""
    print("🎉 KẾT QUẢ TÍCH HỢP HỆ THỐNG CRAWL REALTIME")
    print("=" * 60)
    
    # Kiểm tra server
    print("\n🔍 KIỂM TRA SERVER:")
    print("-" * 30)
    
    health_data = check_server_status()
    if health_data:
        print("✅ Server đang chạy")
        print(f"   Status: {health_data['status']}")
        print(f"   Crawler running: {health_data['crawler_running']}")
        print(f"   Total seen items: {health_data['total_seen_items']}")
        print(f"   Cars crawled: {health_data['cars_crawled']}")
        print(f"   New items found: {health_data['new_items_found']}")
        print(f"   Uptime: {health_data['uptime_seconds']:.1f} seconds")
        print(f"   Last crawl: {health_data['last_crawl_time']}")
        print(f"   WebSocket connections: {health_data['websocket_connections']}")
        
        # Proxy stats
        proxy = health_data['proxy_rotation']
        print(f"\n🔄 PROXY STATUS:")
        print(f"   Rotation enabled: {proxy['enabled']}")
        print(f"   Total proxies: {proxy['total_proxies']}")
        print(f"   Available proxies: {proxy['available_proxies']}")
        print(f"   Failed proxies: {proxy['failed_proxies']}")
    else:
        print("❌ Server không chạy hoặc không thể kết nối")
        return
    
    # Lấy danh sách xe
    print(f"\n🚗 DANH SÁCH XE ĐÃ CRAWL:")
    print("-" * 30)
    
    cars_data = get_cars_list()
    if cars_data:
        print(f"✅ Tổng số xe: {cars_data['total_cars']}")
        print(f"   Last crawl time: {cars_data['last_crawl_time']}")
        
        if cars_data['cars']:
            print(f"\n📋 Một số ID xe mẫu:")
            for i, car_id in enumerate(cars_data['cars'][:10]):
                print(f"   {i+1}. {car_id}")
            
            if len(cars_data['cars']) > 10:
                print(f"   ... và {len(cars_data['cars']) - 10} xe khác")
    else:
        print("❌ Không thể lấy danh sách xe")
    
    # Hướng dẫn sử dụng
    print(f"\n💡 HƯỚNG DẪN SỬ DỤNG:")
    print("-" * 30)
    print("1. 🌐 Truy cập http://localhost:8000/test để xem giao diện WebSocket")
    print("2. 📡 Kết nối WebSocket tại ws://localhost:8000/ws")
    print("3. 📊 Xem thống kê tại http://localhost:8000/health")
    print("4. 🚗 Xem danh sách xe tại http://localhost:8000/cars")
    print("5. 🔄 Proxy stats tại http://localhost:8000/proxy/stats")
    
    print(f"\n🚀 TÍNH NĂNG ĐÃ TÍCH HỢP:")
    print("-" * 30)
    print("✅ Crawl dữ liệu từ __NEXT_DATA__ (phương pháp mới)")
    print("✅ Fallback về parse HTML (phương pháp cũ)")
    print("✅ Phát hiện xe mới realtime")
    print("✅ Gửi thông báo qua WebSocket")
    print("✅ Proxy rotation với auto-fetch free proxy")
    print("✅ User-agent rotation")
    print("✅ Logging chi tiết")
    print("✅ Thống kê realtime")
    print("✅ Giao diện web test")
    
    print(f"\n📱 TÍCH HỢP ANDROID APP:")
    print("-" * 30)
    print("1. Kết nối WebSocket: ws://<server_ip>:8000/ws")
    print("2. Nhận message type: 'new_listing'")
    print("3. Dữ liệu xe trong field 'data'")
    print("4. Các trường: id, title, price, year, mileage, fuel, brand, model, location, url")
    
    print(f"\n🔄 CÁCH CHẠY:")
    print("-" * 30)
    print("1. Khởi động server: python3 realtime_backend.py")
    print("2. Test WebSocket: python3 test_websocket.py")
    print("3. Xem giao diện: http://localhost:8000/test")
    print("4. API docs: http://localhost:8000/docs")

def main():
    display_integration_results()

if __name__ == "__main__":
    main()

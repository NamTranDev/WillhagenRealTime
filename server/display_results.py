#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script tổng hợp để hiển thị kết quả crawl dữ liệu từ willhaben.at
"""

import json
import sys
from pathlib import Path

def display_results():
    """
    Hiển thị kết quả crawl dữ liệu
    """
    print("🎉 KẾT QUẢ CRAWL DỮ LIỆU TỪ WILLHABEN.AT")
    print("=" * 50)
    
    # Kiểm tra các file đã tạo
    files_to_check = [
        "willhaben_cars_extracted.json",
        "willhaben_cars_detailed.json",
        "willhaben_full_data.json",
        "comprehensive_analysis.json",
        "html_analysis_results.json"
    ]
    
    print("\n📁 Các file đã được tạo:")
    for file_name in files_to_check:
        if Path(file_name).exists():
            file_size = Path(file_name).stat().st_size
            print(f"   ✅ {file_name} ({file_size:,} bytes)")
        else:
            print(f"   ❌ {file_name} (không tồn tại)")
    
    # Đọc và hiển thị dữ liệu chi tiết
    detailed_file = "willhaben_cars_detailed.json"
    if Path(detailed_file).exists():
        print(f"\n🚗 DỮ LIỆU XE ĐÃ CRAWL:")
        print("=" * 50)
        
        with open(detailed_file, 'r', encoding='utf-8') as f:
            cars = json.load(f)
        
        print(f"📊 Tổng số xe: {len(cars)}")
        print(f"📄 File: {detailed_file}")
        
        # Hiển thị một số xe mẫu
        print(f"\n🎯 MỘT SỐ XE MẪU:")
        print("-" * 50)
        
        for i, car in enumerate(cars[:10]):
            print(f"\n{i+1}. {car.get('title', 'N/A')}")
            print(f"   🆔 ID: {car.get('id', 'N/A')}")
            print(f"   🔗 URL: {car.get('url', 'N/A')}")
            print(f"   📊 Status: {car.get('status', {}).get('description', 'N/A')}")
            print(f"   🏷️  Ad Type ID: {car.get('adTypeId', 'N/A')}")
            print(f"   📦 Product ID: {car.get('productId', 'N/A')}")
            
            # Hiển thị các attributes khác nếu có
            other_attrs = []
            for key, value in car.items():
                if key not in ['id', 'title', 'url', 'status', 'adTypeId', 'productId']:
                    other_attrs.append(f"{key}: {value}")
            
            if other_attrs:
                print(f"   📋 Khác: {', '.join(other_attrs[:3])}")
        
        # Thống kê
        print(f"\n📈 THỐNG KÊ:")
        print("-" * 50)
        
        # Đếm các thương hiệu
        brands = {}
        for car in cars:
            title = car.get('title', '')
            if title:
                # Tìm thương hiệu từ title
                brand_keywords = ['Audi', 'BMW', 'Mercedes', 'VW', 'Volkswagen', 'Hyundai', 'Skoda', 'Seat', 'Citroën', 'Volvo', 'Opel', 'Land Rover', 'MINI', 'Fiat', 'Alfa Romeo']
                for brand in brand_keywords:
                    if brand in title:
                        brands[brand] = brands.get(brand, 0) + 1
                        break
        
        if brands:
            print(f"🏭 Thương hiệu phổ biến:")
            for brand, count in sorted(brands.items(), key=lambda x: x[1], reverse=True):
                print(f"   - {brand}: {count} xe")
        
        # Đếm các loại xe
        car_types = {}
        for car in cars:
            title = car.get('title', '')
            if title:
                # Tìm loại xe từ title
                type_keywords = ['SUV', 'Kombi', 'Limousine', 'Cabrio', 'Coupe', 'Hybrid', 'Elektro', 'Plug-in']
                for car_type in type_keywords:
                    if car_type in title:
                        car_types[car_type] = car_types.get(car_type, 0) + 1
        
        if car_types:
            print(f"\n🚙 Loại xe:")
            for car_type, count in sorted(car_types.items(), key=lambda x: x[1], reverse=True):
                print(f"   - {car_type}: {count} xe")
    
    else:
        print(f"\n❌ Không tìm thấy file {detailed_file}")
    
    # Hiển thị hướng dẫn sử dụng
    print(f"\n💡 HƯỚNG DẪN SỬ DỤNG:")
    print("=" * 50)
    print("1. 📄 File willhaben_cars_detailed.json chứa dữ liệu chi tiết của 30 xe")
    print("2. 🔗 Mỗi xe có URL API để lấy thông tin chi tiết hơn")
    print("3. 🆔 Sử dụng ID để theo dõi các xe đã thấy")
    print("4. 🔄 Có thể chạy lại script để crawl dữ liệu mới")
    print("5. 📊 Dữ liệu có thể được tích hợp vào backend realtime")
    
    print(f"\n🚀 CÁCH TÍCH HỢP VÀO BACKEND:")
    print("-" * 50)
    print("1. Sử dụng script này trong realtime_backend.py")
    print("2. Crawl định kỳ để phát hiện xe mới")
    print("3. So sánh ID để tìm xe mới")
    print("4. Gửi thông báo qua WebSocket khi có xe mới")
    print("5. Lưu dữ liệu vào database để theo dõi")

def main():
    display_results()

if __name__ == "__main__":
    main()

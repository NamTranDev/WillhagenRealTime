#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để tìm JSON thực sự trong file RTF
"""

import json
import re
import sys
from pathlib import Path

def find_json_in_rtf(file_path):
    """
    Tìm JSON thực sự trong file RTF
    """
    print(f"🚀 Tìm JSON trong file RTF: {file_path}")
    
    try:
        # Đọc file RTF
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        print(f"✅ Đã đọc file: {len(content)} ký tự")
        
        # Tìm HTML content trong RTF
        html_match = re.search(r'\\f0\\fs28\s*(.*?)(?=\\f0|$)', content, re.DOTALL)
        
        if not html_match:
            print("❌ Không tìm thấy HTML content trong RTF")
            return None
            
        html_content = html_match.group(1)
        print(f"📄 HTML content: {len(html_content)} ký tự")
        
        # Tìm JSON object trong HTML
        # Pattern để tìm JSON object bắt đầu với { và kết thúc với }
        # Tìm từ cuối file lên để lấy JSON lớn nhất
        
        # Tìm tất cả các vị trí có {
        open_braces = [m.start() for m in re.finditer(r'\{', html_content)]
        close_braces = [m.start() for m in re.finditer(r'\}', html_content)]
        
        print(f"🔍 Tìm thấy {len(open_braces)} dấu {{ và {len(close_braces)} dấu }}")
        
        # Tìm JSON object lớn nhất
        largest_json = None
        largest_size = 0
        
        for start in open_braces:
            # Tìm dấu } tương ứng
            brace_count = 0
            end = -1
            
            for i in range(start, len(html_content)):
                if html_content[i] == '{':
                    brace_count += 1
                elif html_content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i
                        break
            
            if end != -1:
                json_candidate = html_content[start:end+1]
                
                # Kiểm tra xem có phải JSON hợp lệ không
                try:
                    json_obj = json.loads(json_candidate)
                    if len(json_candidate) > largest_size:
                        largest_size = len(json_candidate)
                        largest_json = json_obj
                        print(f"✅ Tìm thấy JSON hợp lệ: {len(json_candidate)} ký tự")
                        print(f"🔑 Keys: {list(json_obj.keys())}")
                except json.JSONDecodeError:
                    continue
        
        if largest_json:
            return largest_json
        else:
            print("❌ Không tìm thấy JSON hợp lệ")
            return None
        
    except Exception as e:
        print(f"❌ Lỗi khi đọc file: {e}")
        return None

def search_car_data(json_data):
    """
    Tìm kiếm dữ liệu xe trong JSON
    """
    print("🔍 Tìm kiếm dữ liệu xe trong JSON...")
    
    def search_recursive(obj, path=""):
        """Tìm kiếm đệ quy"""
        results = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                
                # Tìm các key có thể chứa dữ liệu xe
                if key.lower() in ['adverts', 'ads', 'listings', 'results', 'items', 'advert']:
                    if isinstance(value, list):
                        print(f"🎯 Tìm thấy danh sách tại: {current_path} ({len(value)} items)")
                        results.extend(value)
                    elif isinstance(value, dict):
                        print(f"🎯 Tìm thấy object tại: {current_path}")
                        results.append(value)
                
                # Tiếp tục tìm kiếm
                results.extend(search_recursive(value, current_path))
                
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                results.extend(search_recursive(item, f"{path}[{i}]"))
        
        return results
    
    car_data = search_recursive(json_data)
    print(f"📊 Tìm thấy {len(car_data)} potential car data items")
    
    return car_data

def extract_car_info(item):
    """
    Trích xuất thông tin xe từ một item
    """
    car_info = {}
    
    if isinstance(item, dict):
        # Các trường có thể có
        fields_to_extract = [
            'id', 'adId', 'advertId', 'adId',
            'title', 'name', 'headline', 'subject',
            'price', 'priceAmount', 'priceValue',
            'url', 'selfLink', 'link', 'href',
            'description', 'text', 'content',
            'location', 'city', 'region', 'address',
            'year', 'yearOfConstruction', 'constructionYear',
            'mileage', 'km', 'kilometers',
            'fuel', 'fuelType', 'engine',
            'power', 'hp', 'horsepower',
            'transmission', 'gear', 'gearbox',
            'color', 'paint',
            'brand', 'make', 'manufacturer',
            'model', 'type',
            'images', 'pictures', 'photos',
            'dealer', 'seller', 'contact',
            'date', 'created', 'published',
            'condition', 'state'
        ]
        
        for field in fields_to_extract:
            if field in item:
                car_info[field] = item[field]
    
    return car_info

def main():
    if len(sys.argv) != 2:
        print("Usage: python find_json_in_rtf.py <path_to_rtf_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        print(f"❌ File không tồn tại: {file_path}")
        sys.exit(1)
    
    # Tìm JSON trong RTF
    json_data = find_json_in_rtf(file_path)
    if not json_data:
        print("❌ Không tìm thấy dữ liệu JSON hợp lệ")
        sys.exit(1)
    
    # Tìm kiếm dữ liệu xe
    car_data = search_car_data(json_data)
    
    if not car_data:
        print("❌ Không tìm thấy dữ liệu xe nào")
        sys.exit(1)
    
    # Trích xuất thông tin từ các items
    parsed_cars = []
    for i, item in enumerate(car_data[:10]):  # Chỉ lấy 10 đầu tiên
        print(f"\n🚗 Parsing item {i+1}...")
        car_info = extract_car_info(item)
        parsed_cars.append(car_info)
        
        # In thông tin cơ bản
        print(f"   ID: {car_info.get('id', 'N/A')}")
        print(f"   Title: {car_info.get('title', 'N/A')}")
        print(f"   Price: {car_info.get('price', 'N/A')}")
        print(f"   URL: {car_info.get('url', 'N/A')}")
    
    # Lưu kết quả
    output_file = "willhaben_cars_found.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(parsed_cars, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Đã lưu {len(parsed_cars)} xe vào file: {output_file}")
    
    # In tổng kết
    print(f"\n📊 Tổng kết:")
    print(f"   - Tổng số items: {len(car_data)}")
    print(f"   - Đã parse: {len(parsed_cars)}")
    print(f"   - File output: {output_file}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để tìm và trích xuất dữ liệu JSON từ cuối file RTF
"""

import json
import re
import sys
from pathlib import Path

def extract_json_from_end_of_file(file_path):
    """
    Tìm và trích xuất JSON từ cuối file RTF
    """
    print(f"🚀 Tìm JSON từ cuối file: {file_path}")
    
    try:
        # Đọc file RTF
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        print(f"✅ Đã đọc file: {len(content)} ký tự")
        
        # Tìm JSON object lớn ở cuối file
        # Pattern để tìm JSON object bắt đầu với {
        json_pattern = r'\{.*\}'
        
        # Tìm tất cả matches
        matches = re.findall(json_pattern, content, re.DOTALL)
        print(f"🔍 Tìm thấy {len(matches)} potential JSON objects")
        
        # Tìm JSON object lớn nhất (có thể chứa dữ liệu)
        largest_json = None
        largest_size = 0
        
        for i, match in enumerate(matches):
            if len(match) > largest_size:
                largest_size = len(match)
                largest_json = match
                print(f"📊 JSON {i+1}: {len(match)} ký tự")
        
        if largest_json:
            print(f"🎯 JSON lớn nhất: {len(largest_json)} ký tự")
            print(f"📄 Bắt đầu: {largest_json[:200]}...")
            print(f"📄 Kết thúc: ...{largest_json[-200:]}")
            
            # Thử parse JSON
            try:
                json_obj = json.loads(largest_json)
                print(f"✅ JSON hợp lệ!")
                print(f"🔑 Keys: {list(json_obj.keys())}")
                return json_obj
            except json.JSONDecodeError as e:
                print(f"❌ JSON không hợp lệ: {e}")
                
                # Thử tìm JSON hợp lệ bằng cách tìm từ cuối lên
                print("🔄 Thử tìm JSON hợp lệ từ cuối file...")
                
                # Tìm từ cuối file lên
                lines = content.split('\n')
                for i in range(len(lines) - 1, -1, -1):
                    line = lines[i]
                    if '{' in line:
                        # Tìm JSON từ dòng này
                        json_start = content.rfind('{', 0, content.rfind(line))
                        if json_start != -1:
                            potential_json = content[json_start:]
                            try:
                                json_obj = json.loads(potential_json)
                                print(f"✅ Tìm thấy JSON hợp lệ từ dòng {i+1}!")
                                print(f"🔑 Keys: {list(json_obj.keys())}")
                                return json_obj
                            except json.JSONDecodeError:
                                continue
        
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
        print("Usage: python extract_json_from_end.py <path_to_rtf_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        print(f"❌ File không tồn tại: {file_path}")
        sys.exit(1)
    
    # Trích xuất JSON từ cuối file
    json_data = extract_json_from_end_of_file(file_path)
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
    output_file = "willhaben_cars_from_end.json"
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

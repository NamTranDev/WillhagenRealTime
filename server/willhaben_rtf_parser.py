#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để parse file RTF chứa HTML từ willhaben.at và trích xuất dữ liệu JSON
"""

import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

def extract_json_from_rtf(file_path):
    """
    Đọc file RTF và trích xuất dữ liệu JSON từ HTML content
    """
    print(f"🚀 Đọc file RTF: {file_path}")
    
    try:
        # Đọc file RTF
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        print(f"✅ Đã đọc file: {len(content)} ký tự")
        
        # Tìm HTML content trong RTF
        # RTF format thường có HTML được embed trong \f0\fs28
        html_match = re.search(r'\\f0\\fs28\s*(.*?)(?=\\f0|$)', content, re.DOTALL)
        
        if not html_match:
            print("❌ Không tìm thấy HTML content trong RTF")
            return None
            
        html_content = html_match.group(1)
        print(f"📄 HTML content: {len(html_content)} ký tự")
        
        # Parse HTML với BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Tìm tất cả script tags
        script_tags = soup.find_all('script')
        print(f"🔍 Tìm thấy {len(script_tags)} script tags")
        
        # Tìm script tag chứa dữ liệu JSON (thường là script cuối cùng)
        json_data = None
        for i, script in enumerate(script_tags):
            if script.string and script.string.strip():
                script_content = script.string.strip()
                print(f"📜 Script {i+1}: {len(script_content)} ký tự")
                
                # Kiểm tra xem có phải JSON không
                if script_content.startswith('{') and script_content.endswith('}'):
                    try:
                        # Thử parse JSON
                        json_obj = json.loads(script_content)
                        print(f"✅ Tìm thấy JSON data trong script {i+1}")
                        json_data = json_obj
                        break
                    except json.JSONDecodeError:
                        print(f"❌ Script {i+1} không phải JSON hợp lệ")
                        continue
        
        if not json_data:
            print("❌ Không tìm thấy dữ liệu JSON hợp lệ")
            return None
            
        return json_data
        
    except Exception as e:
        print(f"❌ Lỗi khi đọc file: {e}")
        return None

def extract_car_listings(json_data):
    """
    Trích xuất danh sách xe từ dữ liệu JSON
    """
    print("🔍 Tìm kiếm dữ liệu xe trong JSON...")
    
    listings = []
    
    def search_in_dict(data, path=""):
        """Tìm kiếm đệ quy trong dictionary"""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                # Tìm các key có thể chứa danh sách xe
                if key in ['adverts', 'ads', 'listings', 'results', 'items'] and isinstance(value, list):
                    print(f"🎯 Tìm thấy danh sách tại: {current_path}")
                    for item in value:
                        if isinstance(item, dict):
                            listings.append(item)
                
                # Tiếp tục tìm kiếm đệ quy
                search_in_dict(value, current_path)
                
        elif isinstance(data, list):
            for i, item in enumerate(data):
                search_in_dict(item, f"{path}[{i}]")
    
    search_in_dict(json_data)
    
    print(f"📊 Tìm thấy {len(listings)} listings")
    return listings

def parse_car_listing(listing):
    """
    Parse một listing xe để lấy thông tin chi tiết
    """
    car_info = {}
    
    # Các trường có thể có
    possible_fields = [
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
    
    def extract_value(obj, field_names):
        """Tìm giá trị trong object với nhiều tên field có thể"""
        if isinstance(obj, dict):
            for field_name in field_names:
                if field_name in obj:
                    return obj[field_name]
        return None
    
    # Trích xuất từng trường
    for field in possible_fields:
        value = extract_value(listing, [field, field.lower(), field.upper()])
        if value is not None:
            car_info[field] = value
    
    # Tìm kiếm đệ quy trong nested objects
    def deep_search(obj, target_fields):
        """Tìm kiếm sâu trong object"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key.lower() in [f.lower() for f in target_fields]:
                    if key not in car_info:  # Chỉ lấy nếu chưa có
                        car_info[key] = value
                if isinstance(value, (dict, list)):
                    deep_search(value, target_fields)
        elif isinstance(obj, list):
            for item in obj:
                deep_search(item, target_fields)
    
    deep_search(listing, possible_fields)
    
    return car_info

def main():
    if len(sys.argv) != 2:
        print("Usage: python willhaben_rtf_parser.py <path_to_rtf_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        print(f"❌ File không tồn tại: {file_path}")
        sys.exit(1)
    
    # Trích xuất JSON từ RTF
    json_data = extract_json_from_rtf(file_path)
    if not json_data:
        sys.exit(1)
    
    # Trích xuất danh sách xe
    listings = extract_car_listings(json_data)
    
    if not listings:
        print("❌ Không tìm thấy danh sách xe nào")
        sys.exit(1)
    
    # Parse từng listing
    parsed_cars = []
    for i, listing in enumerate(listings[:10]):  # Chỉ lấy 10 đầu tiên để test
        print(f"\n🚗 Parsing listing {i+1}...")
        car_info = parse_car_listing(listing)
        parsed_cars.append(car_info)
        
        # In thông tin cơ bản
        print(f"   ID: {car_info.get('id', 'N/A')}")
        print(f"   Title: {car_info.get('title', 'N/A')}")
        print(f"   Price: {car_info.get('price', 'N/A')}")
        print(f"   URL: {car_info.get('url', 'N/A')}")
    
    # Lưu kết quả
    output_file = "willhaben_cars.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(parsed_cars, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Đã lưu {len(parsed_cars)} xe vào file: {output_file}")
    
    # In tổng kết
    print(f"\n📊 Tổng kết:")
    print(f"   - Tổng số listings: {len(listings)}")
    print(f"   - Đã parse: {len(parsed_cars)}")
    print(f"   - File output: {output_file}")

if __name__ == "__main__":
    main()

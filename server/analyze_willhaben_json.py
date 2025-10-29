#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để phân tích chi tiết JSON từ willhaben.at
"""

import json
import re
import sys
from pathlib import Path
import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup

def crawl_willhaben_data():
    """
    Crawl dữ liệu từ willhaben.at
    """
    print("🚀 Crawl dữ liệu từ willhaben.at...")
    
    try:
        ua = UserAgent()
        headers = {
            'User-Agent': ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        url = "https://www.willhaben.at/iad/gebrauchtwagen/auto/gebrauchtwagenboerse"
        
        response = requests.get(url, headers=headers, timeout=30)
        print(f"✅ Status code: {response.status_code}")
        print(f"📄 Content length: {len(response.text)}")
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tìm __NEXT_DATA__
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        if next_data_script:
            print("✅ Tìm thấy __NEXT_DATA__ script!")
            try:
                json_data = json.loads(next_data_script.string)
                print(f"🔑 Keys: {list(json_data.keys())}")
                return json_data
            except json.JSONDecodeError as e:
                print(f"❌ Lỗi parse JSON: {e}")
                return None
        else:
            print("❌ Không tìm thấy __NEXT_DATA__ script")
            return None
        
    except Exception as e:
        print(f"❌ Lỗi khi crawl: {e}")
        return None

def analyze_json_structure(json_data, path="", max_depth=5):
    """
    Phân tích cấu trúc JSON để tìm dữ liệu xe
    """
    if max_depth <= 0:
        return
    
    if isinstance(json_data, dict):
        for key, value in json_data.items():
            current_path = f"{path}.{key}" if path else key
            
            # In thông tin về key
            if isinstance(value, dict):
                print(f"📁 {current_path}: dict với {len(value)} keys")
                if max_depth > 1:
                    analyze_json_structure(value, current_path, max_depth - 1)
            elif isinstance(value, list):
                print(f"📋 {current_path}: list với {len(value)} items")
                if max_depth > 1 and len(value) > 0:
                    print(f"   Item đầu tiên: {type(value[0])}")
                    if isinstance(value[0], dict):
                        print(f"   Keys của item đầu tiên: {list(value[0].keys())[:10]}")
            else:
                print(f"📄 {current_path}: {type(value).__name__} = {str(value)[:100]}")
                
            # Tìm kiếm các key có thể chứa dữ liệu xe
            if key.lower() in ['adverts', 'ads', 'listings', 'results', 'items', 'advert', 'cars', 'vehicles']:
                print(f"🎯 Tìm thấy key liên quan đến xe: {current_path}")
                if isinstance(value, list) and len(value) > 0:
                    print(f"   Số lượng items: {len(value)}")
                    if isinstance(value[0], dict):
                        print(f"   Keys của item đầu tiên: {list(value[0].keys())}")
                elif isinstance(value, dict):
                    print(f"   Keys: {list(value.keys())}")

def search_car_data_recursive(json_data, path=""):
    """
    Tìm kiếm đệ quy dữ liệu xe trong JSON
    """
    results = []
    
    if isinstance(json_data, dict):
        for key, value in json_data.items():
            current_path = f"{path}.{key}" if path else key
            
            # Tìm các key có thể chứa dữ liệu xe
            if key.lower() in ['adverts', 'ads', 'listings', 'results', 'items', 'advert', 'cars', 'vehicles']:
                if isinstance(value, list):
                    print(f"🎯 Tìm thấy danh sách tại: {current_path} ({len(value)} items)")
                    results.extend(value)
                elif isinstance(value, dict):
                    print(f"🎯 Tìm thấy object tại: {current_path}")
                    results.append(value)
            
            # Tiếp tục tìm kiếm
            results.extend(search_car_data_recursive(value, current_path))
            
    elif isinstance(json_data, list):
        for i, item in enumerate(json_data):
            results.extend(search_car_data_recursive(item, f"{path}[{i}]"))
    
    return results

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
        
        # Tìm kiếm đệ quy trong nested objects
        def deep_search(obj, target_fields):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key.lower() in [f.lower() for f in target_fields]:
                        if key not in car_info:
                            car_info[key] = value
                    if isinstance(value, (dict, list)):
                        deep_search(value, target_fields)
            elif isinstance(obj, list):
                for item in obj:
                    deep_search(item, target_fields)
        
        deep_search(item, fields_to_extract)
    
    return car_info

def main():
    print("🚀 Phân tích chi tiết JSON từ willhaben.at")
    
    # Crawl dữ liệu
    json_data = crawl_willhaben_data()
    if not json_data:
        print("❌ Không thể crawl dữ liệu")
        sys.exit(1)
    
    # Phân tích cấu trúc JSON
    print(f"\n📊 Phân tích cấu trúc JSON:")
    analyze_json_structure(json_data)
    
    # Tìm kiếm dữ liệu xe
    print(f"\n🔍 Tìm kiếm dữ liệu xe:")
    car_data = search_car_data_recursive(json_data)
    
    if not car_data:
        print("❌ Không tìm thấy dữ liệu xe")
        
        # Lưu toàn bộ JSON để phân tích thêm
        output_file = "willhaben_full_data.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        print(f"💾 Đã lưu toàn bộ dữ liệu vào: {output_file}")
        sys.exit(1)
    
    print(f"📊 Tìm thấy {len(car_data)} potential car data items")
    
    # Parse thông tin xe
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
    output_file = "willhaben_cars_analyzed.json"
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

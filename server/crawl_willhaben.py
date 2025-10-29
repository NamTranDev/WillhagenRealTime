#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để crawl dữ liệu xe từ willhaben.at bằng headless browser
"""

import json
import re
import time
import sys
from pathlib import Path
from bs4 import BeautifulSoup

def crawl_with_requests():
    """
    Thử crawl bằng requests trước
    """
    print("🚀 Thử crawl bằng requests...")
    
    try:
        import requests
        from fake_useragent import UserAgent
        
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
        
        # Tìm kiếm JSON trong response
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tìm script tags
        script_tags = soup.find_all('script')
        print(f"🔍 Tìm thấy {len(script_tags)} script tags")
        
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
        else:
            print("❌ Không tìm thấy __NEXT_DATA__ script")
        
        # Tìm kiếm các script khác
        for i, script in enumerate(script_tags):
            if script.string and script.string.strip():
                script_content = script.string.strip()
                if script_content.startswith('{') and script_content.endswith('}'):
                    try:
                        json_obj = json.loads(script_content)
                        print(f"✅ Tìm thấy JSON trong script {i+1}")
                        print(f"🔑 Keys: {list(json_obj.keys())}")
                        return json_obj
                    except json.JSONDecodeError:
                        continue
        
        return None
        
    except ImportError:
        print("❌ Cần cài đặt requests: pip install requests")
        return None
    except Exception as e:
        print(f"❌ Lỗi khi crawl: {e}")
        return None

def crawl_with_selenium():
    """
    Crawl bằng Selenium (nếu có)
    """
    print("🚀 Thử crawl bằng Selenium...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Khởi tạo driver
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # Load trang web
            url = "https://www.willhaben.at/iad/gebrauchtwagen/auto/gebrauchtwagenboerse"
            print(f"🌐 Loading: {url}")
            driver.get(url)
            
            # Đợi trang load
            print("⏳ Đợi trang load...")
            time.sleep(5)
            
            # Tìm kiếm dữ liệu JSON
            page_source = driver.page_source
            print(f"📄 Page source length: {len(page_source)}")
            
            # Parse HTML
            soup = BeautifulSoup(page_source, 'html.parser')
            
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
            else:
                print("❌ Không tìm thấy __NEXT_DATA__ script")
            
            # Tìm kiếm các script khác
            script_tags = soup.find_all('script')
            print(f"🔍 Tìm thấy {len(script_tags)} script tags")
            
            for i, script in enumerate(script_tags):
                if script.string and script.string.strip():
                    script_content = script.string.strip()
                    if script_content.startswith('{') and script_content.endswith('}'):
                        try:
                            json_obj = json.loads(script_content)
                            print(f"✅ Tìm thấy JSON trong script {i+1}")
                            print(f"🔑 Keys: {list(json_obj.keys())}")
                            return json_obj
                        except json.JSONDecodeError:
                            continue
            
            return None
            
        finally:
            driver.quit()
            
    except ImportError:
        print("❌ Cần cài đặt Selenium: pip install selenium")
        return None
    except Exception as e:
        print(f"❌ Lỗi khi crawl với Selenium: {e}")
        return None

def extract_car_data(json_data):
    """
    Trích xuất dữ liệu xe từ JSON
    """
    print("🔍 Trích xuất dữ liệu xe từ JSON...")
    
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

def parse_car_info(item):
    """
    Parse thông tin xe từ một item
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
    print("🚀 Crawl dữ liệu xe từ willhaben.at")
    
    # Thử crawl bằng requests trước
    json_data = crawl_with_requests()
    
    # Nếu không thành công, thử Selenium
    if not json_data:
        print("\n🔄 Thử Selenium...")
        json_data = crawl_with_selenium()
    
    if not json_data:
        print("❌ Không thể crawl dữ liệu")
        sys.exit(1)
    
    # Trích xuất dữ liệu xe
    car_data = extract_car_data(json_data)
    
    if not car_data:
        print("❌ Không tìm thấy dữ liệu xe")
        sys.exit(1)
    
    # Parse thông tin xe
    parsed_cars = []
    for i, item in enumerate(car_data[:10]):  # Chỉ lấy 10 đầu tiên
        print(f"\n🚗 Parsing item {i+1}...")
        car_info = parse_car_info(item)
        parsed_cars.append(car_info)
        
        # In thông tin cơ bản
        print(f"   ID: {car_info.get('id', 'N/A')}")
        print(f"   Title: {car_info.get('title', 'N/A')}")
        print(f"   Price: {car_info.get('price', 'N/A')}")
        print(f"   URL: {car_info.get('url', 'N/A')}")
    
    # Lưu kết quả
    output_file = "willhaben_cars_crawled.json"
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

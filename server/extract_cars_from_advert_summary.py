#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để trích xuất dữ liệu xe từ advertSummaryList
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

def extract_car_data_from_advert_summary(json_data):
    """
    Trích xuất dữ liệu xe từ advertSummaryList
    """
    print("🔍 Trích xuất dữ liệu xe từ advertSummaryList...")
    
    try:
        # Đi đến advertSummaryList
        advert_summary_list = json_data['props']['pageProps']['searchResult']['advertSummaryList']['advertSummary']
        print(f"📊 Tìm thấy {len(advert_summary_list)} xe trong advertSummaryList")
        
        cars = []
        for i, advert in enumerate(advert_summary_list):
            print(f"\n🚗 Xe {i+1}:")
            
            car_info = {}
            
            # Trích xuất các trường cơ bản
            if 'adId' in advert:
                car_info['id'] = advert['adId']
                print(f"   ID: {advert['adId']}")
            
            if 'title' in advert:
                car_info['title'] = advert['title']
                print(f"   Title: {advert['title']}")
            
            if 'price' in advert:
                car_info['price'] = advert['price']
                print(f"   Price: {advert['price']}")
            
            if 'selfLink' in advert:
                car_info['url'] = advert['selfLink']
                print(f"   URL: {advert['selfLink']}")
            
            # Trích xuất thông tin chi tiết từ các trường khác
            if 'description' in advert:
                car_info['description'] = advert['description']
            
            if 'location' in advert:
                car_info['location'] = advert['location']
            
            if 'images' in advert:
                car_info['images'] = advert['images']
            
            if 'properties' in advert:
                car_info['properties'] = advert['properties']
            
            if 'advertType' in advert:
                car_info['advertType'] = advert['advertType']
            
            if 'dealer' in advert:
                car_info['dealer'] = advert['dealer']
            
            if 'date' in advert:
                car_info['date'] = advert['date']
            
            if 'isNew' in advert:
                car_info['isNew'] = advert['isNew']
            
            if 'isTopAd' in advert:
                car_info['isTopAd'] = advert['isTopAd']
            
            if 'isHighlighted' in advert:
                car_info['isHighlighted'] = advert['isHighlighted']
            
            # In tất cả các keys có sẵn để debug
            print(f"   Tất cả keys: {list(advert.keys())}")
            
            cars.append(car_info)
        
        return cars
        
    except KeyError as e:
        print(f"❌ Không tìm thấy key: {e}")
        return None
    except Exception as e:
        print(f"❌ Lỗi khi trích xuất dữ liệu: {e}")
        return None

def parse_car_properties(car_info):
    """
    Parse thông tin chi tiết từ properties
    """
    if 'properties' in car_info and car_info['properties']:
        properties = car_info['properties']
        
        # Trích xuất thông tin từ properties
        for prop in properties:
            if 'name' in prop and 'value' in prop:
                prop_name = prop['name']
                prop_value = prop['value']
                
                # Map các properties phổ biến
                if 'year' in prop_name.lower() or 'jahr' in prop_name.lower():
                    car_info['year'] = prop_value
                elif 'km' in prop_name.lower() or 'kilometer' in prop_name.lower():
                    car_info['mileage'] = prop_value
                elif 'fuel' in prop_name.lower() or 'kraftstoff' in prop_name.lower():
                    car_info['fuel'] = prop_value
                elif 'power' in prop_name.lower() or 'leistung' in prop_name.lower():
                    car_info['power'] = prop_value
                elif 'transmission' in prop_name.lower() or 'getriebe' in prop_name.lower():
                    car_info['transmission'] = prop_value
                elif 'color' in prop_name.lower() or 'farbe' in prop_name.lower():
                    car_info['color'] = prop_value
                elif 'brand' in prop_name.lower() or 'marke' in prop_name.lower():
                    car_info['brand'] = prop_value
                elif 'model' in prop_name.lower() or 'modell' in prop_name.lower():
                    car_info['model'] = prop_value

def main():
    print("🚀 Trích xuất dữ liệu xe từ willhaben.at")
    
    # Crawl dữ liệu
    json_data = crawl_willhaben_data()
    if not json_data:
        print("❌ Không thể crawl dữ liệu")
        sys.exit(1)
    
    # Trích xuất dữ liệu xe
    cars = extract_car_data_from_advert_summary(json_data)
    if not cars:
        print("❌ Không thể trích xuất dữ liệu xe")
        sys.exit(1)
    
    # Parse thông tin chi tiết
    print(f"\n🔍 Parse thông tin chi tiết:")
    for car in cars:
        parse_car_properties(car)
    
    # Lưu kết quả
    output_file = "willhaben_cars_extracted.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cars, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Đã lưu {len(cars)} xe vào file: {output_file}")
    
    # In tổng kết
    print(f"\n📊 Tổng kết:")
    print(f"   - Tổng số xe: {len(cars)}")
    print(f"   - File output: {output_file}")
    
    # In một số xe mẫu
    print(f"\n🎯 Một số xe mẫu:")
    for i, car in enumerate(cars[:5]):
        print(f"   {i+1}. {car.get('title', 'N/A')} - {car.get('price', 'N/A')}")

if __name__ == "__main__":
    main()

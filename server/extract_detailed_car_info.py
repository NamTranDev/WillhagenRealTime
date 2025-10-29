#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script cuối cùng để trích xuất thông tin chi tiết từ willhaben.at
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

def extract_detailed_car_info(json_data):
    """
    Trích xuất thông tin chi tiết từ advertSummaryList
    """
    print("🔍 Trích xuất thông tin chi tiết từ advertSummaryList...")
    
    try:
        # Đi đến advertSummaryList
        advert_summary_list = json_data['props']['pageProps']['searchResult']['advertSummaryList']['advertSummary']
        print(f"📊 Tìm thấy {len(advert_summary_list)} xe trong advertSummaryList")
        
        cars = []
        for i, advert in enumerate(advert_summary_list):
            print(f"\n🚗 Xe {i+1}:")
            
            car_info = {}
            
            # Trích xuất các trường cơ bản
            if 'id' in advert:
                car_info['id'] = advert['id']
                print(f"   ID: {advert['id']}")
            
            if 'description' in advert:
                car_info['title'] = advert['description']
                print(f"   Title: {advert['description']}")
            
            if 'selfLink' in advert:
                car_info['url'] = advert['selfLink']
                print(f"   URL: {advert['selfLink']}")
            
            # Trích xuất thông tin từ attributes
            if 'attributes' in advert and advert['attributes']:
                attributes = advert['attributes']
                print(f"   Attributes: {len(attributes)} items")
                
                for attr in attributes:
                    if 'name' in attr and 'value' in attr:
                        attr_name = attr['name']
                        attr_value = attr['value']
                        
                        # Map các attributes phổ biến
                        if 'price' in attr_name.lower() or 'preis' in attr_name.lower():
                            car_info['price'] = attr_value
                            print(f"   Price: {attr_value}")
                        elif 'year' in attr_name.lower() or 'jahr' in attr_name.lower():
                            car_info['year'] = attr_value
                            print(f"   Year: {attr_value}")
                        elif 'km' in attr_name.lower() or 'kilometer' in attr_name.lower():
                            car_info['mileage'] = attr_value
                            print(f"   Mileage: {attr_value}")
                        elif 'fuel' in attr_name.lower() or 'kraftstoff' in attr_name.lower():
                            car_info['fuel'] = attr_value
                            print(f"   Fuel: {attr_value}")
                        elif 'power' in attr_name.lower() or 'leistung' in attr_name.lower():
                            car_info['power'] = attr_value
                            print(f"   Power: {attr_value}")
                        elif 'transmission' in attr_name.lower() or 'getriebe' in attr_name.lower():
                            car_info['transmission'] = attr_value
                            print(f"   Transmission: {attr_value}")
                        elif 'color' in attr_name.lower() or 'farbe' in attr_name.lower():
                            car_info['color'] = attr_value
                            print(f"   Color: {attr_value}")
                        elif 'brand' in attr_name.lower() or 'marke' in attr_name.lower():
                            car_info['brand'] = attr_value
                            print(f"   Brand: {attr_value}")
                        elif 'model' in attr_name.lower() or 'modell' in attr_name.lower():
                            car_info['model'] = attr_value
                            print(f"   Model: {attr_value}")
                        elif 'location' in attr_name.lower() or 'standort' in attr_name.lower():
                            car_info['location'] = attr_value
                            print(f"   Location: {attr_value}")
                        else:
                            # Lưu tất cả các attributes khác
                            car_info[f'attr_{attr_name}'] = attr_value
            
            # Trích xuất thông tin từ teaserAttributes
            if 'teaserAttributes' in advert and advert['teaserAttributes']:
                teaser_attrs = advert['teaserAttributes']
                print(f"   Teaser Attributes: {len(teaser_attrs)} items")
                
                for teaser in teaser_attrs:
                    if 'name' in teaser and 'value' in teaser:
                        teaser_name = teaser['name']
                        teaser_value = teaser['value']
                        
                        # Map các teaser attributes
                        if 'price' in teaser_name.lower() or 'preis' in teaser_name.lower():
                            if 'price' not in car_info:  # Chỉ lấy nếu chưa có
                                car_info['price'] = teaser_value
                                print(f"   Price (teaser): {teaser_value}")
                        elif 'year' in teaser_name.lower() or 'jahr' in teaser_name.lower():
                            if 'year' not in car_info:
                                car_info['year'] = teaser_value
                                print(f"   Year (teaser): {teaser_value}")
                        elif 'km' in teaser_name.lower() or 'kilometer' in teaser_name.lower():
                            if 'mileage' not in car_info:
                                car_info['mileage'] = teaser_value
                                print(f"   Mileage (teaser): {teaser_value}")
            
            # Trích xuất thông tin từ advertiserInfo
            if 'advertiserInfo' in advert and advert['advertiserInfo']:
                advertiser = advert['advertiserInfo']
                if 'name' in advertiser:
                    car_info['dealer'] = advertiser['name']
                    print(f"   Dealer: {advertiser['name']}")
                if 'location' in advertiser:
                    car_info['dealer_location'] = advertiser['location']
                    print(f"   Dealer Location: {advertiser['location']}")
            
            # Trích xuất thông tin từ advertImageList
            if 'advertImageList' in advert and advert['advertImageList']:
                images = advert['advertImageList']
                if isinstance(images, list) and len(images) > 0:
                    car_info['images'] = images
                    print(f"   Images: {len(images)} items")
            
            # Trích xuất thông tin từ advertStatus
            if 'advertStatus' in advert:
                car_info['status'] = advert['advertStatus']
                print(f"   Status: {advert['advertStatus']}")
            
            # Trích xuất thông tin từ adTypeId
            if 'adTypeId' in advert:
                car_info['adTypeId'] = advert['adTypeId']
                print(f"   Ad Type ID: {advert['adTypeId']}")
            
            # Trích xuất thông tin từ productId
            if 'productId' in advert:
                car_info['productId'] = advert['productId']
                print(f"   Product ID: {advert['productId']}")
            
            cars.append(car_info)
        
        return cars
        
    except KeyError as e:
        print(f"❌ Không tìm thấy key: {e}")
        return None
    except Exception as e:
        print(f"❌ Lỗi khi trích xuất dữ liệu: {e}")
        return None

def main():
    print("🚀 Trích xuất thông tin chi tiết từ willhaben.at")
    
    # Crawl dữ liệu
    json_data = crawl_willhaben_data()
    if not json_data:
        print("❌ Không thể crawl dữ liệu")
        sys.exit(1)
    
    # Trích xuất thông tin chi tiết
    cars = extract_detailed_car_info(json_data)
    if not cars:
        print("❌ Không thể trích xuất thông tin xe")
        sys.exit(1)
    
    # Lưu kết quả
    output_file = "willhaben_cars_detailed.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cars, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Đã lưu {len(cars)} xe vào file: {output_file}")
    
    # In tổng kết
    print(f"\n📊 Tổng kết:")
    print(f"   - Tổng số xe: {len(cars)}")
    print(f"   - File output: {output_file}")
    
    # In một số xe mẫu với thông tin chi tiết
    print(f"\n🎯 Một số xe mẫu với thông tin chi tiết:")
    for i, car in enumerate(cars[:5]):
        print(f"\n   {i+1}. {car.get('title', 'N/A')}")
        print(f"      - ID: {car.get('id', 'N/A')}")
        print(f"      - Price: {car.get('price', 'N/A')}")
        print(f"      - Year: {car.get('year', 'N/A')}")
        print(f"      - Mileage: {car.get('mileage', 'N/A')}")
        print(f"      - Fuel: {car.get('fuel', 'N/A')}")
        print(f"      - Location: {car.get('location', 'N/A')}")
        print(f"      - Dealer: {car.get('dealer', 'N/A')}")
        print(f"      - URL: {car.get('url', 'N/A')}")

if __name__ == "__main__":
    main()

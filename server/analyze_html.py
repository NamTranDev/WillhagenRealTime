#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để phân tích chi tiết HTML và tìm cách trích xuất dữ liệu
"""

import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

def analyze_html_structure(file_path):
    """
    Phân tích cấu trúc HTML để tìm dữ liệu
    """
    print(f"🚀 Phân tích HTML từ file: {file_path}")
    
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
        
        # Parse HTML với BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Phân tích các elements chính
        print(f"\n📊 Phân tích cấu trúc HTML:")
        print(f"   - Title: {soup.title.string if soup.title else 'N/A'}")
        print(f"   - Meta description: {soup.find('meta', attrs={'name': 'description'}).get('content') if soup.find('meta', attrs={'name': 'description'}) else 'N/A'}")
        
        # Tìm các elements có thể chứa dữ liệu xe
        print(f"\n🔍 Tìm kiếm elements chứa dữ liệu:")
        
        # 1. Tìm các div có class liên quan đến xe
        car_divs = soup.find_all('div', class_=re.compile(r'(car|auto|vehicle|advert|listing)', re.I))
        print(f"   - Divs liên quan đến xe: {len(car_divs)}")
        
        # 2. Tìm các elements có data attributes
        data_elements = soup.find_all(attrs={'data-testid': True})
        print(f"   - Elements với data-testid: {len(data_elements)}")
        
        # 3. Tìm các elements có id liên quan
        id_elements = soup.find_all(id=re.compile(r'(car|auto|vehicle|advert|listing)', re.I))
        print(f"   - Elements với id liên quan: {len(id_elements)}")
        
        # 4. Tìm các script tags
        script_tags = soup.find_all('script')
        print(f"   - Script tags: {len(script_tags)}")
        
        # 5. Tìm các elements có text chứa từ khóa xe
        car_keywords = ['BMW', 'Audi', 'Mercedes', 'Volkswagen', 'Opel', 'Ford', '€', 'km', 'Jahr']
        for keyword in car_keywords:
            elements = soup.find_all(text=re.compile(keyword, re.I))
            if elements:
                print(f"   - Elements chứa '{keyword}': {len(elements)}")
        
        return soup
        
    except Exception as e:
        print(f"❌ Lỗi khi phân tích HTML: {e}")
        return None

def extract_data_from_elements(soup):
    """
    Trích xuất dữ liệu từ các HTML elements
    """
    print(f"\n🔍 Trích xuất dữ liệu từ HTML elements:")
    
    extracted_data = []
    
    # 1. Tìm các elements có thể chứa thông tin xe
    potential_car_elements = []
    
    # Tìm các div có class chứa từ khóa liên quan
    for div in soup.find_all('div'):
        class_name = ' '.join(div.get('class', []))
        if any(keyword in class_name.lower() for keyword in ['car', 'auto', 'vehicle', 'advert', 'listing', 'item']):
            potential_car_elements.append(div)
    
    print(f"   - Tìm thấy {len(potential_car_elements)} potential car elements")
    
    # 2. Trích xuất thông tin từ mỗi element
    for i, element in enumerate(potential_car_elements[:10]):  # Chỉ lấy 10 đầu tiên
        print(f"\n🚗 Element {i+1}:")
        
        car_data = {}
        
        # Trích xuất text content
        text_content = element.get_text(strip=True)
        if text_content:
            car_data['text'] = text_content[:200] + "..." if len(text_content) > 200 else text_content
        
        # Trích xuất attributes
        car_data['attributes'] = dict(element.attrs)
        
        # Tìm các elements con có thể chứa thông tin cụ thể
        title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if title_elem:
            car_data['title'] = title_elem.get_text(strip=True)
        
        price_elem = element.find(text=re.compile(r'€\s*\d+'))
        if price_elem:
            car_data['price'] = price_elem.strip()
        
        # Tìm links
        links = element.find_all('a', href=True)
        if links:
            car_data['links'] = [link['href'] for link in links]
        
        # Tìm images
        images = element.find_all('img', src=True)
        if images:
            car_data['images'] = [img['src'] for img in images]
        
        extracted_data.append(car_data)
        
        # In thông tin cơ bản
        print(f"   - Title: {car_data.get('title', 'N/A')}")
        print(f"   - Price: {car_data.get('price', 'N/A')}")
        print(f"   - Text: {car_data.get('text', 'N/A')[:100]}...")
    
    return extracted_data

def search_for_json_patterns(html_content):
    """
    Tìm kiếm các pattern JSON có thể có trong HTML
    """
    print(f"\n🔍 Tìm kiếm JSON patterns trong HTML:")
    
    # Các pattern có thể chứa JSON
    patterns = [
        r'window\.__NEXT_DATA__\s*=\s*(\{.*?\});',
        r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});',
        r'window\.__DATA__\s*=\s*(\{.*?\});',
        r'var\s+data\s*=\s*(\{.*?\});',
        r'const\s+data\s*=\s*(\{.*?\});',
        r'let\s+data\s*=\s*(\{.*?\});',
        r'data:\s*(\{.*?\})',
        r'"data":\s*(\{.*?\})',
        r'"adverts":\s*(\[.*?\])',
        r'"ads":\s*(\[.*?\])',
        r'"listings":\s*(\[.*?\])',
        r'"results":\s*(\[.*?\])',
    ]
    
    found_patterns = []
    
    for i, pattern in enumerate(patterns):
        matches = re.findall(pattern, html_content, re.DOTALL)
        if matches:
            print(f"   Pattern {i+1}: Tìm thấy {len(matches)} matches")
            for j, match in enumerate(matches[:3]):  # Chỉ lấy 3 đầu tiên
                print(f"     Match {j+1}: {len(match)} ký tự")
                print(f"     Bắt đầu: {match[:100]}...")
                
                # Thử parse JSON
                try:
                    json_obj = json.loads(match)
                    print(f"     ✅ JSON hợp lệ!")
                    print(f"     Keys: {list(json_obj.keys())[:5]}...")
                    found_patterns.append(json_obj)
                except json.JSONDecodeError:
                    print(f"     ❌ Không phải JSON hợp lệ")
        else:
            print(f"   Pattern {i+1}: Không tìm thấy")
    
    return found_patterns

def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze_html.py <path_to_rtf_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        print(f"❌ File không tồn tại: {file_path}")
        sys.exit(1)
    
    # Phân tích cấu trúc HTML
    soup = analyze_html_structure(file_path)
    if not soup:
        sys.exit(1)
    
    # Trích xuất dữ liệu từ elements
    extracted_data = extract_data_from_elements(soup)
    
    # Tìm kiếm JSON patterns
    html_content = str(soup)
    json_patterns = search_for_json_patterns(html_content)
    
    # Lưu kết quả
    results = {
        'extracted_data': extracted_data,
        'json_patterns': json_patterns,
        'summary': {
            'total_elements': len(extracted_data),
            'json_found': len(json_patterns)
        }
    }
    
    output_file = "html_analysis_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Đã lưu kết quả phân tích vào file: {output_file}")
    
    # In tổng kết
    print(f"\n📊 Tổng kết phân tích:")
    print(f"   - Elements được trích xuất: {len(extracted_data)}")
    print(f"   - JSON patterns tìm thấy: {len(json_patterns)}")
    print(f"   - File output: {output_file}")
    
    if extracted_data:
        print(f"\n🎯 Một số dữ liệu được trích xuất:")
        for i, data in enumerate(extracted_data[:3]):
            print(f"   {i+1}. {data.get('title', 'N/A')} - {data.get('price', 'N/A')}")

if __name__ == "__main__":
    main()

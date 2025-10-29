#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script tổng hợp để tìm tất cả các pattern có thể có trong HTML
"""

import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

def comprehensive_html_analysis(file_path):
    """
    Phân tích toàn diện HTML để tìm mọi pattern có thể có
    """
    print(f"🚀 Phân tích toàn diện HTML từ file: {file_path}")
    
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
        
        # 1. Phân tích meta tags
        print(f"\n📊 Phân tích Meta Tags:")
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            if meta.get('name') == 'description':
                print(f"   - Description: {meta.get('content', 'N/A')}")
            elif meta.get('property') == 'og:title':
                print(f"   - OG Title: {meta.get('content', 'N/A')}")
            elif meta.get('property') == 'og:description':
                print(f"   - OG Description: {meta.get('content', 'N/A')}")
        
        # 2. Tìm kiếm tất cả text chứa từ khóa liên quan
        print(f"\n🔍 Tìm kiếm từ khóa liên quan:")
        keywords = ['BMW', 'Audi', 'Mercedes', 'Volkswagen', 'Opel', 'Ford', '€', 'km', 'Jahr', 'Gebrauchtwagen']
        for keyword in keywords:
            count = html_content.count(keyword)
            if count > 0:
                print(f"   - '{keyword}': {count} lần xuất hiện")
        
        # 3. Tìm kiếm các pattern số (có thể là giá, năm, km)
        print(f"\n💰 Tìm kiếm pattern số:")
        price_patterns = [
            r'€\s*\d+[.,]\d+',
            r'€\s*\d+',
            r'\d+[.,]\d+\s*€',
            r'\d+\s*€'
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                print(f"   - Pattern '{pattern}': {len(matches)} matches")
                print(f"     Ví dụ: {matches[:5]}")
        
        # 4. Tìm kiếm năm (có thể là năm sản xuất)
        year_pattern = r'\b(19|20)\d{2}\b'
        years = re.findall(year_pattern, html_content)
        if years:
            print(f"   - Năm: {len(years)} matches - {set(years)}")
        
        # 5. Tìm kiếm km
        km_pattern = r'\b\d+[.,]\d+\s*km\b'
        km_matches = re.findall(km_pattern, html_content)
        if km_matches:
            print(f"   - KM: {len(km_matches)} matches - {km_matches[:5]}")
        
        # 6. Tìm kiếm các script tags và nội dung
        print(f"\n📜 Phân tích Script Tags:")
        script_tags = soup.find_all('script')
        for i, script in enumerate(script_tags):
            if script.string:
                script_content = script.string.strip()
                print(f"   Script {i+1}: {len(script_content)} ký tự")
                print(f"     Bắt đầu: {script_content[:100]}...")
                
                # Tìm kiếm các pattern trong script
                if 'advert' in script_content.lower():
                    print(f"     ✅ Chứa từ 'advert'")
                if 'car' in script_content.lower():
                    print(f"     ✅ Chứa từ 'car'")
                if 'price' in script_content.lower():
                    print(f"     ✅ Chứa từ 'price'")
        
        # 7. Tìm kiếm các elements có thể chứa dữ liệu
        print(f"\n🔍 Tìm kiếm Elements:")
        
        # Tìm tất cả divs
        all_divs = soup.find_all('div')
        print(f"   - Tổng số divs: {len(all_divs)}")
        
        # Tìm divs có class
        divs_with_class = [div for div in all_divs if div.get('class')]
        print(f"   - Divs có class: {len(divs_with_class)}")
        
        # Tìm divs có id
        divs_with_id = [div for div in all_divs if div.get('id')]
        print(f"   - Divs có id: {len(divs_with_id)}")
        
        # Tìm divs có data attributes
        divs_with_data = [div for div in all_divs if any(attr.startswith('data-') for attr in div.attrs)]
        print(f"   - Divs có data attributes: {len(divs_with_data)}")
        
        # 8. Tìm kiếm các pattern JSON trong toàn bộ HTML
        print(f"\n🔍 Tìm kiếm JSON Patterns:")
        
        # Tìm tất cả các object JSON có thể có
        json_patterns = [
            r'\{[^{}]*"advert"[^{}]*\}',
            r'\{[^{}]*"ad"[^{}]*\}',
            r'\{[^{}]*"car"[^{}]*\}',
            r'\{[^{}]*"auto"[^{}]*\}',
            r'\{[^{}]*"vehicle"[^{}]*\}',
            r'\{[^{}]*"price"[^{}]*\}',
            r'\{[^{}]*"title"[^{}]*\}',
            r'\{[^{}]*"description"[^{}]*\}',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                print(f"   - Pattern '{pattern}': {len(matches)} matches")
                for match in matches[:3]:
                    print(f"     Ví dụ: {match[:100]}...")
        
        # 9. Tìm kiếm các pattern khác
        print(f"\n🔍 Tìm kiếm các Pattern khác:")
        
        # Tìm các pattern có thể chứa dữ liệu
        other_patterns = [
            r'data-[a-zA-Z-]+="[^"]*"',
            r'id="[^"]*"',
            r'class="[^"]*"',
            r'href="[^"]*"',
            r'src="[^"]*"',
        ]
        
        for pattern in other_patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                print(f"   - Pattern '{pattern}': {len(matches)} matches")
                print(f"     Ví dụ: {matches[:3]}")
        
        return {
            'html_content': html_content,
            'soup': soup,
            'analysis': {
                'total_chars': len(html_content),
                'script_tags': len(script_tags),
                'divs': len(all_divs),
                'keywords_found': {kw: html_content.count(kw) for kw in keywords if html_content.count(kw) > 0}
            }
        }
        
    except Exception as e:
        print(f"❌ Lỗi khi phân tích HTML: {e}")
        return None

def suggest_solutions(analysis_result):
    """
    Đưa ra các giải pháp dựa trên kết quả phân tích
    """
    print(f"\n💡 Đề xuất giải pháp:")
    
    if not analysis_result:
        print("❌ Không thể phân tích file")
        return
    
    analysis = analysis_result['analysis']
    
    print(f"📊 Kết quả phân tích:")
    print(f"   - File chứa HTML tĩnh từ Next.js")
    print(f"   - Có {analysis['script_tags']} script tags (external)")
    print(f"   - Có {analysis['divs']} div elements")
    print(f"   - Từ khóa tìm thấy: {analysis['keywords_found']}")
    
    print(f"\n🎯 Kết luận:")
    print(f"   - File RTF này chứa HTML được render từ Next.js")
    print(f"   - Dữ liệu xe KHÔNG có trong HTML tĩnh")
    print(f"   - Dữ liệu được load động bằng JavaScript")
    
    print(f"\n🚀 Giải pháp đề xuất:")
    print(f"   1. Sử dụng Selenium/Playwright để render trang web")
    print(f"   2. Sử dụng API của willhaben.at (nếu có)")
    print(f"   3. Sử dụng headless browser để crawl dữ liệu")
    print(f"   4. Phân tích network requests để tìm API endpoints")
    
    print(f"\n📝 Script mẫu với Selenium:")
    print(f"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import json

# Setup Chrome driver
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(options=chrome_options)

try:
    # Load trang web
    driver.get('https://www.willhaben.at/iad/gebrauchtwagen/auto/gebrauchtwagenboerse')
    
    # Đợi trang load
    time.sleep(5)
    
    # Tìm dữ liệu JSON trong page source
    page_source = driver.page_source
    
    # Tìm __NEXT_DATA__ hoặc các script chứa dữ liệu
    # ... (code để parse dữ liệu)
    
finally:
    driver.quit()
""")

def main():
    if len(sys.argv) != 2:
        print("Usage: python comprehensive_analysis.py <path_to_rtf_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        print(f"❌ File không tồn tại: {file_path}")
        sys.exit(1)
    
    # Phân tích toàn diện
    analysis_result = comprehensive_html_analysis(file_path)
    
    # Đưa ra giải pháp
    suggest_solutions(analysis_result)
    
    # Lưu kết quả
    if analysis_result:
        output_file = "comprehensive_analysis.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_result['analysis'], f, ensure_ascii=False, indent=2)
        print(f"\n✅ Đã lưu kết quả phân tích vào file: {output_file}")

if __name__ == "__main__":
    main()

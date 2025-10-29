#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script debug để xem chi tiết các script tags trong file RTF
"""

import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

def debug_rtf_scripts(file_path):
    """
    Debug các script tags trong file RTF
    """
    print(f"🚀 Debug file RTF: {file_path}")
    
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
        
        # Tìm tất cả script tags
        script_tags = soup.find_all('script')
        print(f"🔍 Tìm thấy {len(script_tags)} script tags")
        
        # Debug từng script tag
        for i, script in enumerate(script_tags):
            print(f"\n📜 Script {i+1}:")
            print(f"   - Có src: {script.get('src', 'None')}")
            print(f"   - Có id: {script.get('id', 'None')}")
            print(f"   - Có type: {script.get('type', 'None')}")
            
            if script.string:
                script_content = script.string.strip()
                print(f"   - Nội dung: {len(script_content)} ký tự")
                print(f"   - Bắt đầu: {script_content[:100]}...")
                print(f"   - Kết thúc: ...{script_content[-100:]}")
                
                # Kiểm tra JSON
                if script_content.startswith('{') and script_content.endswith('}'):
                    print(f"   - ✅ Có thể là JSON")
                    try:
                        json_obj = json.loads(script_content)
                        print(f"   - ✅ JSON hợp lệ!")
                        print(f"   - Keys: {list(json_obj.keys())[:5]}...")
                    except json.JSONDecodeError as e:
                        print(f"   - ❌ JSON không hợp lệ: {e}")
                else:
                    print(f"   - ❌ Không phải JSON")
            else:
                print(f"   - Không có nội dung")
        
        # Tìm kiếm JSON trong toàn bộ HTML
        print(f"\n🔍 Tìm kiếm JSON patterns trong HTML...")
        
        # Pattern 1: Tìm các object JSON
        json_patterns = [
            r'\{[^{}]*"adverts"[^{}]*\}',
            r'\{[^{}]*"ads"[^{}]*\}',
            r'\{[^{}]*"listings"[^{}]*\}',
            r'\{[^{}]*"results"[^{}]*\}',
            r'\{[^{}]*"items"[^{}]*\}',
        ]
        
        for i, pattern in enumerate(json_patterns):
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            print(f"   Pattern {i+1}: Tìm thấy {len(matches)} matches")
            if matches:
                print(f"   - Ví dụ: {matches[0][:200]}...")
        
        # Tìm kiếm các từ khóa liên quan đến xe
        car_keywords = ['advert', 'ad', 'listing', 'car', 'auto', 'vehicle', 'price', 'title']
        for keyword in car_keywords:
            count = html_content.lower().count(keyword)
            if count > 0:
                print(f"   - '{keyword}': {count} lần xuất hiện")
        
        return html_content
        
    except Exception as e:
        print(f"❌ Lỗi khi đọc file: {e}")
        return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python debug_rtf.py <path_to_rtf_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        print(f"❌ File không tồn tại: {file_path}")
        sys.exit(1)
    
    debug_rtf_scripts(file_path)

if __name__ == "__main__":
    main()

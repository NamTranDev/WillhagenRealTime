#!/usr/bin/env python3
"""
Willhaben Simple Parser
=======================

Script đơn giản để parse file HTML/RTF từ Willhaben và trích xuất dữ liệu JSON
"""

import json
import re
import sys
from pathlib import Path


def extract_html_from_rtf(content: str) -> str:
    """Extract HTML content từ RTF file"""
    # Tìm HTML content trong RTF
    html_match = re.search(r'<!DOCTYPE html>.*?</html>', content, re.DOTALL)
    if html_match:
        return html_match.group(0)
    return content


def extract_next_data(html_content: str) -> dict:
    """Extract JSON từ thẻ <script id="__NEXT_DATA__">"""
    # Tìm thẻ script với __NEXT_DATA__
    pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
    match = re.search(pattern, html_content, re.DOTALL)
    
    if not match:
        print("❌ Không tìm thấy thẻ __NEXT_DATA__")
        return {}
    
    try:
        json_content = match.group(1)
        return json.loads(json_content)
    except json.JSONDecodeError as e:
        print(f"❌ Lỗi parse JSON: {e}")
        return {}


def find_listings_recursive(data, path=""):
    """Tìm listings trong JSON data"""
    listings = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            # Tìm các key có thể chứa listings
            if key in ['adverts', 'ads', 'listings', 'items', 'results', 'advertSummaryList']:
                if isinstance(value, list):
                    print(f"🔍 Tìm thấy danh sách tại: {current_path} ({len(value)} items)")
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            listing = extract_listing_info(item, f"{current_path}[{i}]")
                            if listing:
                                listings.append(listing)
            
            # Tiếp tục tìm trong nested objects
            listings.extend(find_listings_recursive(value, current_path))
    
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                listing = extract_listing_info(item, f"{path}[{i}]")
                if listing:
                    listings.append(listing)
    
    return listings


def extract_listing_info(item, path):
    """Extract thông tin từ một listing"""
    listing = {
        'path': path,
        'id': get_value(item, ['id', 'adId', 'advertId', 'advert_id']),
        'title': get_value(item, ['title', 'headline', 'name', 'subject']),
        'price': get_value(item, ['price', 'priceValue', 'price_value']),
        'url': get_value(item, ['url', 'selfLink', 'self_link', 'link']),
        'description': get_value(item, ['description', 'text', 'content']),
        'location': get_value(item, ['location', 'address', 'city', 'plz']),
        'year': get_value(item, ['year', 'yearOfConstruction', 'year_of_construction']),
        'km': get_value(item, ['km', 'mileage', 'kilometer']),
        'fuel': get_value(item, ['fuel', 'fuelType', 'fuel_type']),
        'power': get_value(item, ['power', 'powerKw', 'power_kw']),
        'images': get_value(item, ['images', 'pictures', 'photos']),
        'seller': get_value(item, ['seller', 'dealer', 'user']),
        'category': get_value(item, ['category', 'categoryId', 'category_id']),
        'created': get_value(item, ['created', 'createdAt', 'created_at']),
        'modified': get_value(item, ['modified', 'modifiedAt', 'modified_at'])
    }
    
    # Chỉ trả về nếu có ít nhất id hoặc title
    if listing['id'] or listing['title']:
        return listing
    return None


def get_value(data, keys):
    """Lấy giá trị từ dict với nhiều key có thể"""
    for key in keys:
        if key in data:
            return data[key]
    
    # Tìm trong nested objects
    for key, value in data.items():
        if isinstance(value, dict):
            result = get_value(value, keys)
            if result is not None:
                return result
    
    return None


def main():
    """Hàm main"""
    if len(sys.argv) < 2:
        print("❌ Sử dụng: python willhaben_simple_parser.py <file_path>")
        print("📝 Ví dụ: python willhaben_simple_parser.py '/Users/apple/Desktop/willhaben html.rtf'")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # Kiểm tra file tồn tại
    if not Path(file_path).exists():
        print(f"❌ File không tồn tại: {file_path}")
        sys.exit(1)
    
    print(f"🚀 Bắt đầu parse file: {file_path}")
    
    # Đọc file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"✅ Đã đọc file: {len(content)} ký tự")
    except Exception as e:
        print(f"❌ Lỗi đọc file: {e}")
        sys.exit(1)
    
    # Extract HTML từ RTF
    html_content = extract_html_from_rtf(content)
    print(f"📄 HTML content: {len(html_content)} ký tự")
    
    # Extract JSON data
    next_data = extract_next_data(html_content)
    if not next_data:
        print("❌ Không thể extract JSON data")
        sys.exit(1)
    
    print(f"✅ Đã parse JSON: {len(next_data)} keys")
    
    # Tìm listings
    print("🔍 Tìm kiếm listings...")
    listings = find_listings_recursive(next_data)
    
    if listings:
        print(f"✅ Tìm thấy {len(listings)} listings")
        
        # In kết quả
        print("\n" + "="*60)
        print("📋 DANH SÁCH LISTINGS")
        print("="*60)
        
        for i, listing in enumerate(listings[:5], 1):  # Chỉ hiển thị 5 đầu
            print(f"\n🚗 LISTING {i}:")
            print("-" * 30)
            for key, value in listing.items():
                if value is not None:
                    print(f"{key}: {value}")
        
        if len(listings) > 5:
            print(f"\n... và {len(listings) - 5} listings khác")
        
        # Lưu ra file JSON
        output_file = f"{Path(file_path).stem}_listings.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(listings, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Đã lưu vào: {output_file}")
        except Exception as e:
            print(f"❌ Lỗi lưu file: {e}")
        
    else:
        print("❌ Không tìm thấy listings nào")
        
        # Debug: In structure của JSON
        print("\n🔍 DEBUG - Cấu trúc JSON:")
        print("-" * 40)
        def print_structure(data, indent=0):
            if isinstance(data, dict):
                for key, value in data.items():
                    print("  " * indent + f"{key}: {type(value).__name__}")
                    if isinstance(value, (dict, list)) and indent < 3:
                        print_structure(value, indent + 1)
            elif isinstance(data, list) and len(data) > 0:
                print("  " * indent + f"List[{len(data)}]")
                if isinstance(data[0], dict) and indent < 3:
                    print_structure(data[0], indent + 1)
        
        print_structure(next_data)


if __name__ == "__main__":
    main()

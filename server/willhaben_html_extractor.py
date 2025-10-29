#!/usr/bin/env python3
"""
Willhaben HTML Data Extractor
=============================

Script để tìm và extract dữ liệu từ HTML content của Willhaben
"""

import re
import json
import sys
from pathlib import Path


def extract_html_from_rtf(content: str) -> str:
    """Extract HTML content từ RTF file"""
    html_match = re.search(r'<!DOCTYPE html>.*?</html>', content, re.DOTALL)
    if html_match:
        return html_match.group(0)
    return content


def find_data_in_html(html_content: str):
    """Tìm dữ liệu trong HTML content"""
    print("🔍 Tìm kiếm dữ liệu trong HTML...")
    
    # Tìm các pattern có thể chứa dữ liệu
    patterns = [
        # JSON trong script tags
        r'<script[^>]*>(.*?)</script>',
        # JSON trong data attributes
        r'data-[^=]*="([^"]*)"',
        # JSON trong window variables
        r'window\.[^=]*=\s*({.*?});',
        # JSON trong các thẻ khác
        r'<[^>]*data-[^=]*="([^"]*)"',
    ]
    
    all_data = []
    
    for i, pattern in enumerate(patterns):
        matches = re.findall(pattern, html_content, re.DOTALL)
        print(f"Pattern {i+1}: Tìm thấy {len(matches)} matches")
        
        for j, match in enumerate(matches):
            if len(match.strip()) > 10:  # Chỉ xử lý content có ý nghĩa
                # Thử parse JSON
                try:
                    # Clean up match
                    clean_match = match.strip()
                    if clean_match.startswith('{') and clean_match.endswith('}'):
                        data = json.loads(clean_match)
                        all_data.append({
                            'pattern': i+1,
                            'match': j+1,
                            'data': data,
                            'size': len(clean_match)
                        })
                        print(f"  ✅ Match {j+1}: JSON hợp lệ ({len(clean_match)} ký tự)")
                    else:
                        # Thử decode HTML entities
                        import html
                        decoded = html.unescape(clean_match)
                        if decoded.startswith('{') and decoded.endswith('}'):
                            data = json.loads(decoded)
                            all_data.append({
                                'pattern': i+1,
                                'match': j+1,
                                'data': data,
                                'size': len(decoded)
                            })
                            print(f"  ✅ Match {j+1}: JSON hợp lệ sau decode ({len(decoded)} ký tự)")
                except:
                    pass
    
    return all_data


def search_for_listings(data_list):
    """Tìm listings trong danh sách data"""
    listings = []
    
    for item in data_list:
        data = item['data']
        found_listings = find_listings_recursive(data, f"pattern{item['pattern']}_match{item['match']}")
        if found_listings:
            print(f"🎯 Tìm thấy {len(found_listings)} listings trong pattern {item['pattern']}, match {item['match']}")
            listings.extend(found_listings)
    
    return listings


def find_listings_recursive(data, path=""):
    """Tìm listings trong JSON data"""
    listings = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            # Tìm các key có thể chứa listings
            if key.lower() in ['adverts', 'ads', 'listings', 'items', 'results', 'advertsummarylist', 'advertlist']:
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
        'id': get_value(item, ['id', 'adId', 'advertId', 'advert_id', 'advertId']),
        'title': get_value(item, ['title', 'headline', 'name', 'subject', 'headline']),
        'price': get_value(item, ['price', 'priceValue', 'price_value', 'priceValue']),
        'url': get_value(item, ['url', 'selfLink', 'self_link', 'link', 'selfLink']),
        'description': get_value(item, ['description', 'text', 'content', 'description']),
        'location': get_value(item, ['location', 'address', 'city', 'plz', 'location']),
        'year': get_value(item, ['year', 'yearOfConstruction', 'year_of_construction', 'yearOfConstruction']),
        'km': get_value(item, ['km', 'mileage', 'kilometer', 'mileage']),
        'fuel': get_value(item, ['fuel', 'fuelType', 'fuel_type', 'fuelType']),
        'power': get_value(item, ['power', 'powerKw', 'power_kw', 'powerKw']),
        'images': get_value(item, ['images', 'pictures', 'photos', 'images']),
        'seller': get_value(item, ['seller', 'dealer', 'user', 'seller']),
        'category': get_value(item, ['category', 'categoryId', 'category_id', 'categoryId']),
        'created': get_value(item, ['created', 'createdAt', 'created_at', 'createdAt']),
        'modified': get_value(item, ['modified', 'modifiedAt', 'modified_at', 'modifiedAt'])
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
        print("❌ Sử dụng: python willhaben_html_extractor.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        print(f"❌ File không tồn tại: {file_path}")
        sys.exit(1)
    
    print(f"🚀 Extract dữ liệu từ: {file_path}")
    
    # Đọc file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"✅ Đã đọc file: {len(content)} ký tự")
    except Exception as e:
        print(f"❌ Lỗi đọc file: {e}")
        sys.exit(1)
    
    # Extract HTML
    html_content = extract_html_from_rtf(content)
    print(f"📄 HTML content: {len(html_content)} ký tự")
    
    # Tìm dữ liệu
    data_list = find_data_in_html(html_content)
    
    if not data_list:
        print("❌ Không tìm thấy dữ liệu JSON nào")
        sys.exit(1)
    
    print(f"✅ Tìm thấy {len(data_list)} JSON objects")
    
    # Tìm listings
    listings = search_for_listings(data_list)
    
    if listings:
        print(f"🎉 Tìm thấy {len(listings)} listings!")
        
        # In kết quả
        print("\n" + "="*60)
        print("📋 DANH SÁCH LISTINGS")
        print("="*60)
        
        for i, listing in enumerate(listings[:5], 1):
            print(f"\n🚗 LISTING {i}:")
            print("-" * 30)
            for key, value in listing.items():
                if value is not None:
                    print(f"{key}: {value}")
        
        if len(listings) > 5:
            print(f"\n... và {len(listings) - 5} listings khác")
        
        # Lưu ra file JSON
        output_file = f"{Path(file_path).stem}_extracted_listings.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(listings, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Đã lưu vào: {output_file}")
        except Exception as e:
            print(f"❌ Lỗi lưu file: {e}")
        
    else:
        print("❌ Không tìm thấy listings nào")
        
        # Debug: In structure của JSON objects
        print("\n🔍 DEBUG - Cấu trúc JSON objects:")
        print("-" * 40)
        for i, item in enumerate(data_list[:3]):  # Chỉ debug 3 objects đầu
            print(f"\nJSON Object {i+1} (Pattern {item['pattern']}, Match {item['match']}):")
            data = item['data']
            
            def print_structure(data, indent=0):
                if isinstance(data, dict):
                    for key, value in data.items():
                        print("  " * indent + f"{key}: {type(value).__name__}")
                        if isinstance(value, (dict, list)) and indent < 2:
                            print_structure(value, indent + 1)
                elif isinstance(data, list) and len(data) > 0:
                    print("  " * indent + f"List[{len(data)}]")
                    if isinstance(data[0], dict) and indent < 2:
                        print_structure(data[0], indent + 1)
            
            print_structure(data)


if __name__ == "__main__":
    main()

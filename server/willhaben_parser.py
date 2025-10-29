#!/usr/bin/env python3
"""
Willhaben HTML Parser
====================

Script để parse file HTML từ Willhaben và trích xuất dữ liệu JSON từ thẻ __NEXT_DATA__
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup


class WillhabenParser:
    """Parser cho file HTML Willhaben"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.html_content = ""
        self.next_data = {}
        self.listings = []
    
    def read_file(self) -> str:
        """Đọc nội dung file HTML"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Nếu file là RTF, extract HTML content
            if content.startswith('{\\rtf1'):
                # Tìm và extract HTML từ RTF
                html_match = re.search(r'<!DOCTYPE html>.*?</html>', content, re.DOTALL)
                if html_match:
                    self.html_content = html_match.group(0)
                else:
                    raise ValueError("Không tìm thấy HTML content trong RTF file")
            else:
                self.html_content = content
            
            print(f"✅ Đã đọc file: {self.file_path}")
            print(f"📄 Kích thước HTML: {len(self.html_content)} ký tự")
            return self.html_content
            
        except Exception as e:
            print(f"❌ Lỗi đọc file: {e}")
            return ""
    
    def extract_next_data(self) -> Optional[Dict]:
        """Trích xuất JSON từ thẻ <script id="__NEXT_DATA__">"""
        try:
            soup = BeautifulSoup(self.html_content, 'html.parser')
            
            # Tìm thẻ script với id="__NEXT_DATA__"
            next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
            
            if not next_data_script:
                print("❌ Không tìm thấy thẻ <script id=\"__NEXT_DATA__\">")
                return None
            
            # Lấy nội dung JSON
            json_content = next_data_script.string
            if not json_content:
                print("❌ Thẻ __NEXT_DATA__ không có nội dung")
                return None
            
            # Parse JSON
            self.next_data = json.loads(json_content)
            print(f"✅ Đã parse JSON từ __NEXT_DATA__")
            print(f"📊 Có {len(self.next_data)} keys trong JSON")
            
            return self.next_data
            
        except json.JSONDecodeError as e:
            print(f"❌ Lỗi parse JSON: {e}")
            return None
        except Exception as e:
            print(f"❌ Lỗi extract next data: {e}")
            return None
    
    def find_listings_in_props(self, data: Any, path: str = "") -> List[Dict]:
        """Tìm danh sách listings trong props"""
        listings = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                # Tìm các key có thể chứa listings
                if key in ['adverts', 'ads', 'listings', 'items', 'results', 'advertSummaryList']:
                    if isinstance(value, list):
                        print(f"🔍 Tìm thấy danh sách tại: {current_path} ({len(value)} items)")
                        listings.extend(self.extract_listings_from_list(value, current_path))
                
                # Tiếp tục tìm trong nested objects
                listings.extend(self.find_listings_in_props(value, current_path))
                
        elif isinstance(data, list):
            listings.extend(self.extract_listings_from_list(data, path))
        
        return listings
    
    def extract_listings_from_list(self, items: List, path: str) -> List[Dict]:
        """Trích xuất listings từ danh sách"""
        listings = []
        
        for i, item in enumerate(items):
            if isinstance(item, dict):
                listing = self.extract_listing_info(item, f"{path}[{i}]")
                if listing:
                    listings.append(listing)
        
        return listings
    
    def extract_listing_info(self, item: Dict, path: str) -> Optional[Dict]:
        """Trích xuất thông tin từ một listing"""
        try:
            # Tìm các trường có thể có
            listing = {
                'path': path,
                'id': self.get_nested_value(item, ['id', 'adId', 'advertId', 'advert_id']),
                'title': self.get_nested_value(item, ['title', 'headline', 'name', 'subject']),
                'price': self.get_nested_value(item, ['price', 'priceValue', 'price_value']),
                'url': self.get_nested_value(item, ['url', 'selfLink', 'self_link', 'link']),
                'description': self.get_nested_value(item, ['description', 'text', 'content']),
                'location': self.get_nested_value(item, ['location', 'address', 'city', 'plz']),
                'year': self.get_nested_value(item, ['year', 'yearOfConstruction', 'year_of_construction']),
                'km': self.get_nested_value(item, ['km', 'mileage', 'kilometer']),
                'fuel': self.get_nested_value(item, ['fuel', 'fuelType', 'fuel_type']),
                'power': self.get_nested_value(item, ['power', 'powerKw', 'power_kw']),
                'images': self.get_nested_value(item, ['images', 'pictures', 'photos']),
                'seller': self.get_nested_value(item, ['seller', 'dealer', 'user']),
                'category': self.get_nested_value(item, ['category', 'categoryId', 'category_id']),
                'created': self.get_nested_value(item, ['created', 'createdAt', 'created_at']),
                'modified': self.get_nested_value(item, ['modified', 'modifiedAt', 'modified_at']),
                'raw_data': item  # Giữ lại raw data để debug
            }
            
            # Chỉ trả về listing nếu có ít nhất id hoặc title
            if listing['id'] or listing['title']:
                return listing
            
        except Exception as e:
            print(f"⚠️ Lỗi extract listing tại {path}: {e}")
        
        return None
    
    def get_nested_value(self, data: Dict, keys: List[str]) -> Any:
        """Lấy giá trị từ nested dict với nhiều key có thể"""
        for key in keys:
            if key in data:
                return data[key]
        
        # Tìm trong nested objects
        for key, value in data.items():
            if isinstance(value, dict):
                result = self.get_nested_value(value, keys)
                if result is not None:
                    return result
        
        return None
    
    def parse(self) -> List[Dict]:
        """Parse file và trích xuất listings"""
        print(f"🚀 Bắt đầu parse file: {self.file_path}")
        
        # Đọc file
        if not self.read_file():
            return []
        
        # Extract JSON data
        if not self.extract_next_data():
            return []
        
        # Tìm listings trong props
        print("🔍 Tìm kiếm listings trong JSON data...")
        
        # Tìm trong props.pageProps
        if 'props' in self.next_data and 'pageProps' in self.next_data['props']:
            page_props = self.next_data['props']['pageProps']
            self.listings = self.find_listings_in_props(page_props, 'props.pageProps')
        
        # Tìm trong toàn bộ JSON nếu chưa tìm thấy
        if not self.listings:
            print("🔍 Tìm kiếm trong toàn bộ JSON...")
            self.listings = self.find_listings_in_props(self.next_data, 'root')
        
        print(f"✅ Tìm thấy {len(self.listings)} listings")
        return self.listings
    
    def save_to_json(self, output_file: str = None) -> str:
        """Lưu kết quả ra file JSON"""
        if not output_file:
            output_file = f"{Path(self.file_path).stem}_listings.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.listings, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Đã lưu {len(self.listings)} listings vào: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"❌ Lỗi lưu file: {e}")
            return ""
    
    def print_summary(self):
        """In tóm tắt kết quả"""
        print("\n" + "="*60)
        print("📊 TÓM TẮT KẾT QUẢ")
        print("="*60)
        print(f"📁 File: {self.file_path}")
        print(f"📄 Kích thước HTML: {len(self.html_content)} ký tự")
        print(f"🔍 Số listings tìm thấy: {len(self.listings)}")
        
        if self.listings:
            print(f"\n📋 MẪU LISTING ĐẦU TIÊN:")
            print("-" * 40)
            first_listing = self.listings[0]
            for key, value in first_listing.items():
                if key != 'raw_data' and value is not None:
                    print(f"{key}: {value}")
        
        print("\n" + "="*60)


def main():
    """Hàm main"""
    if len(sys.argv) < 2:
        print("❌ Sử dụng: python willhaben_parser.py <file_path>")
        print("📝 Ví dụ: python willhaben_parser.py '/Users/apple/Desktop/willhaben html.rtf'")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # Kiểm tra file tồn tại
    if not Path(file_path).exists():
        print(f"❌ File không tồn tại: {file_path}")
        sys.exit(1)
    
    # Tạo parser và parse
    parser = WillhabenParser(file_path)
    listings = parser.parse()
    
    if listings:
        # In kết quả ra console
        print("\n" + "="*60)
        print("📋 DANH SÁCH LISTINGS")
        print("="*60)
        
        for i, listing in enumerate(listings[:10], 1):  # Chỉ hiển thị 10 đầu
            print(f"\n🚗 LISTING {i}:")
            print("-" * 30)
            for key, value in listing.items():
                if key != 'raw_data' and value is not None:
                    print(f"{key}: {value}")
        
        if len(listings) > 10:
            print(f"\n... và {len(listings) - 10} listings khác")
        
        # Lưu ra file JSON
        output_file = parser.save_to_json()
        
        # In tóm tắt
        parser.print_summary()
        
    else:
        print("❌ Không tìm thấy listings nào")


if __name__ == "__main__":
    main()

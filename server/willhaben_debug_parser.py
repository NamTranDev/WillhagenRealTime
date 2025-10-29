#!/usr/bin/env python3
"""
Willhaben Debug Parser
======================

Script để debug và tìm tất cả thẻ script trong HTML
"""

import re
import sys
from pathlib import Path


def extract_html_from_rtf(content: str) -> str:
    """Extract HTML content từ RTF file"""
    html_match = re.search(r'<!DOCTYPE html>.*?</html>', content, re.DOTALL)
    if html_match:
        return html_match.group(0)
    return content


def find_all_scripts(html_content: str):
    """Tìm tất cả thẻ script"""
    # Tìm tất cả thẻ script
    script_pattern = r'<script[^>]*>(.*?)</script>'
    scripts = re.findall(script_pattern, html_content, re.DOTALL)
    
    print(f"🔍 Tìm thấy {len(scripts)} thẻ script")
    
    for i, script_content in enumerate(scripts):
        print(f"\n📜 SCRIPT {i+1}:")
        print("-" * 40)
        
        # Tìm thẻ script tag để lấy attributes
        script_tag_pattern = r'<script[^>]*>'
        script_tags = re.findall(script_tag_pattern, html_content)
        
        if i < len(script_tags):
            print(f"Tag: {script_tags[i]}")
        
        # Kiểm tra nội dung
        if len(script_content.strip()) > 0:
            # Kiểm tra có phải JSON không
            if script_content.strip().startswith('{') and script_content.strip().endswith('}'):
                print("✅ Có vẻ là JSON data")
                try:
                    import json
                    data = json.loads(script_content)
                    print(f"📊 JSON keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                except:
                    print("❌ Không phải JSON hợp lệ")
            else:
                print(f"📄 Nội dung: {script_content[:200]}...")
        else:
            print("📄 Script rỗng")


def find_json_data(html_content: str):
    """Tìm tất cả JSON data trong HTML"""
    # Tìm các pattern JSON có thể
    patterns = [
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',
        r'window\.__NEXT_DATA__\s*=\s*({.*?});',
        r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
        r'window\.__DATA__\s*=\s*({.*?});',
    ]
    
    for i, pattern in enumerate(patterns):
        matches = re.findall(pattern, html_content, re.DOTALL)
        if matches:
            print(f"\n🎯 Pattern {i+1} tìm thấy {len(matches)} matches:")
            for j, match in enumerate(matches):
                print(f"  Match {j+1}: {len(match)} ký tự")
                if len(match) > 100:
                    print(f"    Preview: {match[:100]}...")
                else:
                    print(f"    Content: {match}")


def main():
    """Hàm main"""
    if len(sys.argv) < 2:
        print("❌ Sử dụng: python willhaben_debug_parser.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        print(f"❌ File không tồn tại: {file_path}")
        sys.exit(1)
    
    print(f"🚀 Debug file: {file_path}")
    
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
    
    # Tìm tất cả scripts
    find_all_scripts(html_content)
    
    # Tìm JSON data
    find_json_data(html_content)


if __name__ == "__main__":
    main()

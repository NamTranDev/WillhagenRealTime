#!/usr/bin/env python3
"""
Willhaben.at Realtime Crawler Backend
=====================================

Backend Python realtime crawl dữ liệu từ trang web Willhaben.at
Sử dụng FastAPI + aiohttp + WebSocket để phát hiện và gửi tin mới realtime

Tác giả: AI Assistant
Ngày tạo: 2024
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fake_useragent import UserAgent
import uvicorn


# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """Cấu hình ứng dụng"""
    
    # Crawler settings
    BASE_URL = "https://www.willhaben.at/iad/gebrauchtwagen/auto/gebrauchtwagenboerse"
    CRAWL_INTERVAL = 3.0  # Giây giữa các lần crawl
    MAX_WORKERS = 5  # Số worker async song song
    REQUEST_TIMEOUT = 10  # Timeout cho HTTP requests
    
    # Anti-detection settings
    MIN_DELAY = 0.5  # Delay tối thiểu giữa requests
    MAX_DELAY = 2.0  # Delay tối đa giữa requests
    USER_AGENT_ROTATION = True
    
    # Proxy settings
    USE_PROXY_ROTATION = False  # Bật/tắt proxy rotation
    AUTO_FETCH_FREE_PROXY = True  # Tự động lấy proxy free
    PROXY_LIST = [
        # Thêm proxy của bạn vào đây (tùy chọn)
        # "http://proxy1:port",
        # "http://proxy2:port",
        # "http://proxy3:port",
        # "http://username:password@proxy4:port"
    ]
    PROXY_TIMEOUT = 10  # Timeout cho proxy requests
    FREE_PROXY_SOURCES = [
        "https://www.proxy-list.download/api/v1/get?type=http",
        "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"
    ]
    MAX_FREE_PROXIES = 50  # Số lượng proxy free tối đa
    PROXY_FETCH_INTERVAL = 300  # Thời gian fetch proxy mới (giây)
    
    # WebSocket settings
    MAX_CONNECTIONS = 100
    
    # Logging
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging():
    """Thiết lập logging"""
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format=Config.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('willhaben_crawler.log')
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logging()


# =============================================================================
# FREE PROXY MANAGER
# =============================================================================

class FreeProxyManager:
    """Quản lý việc fetch và test proxy free"""
    
    def __init__(self):
        self.logger = logging.getLogger("FreeProxyManager")
        self.last_fetch_time = None
        self.fetched_proxies = []
        
    async def fetch_proxies_from_source(self, session: aiohttp.ClientSession, source: str) -> List[str]:
        """Fetch proxy từ một nguồn cụ thể"""
        try:
            self.logger.debug(f"Fetching proxies from: {source}")
            
            async with session.get(source, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    content = await response.text()
                    proxies = self.parse_proxy_content(content)
                    self.logger.info(f"Fetched {len(proxies)} proxies from {source}")
                    return proxies
                else:
                    self.logger.warning(f"Failed to fetch from {source}: HTTP {response.status}")
                    return []
        except Exception as e:
            self.logger.error(f"Error fetching from {source}: {e}")
            return []
    
    def parse_proxy_content(self, content: str) -> List[str]:
        """Parse nội dung proxy từ các nguồn khác nhau"""
        proxies = []
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Parse các format khác nhau
            if ':' in line:
                parts = line.split(':')
                if len(parts) >= 2:
                    ip = parts[0].strip()
                    port = parts[1].strip()
                    
                    # Validate IP và port
                    if self.is_valid_ip(ip) and self.is_valid_port(port):
                        proxy = f"http://{ip}:{port}"
                        proxies.append(proxy)
        
        return proxies
    
    def is_valid_ip(self, ip: str) -> bool:
        """Kiểm tra IP có hợp lệ không"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            
            for part in parts:
                if not part.isdigit() or int(part) < 0 or int(part) > 255:
                    return False
            
            return True
        except:
            return False
    
    def is_valid_port(self, port: str) -> bool:
        """Kiểm tra port có hợp lệ không"""
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except:
            return False
    
    async def test_proxy(self, session: aiohttp.ClientSession, proxy: str) -> bool:
        """Test proxy có hoạt động không"""
        try:
            test_url = "http://httpbin.org/ip"
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with session.get(test_url, proxy=proxy, timeout=timeout) as response:
                if response.status == 200:
                    return True
                return False
        except Exception as e:
            self.logger.debug(f"Proxy test failed for {proxy}: {e}")
            return False
    
    async def fetch_and_test_proxies(self) -> List[str]:
        """Fetch và test proxy từ tất cả nguồn"""
        if not Config.AUTO_FETCH_FREE_PROXY:
            return []
        
        self.logger.info("Starting to fetch free proxies...")
        
        async with aiohttp.ClientSession() as session:
            all_proxies = []
            
            # Fetch từ tất cả nguồn
            for source in Config.FREE_PROXY_SOURCES:
                proxies = await self.fetch_proxies_from_source(session, source)
                all_proxies.extend(proxies)
                
                # Delay giữa các requests
                await asyncio.sleep(random.uniform(1, 3))
            
            # Loại bỏ duplicate
            unique_proxies = list(set(all_proxies))
            self.logger.info(f"Found {len(unique_proxies)} unique proxies")
            
            # Test proxy và chỉ giữ lại những proxy hoạt động
            working_proxies = []
            test_tasks = []
            
            # Tạo tasks để test song song
            for proxy in unique_proxies[:Config.MAX_FREE_PROXIES]:
                task = asyncio.create_task(self.test_proxy(session, proxy))
                test_tasks.append((proxy, task))
            
            # Chờ kết quả test
            for proxy, task in test_tasks:
                try:
                    is_working = await task
                    if is_working:
                        working_proxies.append(proxy)
                        self.logger.debug(f"Proxy working: {proxy}")
                except Exception as e:
                    self.logger.debug(f"Error testing proxy {proxy}: {e}")
            
            self.logger.info(f"Found {len(working_proxies)} working proxies")
            self.last_fetch_time = datetime.now()
            
            return working_proxies


# =============================================================================
# PROXY MANAGER
# =============================================================================

class ProxyManager:
    """Quản lý proxy rotation"""
    
    def __init__(self):
        self.proxy_list = [proxy for proxy in Config.PROXY_LIST if proxy.strip()]
        self.current_proxy_index = 0
        self.failed_proxies = set()
        self.logger = logging.getLogger("ProxyManager")
        self.free_proxy_manager = FreeProxyManager()
        self.last_fetch_time = None
        
        if self.proxy_list:
            self.logger.info(f"Initialized with {len(self.proxy_list)} manual proxies")
        else:
            self.logger.info("No manual proxies configured")
        
        # Tự động fetch proxy free nếu được bật
        if Config.AUTO_FETCH_FREE_PROXY:
            self.logger.info("Auto-fetch free proxies is enabled")
    
    def get_next_proxy(self) -> Optional[str]:
        """Lấy proxy tiếp theo trong danh sách"""
        if not self.proxy_list:
            return None
        
        # Lọc bỏ các proxy đã fail
        available_proxies = [p for p in self.proxy_list if p not in self.failed_proxies]
        
        if not available_proxies:
            # Reset failed proxies nếu tất cả đều fail
            self.logger.warning("All proxies failed, resetting failed list")
            self.failed_proxies.clear()
            available_proxies = self.proxy_list
        
        if not available_proxies:
            return None
        
        # Lấy proxy tiếp theo
        proxy = available_proxies[self.current_proxy_index % len(available_proxies)]
        self.current_proxy_index += 1
        
        return proxy
    
    def get_random_proxy(self) -> Optional[str]:
        """Lấy proxy ngẫu nhiên"""
        if not self.proxy_list:
            return None
        
        available_proxies = [p for p in self.proxy_list if p not in self.failed_proxies]
        
        if not available_proxies:
            self.failed_proxies.clear()
            available_proxies = self.proxy_list
        
        if not available_proxies:
            return None
        
        return random.choice(available_proxies)
    
    def mark_proxy_failed(self, proxy: str):
        """Đánh dấu proxy bị lỗi"""
        if proxy:
            self.failed_proxies.add(proxy)
            self.logger.warning(f"Marked proxy as failed: {proxy}")
    
    def is_proxy_available(self) -> bool:
        """Kiểm tra có proxy nào khả dụng không"""
        if not self.proxy_list:
            return False
        
        available_proxies = [p for p in self.proxy_list if p not in self.failed_proxies]
        return len(available_proxies) > 0
    
    async def fetch_free_proxies(self) -> List[str]:
        """Fetch proxy free từ các nguồn"""
        if not Config.AUTO_FETCH_FREE_PROXY:
            return []
        
        # Kiểm tra thời gian fetch cuối cùng
        now = datetime.now()
        if (self.last_fetch_time and 
            (now - self.last_fetch_time).total_seconds() < Config.PROXY_FETCH_INTERVAL):
            return []
        
        self.logger.info("Fetching free proxies...")
        free_proxies = await self.free_proxy_manager.fetch_and_test_proxies()
        
        if free_proxies:
            # Thêm proxy free vào danh sách
            self.proxy_list.extend(free_proxies)
            # Loại bỏ duplicate
            self.proxy_list = list(set(self.proxy_list))
            self.last_fetch_time = now
            
            self.logger.info(f"Added {len(free_proxies)} free proxies. Total proxies: {len(self.proxy_list)}")
        
        return free_proxies
    
    def get_stats(self) -> Dict[str, Any]:
        """Lấy thống kê proxy"""
        return {
            "total_proxies": len(self.proxy_list),
            "available_proxies": len([p for p in self.proxy_list if p not in self.failed_proxies]),
            "failed_proxies": len(self.failed_proxies),
            "current_index": self.current_proxy_index,
            "proxy_rotation_enabled": Config.USE_PROXY_ROTATION,
            "auto_fetch_enabled": Config.AUTO_FETCH_FREE_PROXY,
            "last_fetch_time": self.last_fetch_time.isoformat() if self.last_fetch_time else None,
            "manual_proxies": len([p for p in Config.PROXY_LIST if p.strip()]),
            "free_proxies": len(self.proxy_list) - len([p for p in Config.PROXY_LIST if p.strip()])
        }


# =============================================================================
# WEBSOCKET MANAGER
# =============================================================================

class WebSocketManager:
    """Quản lý kết nối WebSocket"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.logger = logging.getLogger("WebSocketManager")
    
    async def connect(self, websocket: WebSocket):
        """Kết nối WebSocket mới"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Ngắt kết nối WebSocket"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Gửi tin nhắn đến một WebSocket cụ thể"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Gửi tin nhắn đến tất cả WebSocket đang kết nối"""
        if not self.active_connections:
            return
        
        message_str = json.dumps(message, ensure_ascii=False)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                self.logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Loại bỏ các kết nối bị lỗi
        for connection in disconnected:
            self.disconnect(connection)
        
        if self.active_connections:
            self.logger.info(f"Broadcasted message to {len(self.active_connections)} connections")


# =============================================================================
# CRAWLER CLASS
# =============================================================================

class WillhabenCrawler:
    """Crawler chính cho Willhaben.at"""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
        self.proxy_manager = ProxyManager()
        self.seen_ids: Set[str] = set()
        self.total_crawled = 0
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_agent = UserAgent()
        self.logger = logging.getLogger("WillhabenCrawler")
        self.is_running = False
        
        # Thống kê
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "new_items_found": 0,
            "last_crawl_time": None,
            "start_time": datetime.now()
        }
    
    async def create_session(self):
        """Tạo aiohttp session với cấu hình"""
        timeout = aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
    
    async def close_session(self):
        """Đóng aiohttp session"""
        if self.session:
            await self.session.close()
    
    def get_random_headers(self) -> Dict[str, str]:
        """Tạo headers ngẫu nhiên để tránh detection"""
        headers = {
            'User-Agent': self.user_agent.random if Config.USER_AGENT_ROTATION else self.user_agent.chrome,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        return headers
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch một trang web với proxy rotation"""
        if not self.session:
            await self.create_session()
        
        headers = self.get_random_headers()
        
        # Lấy proxy nếu có
        proxy = None
        if Config.USE_PROXY_ROTATION and self.proxy_manager.is_proxy_available():
            proxy = self.proxy_manager.get_random_proxy()
            if proxy:
                self.logger.debug(f"Using proxy: {proxy}")
        
        try:
            self.stats["total_requests"] += 1
            
            # Tạo timeout riêng cho proxy
            timeout = aiohttp.ClientTimeout(total=Config.PROXY_TIMEOUT if proxy else Config.REQUEST_TIMEOUT)
            
            async with self.session.get(url, headers=headers, proxy=proxy, timeout=timeout) as response:
                if response.status == 200:
                    self.stats["successful_requests"] += 1
                    content = await response.text()
                    self.logger.debug(f"Successfully fetched {url} via {proxy or 'direct'}")
                    return content
                else:
                    self.stats["failed_requests"] += 1
                    self.logger.warning(f"HTTP {response.status} for {url} via {proxy or 'direct'}")
                    
                    # Đánh dấu proxy fail nếu có lỗi
                    if proxy and response.status in [403, 407, 502, 503]:
                        self.proxy_manager.mark_proxy_failed(proxy)
                    
                    return None
        except Exception as e:
            self.stats["failed_requests"] += 1
            self.logger.error(f"Error fetching {url} via {proxy or 'direct'}: {e}")
            
            # Đánh dấu proxy fail nếu có exception
            if proxy:
                self.proxy_manager.mark_proxy_failed(proxy)
            
            return None
    
    def parse_car_listings(self, html: str) -> List[Dict[str, Any]]:
        """Parse HTML để trích xuất thông tin xe"""
        soup = BeautifulSoup(html, 'html.parser')  # Sử dụng html.parser thay vì lxml
        listings = []
        
        try:
            # Tìm các container chứa thông tin xe
            # Cấu trúc có thể thay đổi, cần điều chỉnh theo thực tế
            car_containers = soup.find_all('div', class_=lambda x: x and 'search-result' in x.lower())
            
            if not car_containers:
                # Thử các selector khác
                car_containers = soup.find_all('div', {'data-testid': lambda x: x and 'result' in x.lower()})
            
            if not car_containers:
                # Fallback: tìm tất cả div có chứa thông tin xe
                car_containers = soup.find_all('div', class_=lambda x: x and any(
                    keyword in x.lower() for keyword in ['item', 'listing', 'ad', 'result']
                ))
            
            self.logger.info(f"Found {len(car_containers)} potential car listings")
            
            for container in car_containers:
                try:
                    listing = self.extract_car_info(container)
                    if listing and listing.get('id'):
                        listings.append(listing)
                except Exception as e:
                    self.logger.debug(f"Error parsing container: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Error parsing HTML: {e}")
        
        return listings
    
    def parse_next_data(self, html: str) -> List[Dict[str, Any]]:
        """Parse dữ liệu từ __NEXT_DATA__ script tag"""
        soup = BeautifulSoup(html, 'html.parser')
        listings = []
        
        try:
            # Tìm script tag chứa __NEXT_DATA__
            next_data_script = soup.find('script', id='__NEXT_DATA__')
            
            if not next_data_script or not next_data_script.string:
                self.logger.warning("Không tìm thấy __NEXT_DATA__ script")
                return listings
            
            # Parse JSON data
            json_data = json.loads(next_data_script.string)
            
            # Trích xuất dữ liệu xe từ advertSummaryList
            try:
                advert_summary_list = json_data['props']['pageProps']['searchResult']['advertSummaryList']['advertSummary']
                self.logger.info(f"Tìm thấy {len(advert_summary_list)} xe trong __NEXT_DATA__")
                
                for advert in advert_summary_list:
                    try:
                        car_info = self.extract_car_from_advert(advert)
                        if car_info and car_info.get('id'):
                            listings.append(car_info)
                    except Exception as e:
                        self.logger.debug(f"Lỗi khi parse advert: {e}")
                        continue
                        
            except KeyError as e:
                self.logger.warning(f"Không tìm thấy advertSummaryList trong JSON: {e}")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Lỗi parse JSON từ __NEXT_DATA__: {e}")
        except Exception as e:
            self.logger.error(f"Lỗi khi parse __NEXT_DATA__: {e}")
        
        return listings
    
    def extract_car_from_advert(self, advert: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Trích xuất thông tin xe từ advert object"""
        try:
            car_info = {
                'id': str(advert.get('id', '')),
                'title': advert.get('description', ''),
                'url': advert.get('selfLink', ''),
                'status': advert.get('advertStatus', {}),
                'adTypeId': advert.get('adTypeId'),
                'productId': advert.get('productId'),
                'verticalId': advert.get('verticalId'),
                'crawled_at': datetime.now().isoformat()
            }
            
            # Trích xuất thông tin từ attributes
            if 'attributes' in advert and advert['attributes']:
                for attr in advert['attributes']:
                    if 'name' in attr and 'value' in attr:
                        attr_name = attr['name'].lower()
                        attr_value = attr['value']
                        
                        # Map các attributes phổ biến
                        if 'price' in attr_name or 'preis' in attr_name:
                            car_info['price'] = attr_value
                        elif 'year' in attr_name or 'jahr' in attr_name:
                            car_info['year'] = attr_value
                        elif 'km' in attr_name or 'kilometer' in attr_name:
                            car_info['mileage'] = attr_value
                        elif 'fuel' in attr_name or 'kraftstoff' in attr_name:
                            car_info['fuel'] = attr_value
                        elif 'power' in attr_name or 'leistung' in attr_name:
                            car_info['power'] = attr_value
                        elif 'transmission' in attr_name or 'getriebe' in attr_name:
                            car_info['transmission'] = attr_value
                        elif 'color' in attr_name or 'farbe' in attr_name:
                            car_info['color'] = attr_value
                        elif 'brand' in attr_name or 'marke' in attr_name:
                            car_info['brand'] = attr_value
                        elif 'model' in attr_name or 'modell' in attr_name:
                            car_info['model'] = attr_value
                        elif 'location' in attr_name or 'standort' in attr_name:
                            car_info['location'] = attr_value
            
            # Trích xuất thông tin từ teaserAttributes
            if 'teaserAttributes' in advert and advert['teaserAttributes']:
                for teaser in advert['teaserAttributes']:
                    if 'name' in teaser and 'value' in teaser:
                        teaser_name = teaser['name'].lower()
                        teaser_value = teaser['value']
                        
                        # Map các teaser attributes
                        if 'price' in teaser_name or 'preis' in teaser_name:
                            if 'price' not in car_info:
                                car_info['price'] = teaser_value
                        elif 'year' in teaser_name or 'jahr' in teaser_name:
                            if 'year' not in car_info:
                                car_info['year'] = teaser_value
                        elif 'km' in teaser_name or 'kilometer' in teaser_name:
                            if 'mileage' not in car_info:
                                car_info['mileage'] = teaser_value
            
            # Trích xuất thông tin từ advertiserInfo
            if 'advertiserInfo' in advert and advert['advertiserInfo']:
                advertiser = advert['advertiserInfo']
                if 'name' in advertiser:
                    car_info['dealer'] = advertiser['name']
                if 'location' in advertiser:
                    car_info['dealer_location'] = advertiser['location']
            
            # Trích xuất thông tin từ advertImageList
            if 'advertImageList' in advert and advert['advertImageList']:
                images = advert['advertImageList']
                if isinstance(images, list) and len(images) > 0:
                    car_info['images'] = images
            
            return car_info
            
        except Exception as e:
            self.logger.error(f"Lỗi khi extract car info từ advert: {e}")
            return None
    
    def extract_car_info(self, container) -> Optional[Dict[str, Any]]:
        """Trích xuất thông tin xe từ một container"""
        try:
            # Tìm ID của listing
            listing_id = None
            
            # Thử các cách khác nhau để lấy ID
            if container.get('data-adid'):
                listing_id = container.get('data-adid')
            elif container.get('id'):
                listing_id = container.get('id')
            else:
                # Tìm trong các thẻ con
                id_element = container.find(['a', 'div'], {'data-adid': True})
                if id_element:
                    listing_id = id_element.get('data-adid')
            
            if not listing_id:
                return None
            
            # Trích xuất thông tin cơ bản
            title_element = container.find(['h2', 'h3', 'a'], class_=lambda x: x and 'title' in x.lower())
            title = title_element.get_text(strip=True) if title_element else "N/A"
            
            # Tìm giá
            price_element = container.find(['span', 'div'], class_=lambda x: x and 'price' in x.lower())
            price = price_element.get_text(strip=True) if price_element else "N/A"
            
            # Tìm năm sản xuất
            year_element = container.find(['span', 'div'], class_=lambda x: x and 'year' in x.lower())
            year = year_element.get_text(strip=True) if year_element else "N/A"
            
            # Tìm kilomet
            km_element = container.find(['span', 'div'], class_=lambda x: x and ('km' in x.lower() or 'mileage' in x.lower()))
            km = km_element.get_text(strip=True) if km_element else "N/A"
            
            # Tìm link chi tiết
            link_element = container.find('a', href=True)
            link = urljoin(Config.BASE_URL, link_element['href']) if link_element else None
            
            # Tìm hình ảnh
            img_element = container.find('img', src=True)
            image_url = img_element['src'] if img_element else None
            
            return {
                'id': str(listing_id),
                'title': title,
                'price': price,
                'year': year,
                'km': km,
                'link': link,
                'image_url': image_url,
                'crawled_at': datetime.now().isoformat(),
                'source': 'willhaben.at'
            }
            
        except Exception as e:
            self.logger.debug(f"Error extracting car info: {e}")
            return None
    
    async def crawl_once(self) -> List[Dict[str, Any]]:
        """Thực hiện một lần crawl"""
        self.logger.info("Starting crawl cycle...")
        
        html = await self.fetch_page(Config.BASE_URL)
        if not html:
            self.logger.warning("Failed to fetch page")
            return []
        
        # Thử parse từ __NEXT_DATA__ trước (phương pháp mới)
        listings = self.parse_next_data(html)
        
        # Nếu không có dữ liệu từ __NEXT_DATA__, fallback về phương pháp cũ
        if not listings:
            self.logger.info("No data from __NEXT_DATA__, trying fallback method...")
            listings = self.parse_car_listings(html)
        
        self.logger.info(f"Parsed {len(listings)} listings")
        
        # Phát hiện tin mới
        new_listings = []
        for listing in listings:
            if listing['id'] not in self.seen_ids:
                self.seen_ids.add(listing['id'])
                new_listings.append(listing)
                self.stats["new_items_found"] += 1
                self.logger.info(f"New listing found: {listing.get('title', 'N/A')} - {listing.get('price', 'N/A')}")
        
        self.total_crawled += len(listings)
        self.stats["last_crawl_time"] = datetime.now()
        
        return new_listings
    
    async def crawl_loop(self):
        """Vòng lặp crawl chính"""
        self.is_running = True
        self.logger.info("Starting crawler loop...")
        
        # Fetch proxy free lần đầu
        if Config.AUTO_FETCH_FREE_PROXY:
            await self.proxy_manager.fetch_free_proxies()
        
        while self.is_running:
            try:
                start_time = time.time()
                
                # Fetch proxy free định kỳ
                if Config.AUTO_FETCH_FREE_PROXY:
                    await self.proxy_manager.fetch_free_proxies()
                
                # Thực hiện crawl
                new_listings = await self.crawl_once()
                
                # Gửi tin mới qua WebSocket
                if new_listings:
                    for listing in new_listings:
                        await self.websocket_manager.broadcast({
                            'type': 'new_listing',
                            'data': listing,
                            'timestamp': datetime.now().isoformat()
                        })
                
                # Tính thời gian crawl
                crawl_time = time.time() - start_time
                self.logger.info(f"Crawl completed in {crawl_time:.2f}s. Found {len(new_listings)} new listings")
                
                # Random delay để tránh bị chặn
                delay = random.uniform(Config.MIN_DELAY, Config.MAX_DELAY)
                await asyncio.sleep(Config.CRAWL_INTERVAL + delay)
                
            except Exception as e:
                self.logger.error(f"Error in crawl loop: {e}")
                await asyncio.sleep(Config.CRAWL_INTERVAL)
    
    def stop(self):
        """Dừng crawler"""
        self.is_running = False
        self.logger.info("Crawler stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Lấy thống kê crawler"""
        uptime = datetime.now() - self.stats["start_time"]
        proxy_stats = self.proxy_manager.get_stats()
        
        return {
            "is_running": self.is_running,
            "total_crawled": self.total_crawled,
            "seen_ids_count": len(self.seen_ids),
            "uptime_seconds": uptime.total_seconds(),
            "stats": self.stats,
            "proxy_stats": proxy_stats,
            "cars_crawled": len(self.seen_ids),
            "last_crawl_time": self.stats["last_crawl_time"].isoformat() if self.stats["last_crawl_time"] else None
        }


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

# Khởi tạo ứng dụng
app = FastAPI(
    title="Willhaben.at Realtime Crawler",
    description="Backend realtime crawl dữ liệu từ Willhaben.at",
    version="1.0.0"
)

# Khởi tạo các component
websocket_manager = WebSocketManager()
crawler = WillhabenCrawler(websocket_manager)


@app.on_event("startup")
async def startup_event():
    """Khởi tạo khi ứng dụng bắt đầu"""
    logger.info("Starting Willhaben Crawler Backend...")
    
    # Tạo crawler session
    await crawler.create_session()
    
    # Bắt đầu crawler loop
    asyncio.create_task(crawler.crawl_loop())
    
    logger.info("Backend started successfully!")


@app.on_event("shutdown")
async def shutdown_event():
    """Dọn dẹp khi ứng dụng tắt"""
    logger.info("Shutting down...")
    
    # Dừng crawler
    crawler.stop()
    
    # Đóng session
    await crawler.close_session()
    
    logger.info("Backend stopped!")


@app.get("/")
async def root():
    """Trang chủ"""
    return {
        "message": "Willhaben.at Realtime Crawler Backend",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "test": "/test",
            "websocket": "/ws"
        }
    }


@app.get("/health")
async def health():
    """Endpoint health check"""
    stats = crawler.get_stats()
    proxy_stats = stats["proxy_stats"]
    
    return {
        "status": "healthy",
        "crawler_running": crawler.is_running,
        "total_seen_items": len(crawler.seen_ids),
        "total_crawled": crawler.total_crawled,
        "cars_crawled": stats["cars_crawled"],
        "new_items_found": stats["stats"]["new_items_found"],
        "uptime_seconds": stats["uptime_seconds"],
        "last_crawl_time": stats["last_crawl_time"],
        "websocket_connections": len(websocket_manager.active_connections),
        "proxy_rotation": {
            "enabled": proxy_stats["proxy_rotation_enabled"],
            "total_proxies": proxy_stats["total_proxies"],
            "available_proxies": proxy_stats["available_proxies"],
            "failed_proxies": proxy_stats["failed_proxies"]
        }
    }


@app.get("/cars")
async def get_cars():
    """Lấy danh sách xe đã crawl"""
    return {
        "total_cars": len(crawler.seen_ids),
        "cars": list(crawler.seen_ids),
        "last_crawl_time": crawler.get_stats()["last_crawl_time"]
    }


@app.get("/proxy/stats")
async def proxy_stats():
    """Lấy thống kê proxy"""
    return crawler.proxy_manager.get_stats()


@app.post("/proxy/reset")
async def reset_failed_proxies():
    """Reset danh sách proxy bị lỗi"""
    crawler.proxy_manager.failed_proxies.clear()
    return {"message": "Failed proxies reset successfully"}


@app.post("/proxy/fetch")
async def fetch_free_proxies():
    """Fetch proxy free thủ công"""
    try:
        free_proxies = await crawler.proxy_manager.fetch_free_proxies()
        return {
            "message": f"Successfully fetched {len(free_proxies)} free proxies",
            "new_proxies": len(free_proxies),
            "total_proxies": len(crawler.proxy_manager.proxy_list)
        }
    except Exception as e:
        return {"error": f"Failed to fetch proxies: {str(e)}"}


@app.get("/proxy/list")
async def list_proxies():
    """Xem danh sách proxy hiện tại"""
    return {
        "total_proxies": len(crawler.proxy_manager.proxy_list),
        "available_proxies": len([p for p in crawler.proxy_manager.proxy_list if p not in crawler.proxy_manager.failed_proxies]),
        "failed_proxies": len(crawler.proxy_manager.failed_proxies),
        "proxy_list": crawler.proxy_manager.proxy_list[:10],  # Chỉ hiển thị 10 proxy đầu
        "failed_list": list(crawler.proxy_manager.failed_proxies)[:10]  # Chỉ hiển thị 10 proxy fail đầu
    }


@app.get("/test", response_class=HTMLResponse)
async def test_page():
    """Trang test WebSocket"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Willhaben Crawler Test</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .status {
                padding: 10px;
                margin: 10px 0;
                border-radius: 4px;
                font-weight: bold;
            }
            .connected { background-color: #d4edda; color: #155724; }
            .disconnected { background-color: #f8d7da; color: #721c24; }
            .listing {
                border: 1px solid #ddd;
                margin: 10px 0;
                padding: 15px;
                border-radius: 6px;
                background-color: #f9f9f9;
            }
            .listing h3 { margin-top: 0; color: #333; }
            .listing .price { font-size: 18px; font-weight: bold; color: #e74c3c; }
            .listing .details { color: #666; margin: 5px 0; }
            .listing .link { color: #007bff; text-decoration: none; }
            .listing .link:hover { text-decoration: underline; }
            .timestamp { font-size: 12px; color: #999; }
            #messages {
                max-height: 600px;
                overflow-y: auto;
                border: 1px solid #ddd;
                padding: 10px;
                background-color: white;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚗 Willhaben.at Realtime Crawler Test</h1>
            
            <div id="status" class="status disconnected">
                WebSocket: Disconnected
            </div>
            
            <div>
                <h3>📊 Statistics</h3>
                <p>Total items seen: <span id="total-items">0</span></p>
                <p>Cars crawled: <span id="cars-crawled">0</span></p>
                <p>New items found: <span id="new-items">0</span></p>
                <p>Last update: <span id="last-update">Never</span></p>
                
                <h4>🔄 Proxy Status</h4>
                <p>Proxy Rotation: <span id="proxy-enabled">Disabled</span></p>
                <p>Available Proxies: <span id="proxy-available">0</span></p>
                <p>Failed Proxies: <span id="proxy-failed">0</span></p>
                <p>Auto Fetch: <span id="proxy-auto-fetch">Disabled</span></p>
                <p>Free Proxies: <span id="proxy-free">0</span></p>
                <p>Manual Proxies: <span id="proxy-manual">0</span></p>
                <button onclick="fetchProxies()" style="margin: 5px; padding: 5px 10px;">Fetch Free Proxies</button>
                <button onclick="resetProxies()" style="margin: 5px; padding: 5px 10px;">Reset Failed</button>
            </div>
            
            <div>
                <h3>🆕 New Listings (Real-time)</h3>
                <div id="messages"></div>
            </div>
        </div>

        <script>
            let ws = null;
            let totalItems = 0;
            let newItems = 0;

            function connect() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function(event) {
                    document.getElementById('status').textContent = 'WebSocket: Connected';
                    document.getElementById('status').className = 'status connected';
                    console.log('WebSocket connected');
                };
                
                ws.onmessage = function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        if (data.type === 'new_listing') {
                            addNewListing(data.data);
                            newItems++;
                            document.getElementById('new-items').textContent = newItems;
                            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                        }
                    } catch (e) {
                        console.error('Error parsing message:', e);
                    }
                };
                
                ws.onclose = function(event) {
                    document.getElementById('status').textContent = 'WebSocket: Disconnected';
                    document.getElementById('status').className = 'status disconnected';
                    console.log('WebSocket disconnected');
                    
                    // Tự động kết nối lại sau 3 giây
                    setTimeout(connect, 3000);
                };
                
                ws.onerror = function(error) {
                    console.error('WebSocket error:', error);
                };
            }

            function addNewListing(listing) {
                const messagesDiv = document.getElementById('messages');
                const listingDiv = document.createElement('div');
                listingDiv.className = 'listing';
                
                listingDiv.innerHTML = `
                    <h3>${listing.title || 'N/A'}</h3>
                    <div class="price">${listing.price || 'N/A'}</div>
                    <div class="details">
                        <strong>ID:</strong> ${listing.id || 'N/A'} | 
                        <strong>Year:</strong> ${listing.year || 'N/A'} | 
                        <strong>Mileage:</strong> ${listing.mileage || 'N/A'} | 
                        <strong>Fuel:</strong> ${listing.fuel || 'N/A'}
                    </div>
                    <div class="details">
                        <strong>Brand:</strong> ${listing.brand || 'N/A'} | 
                        <strong>Model:</strong> ${listing.model || 'N/A'} | 
                        <strong>Location:</strong> ${listing.location || 'N/A'}
                    </div>
                    ${listing.url ? `<a href="${listing.url}" target="_blank" class="link">View Details</a>` : ''}
                    <div class="timestamp">Found at: ${new Date(listing.crawled_at).toLocaleString()}</div>
                `;
                
                messagesDiv.insertBefore(listingDiv, messagesDiv.firstChild);
                
                // Giới hạn số lượng tin hiển thị
                while (messagesDiv.children.length > 50) {
                    messagesDiv.removeChild(messagesDiv.lastChild);
                }
            }

            // Bắt đầu kết nối khi trang load
            connect();

            // Cập nhật thống kê định kỳ
            setInterval(async () => {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    document.getElementById('total-items').textContent = data.total_seen_items;
                    document.getElementById('cars-crawled').textContent = data.cars_crawled;
                    document.getElementById('new-items').textContent = data.new_items_found;
                    document.getElementById('last-update').textContent = data.last_crawl_time ? new Date(data.last_crawl_time).toLocaleTimeString() : 'Never';
                    
                    // Cập nhật thông tin proxy
                    document.getElementById('proxy-enabled').textContent = data.proxy_rotation.enabled ? 'Enabled' : 'Disabled';
                    document.getElementById('proxy-available').textContent = data.proxy_rotation.available_proxies;
                    document.getElementById('proxy-failed').textContent = data.proxy_rotation.failed_proxies;
                    document.getElementById('proxy-auto-fetch').textContent = data.proxy_rotation.auto_fetch_enabled ? 'Enabled' : 'Disabled';
                    document.getElementById('proxy-free').textContent = data.proxy_rotation.free_proxies || 0;
                    document.getElementById('proxy-manual').textContent = data.proxy_rotation.manual_proxies || 0;
                } catch (e) {
                    console.error('Error fetching stats:', e);
                }
            }, 5000);
            
            // Hàm fetch proxy free
            async function fetchProxies() {
                try {
                    const response = await fetch('/proxy/fetch', { method: 'POST' });
                    const data = await response.json();
                    alert(data.message || data.error);
                } catch (e) {
                    alert('Error fetching proxies: ' + e.message);
                }
            }
            
            // Hàm reset proxy bị lỗi
            async function resetProxies() {
                try {
                    const response = await fetch('/proxy/reset', { method: 'POST' });
                    const data = await response.json();
                    alert(data.message);
                } catch (e) {
                    alert('Error resetting proxies: ' + e.message);
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint cho realtime updates"""
    await websocket_manager.connect(websocket)
    
    try:
        # Gửi thông báo chào mừng
        await websocket_manager.send_personal_message(
            json.dumps({
                'type': 'welcome',
                'message': 'Connected to Willhaben Crawler',
                'timestamp': datetime.now().isoformat()
            }),
            websocket
        )
        
        # Giữ kết nối mở
        while True:
            try:
                # Đợi tin nhắn từ client (có thể là ping)
                data = await websocket.receive_text()
                
                # Phản hồi ping
                if data == "ping":
                    await websocket_manager.send_personal_message("pong", websocket)
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        websocket_manager.disconnect(websocket)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    logger.info("Starting Willhaben Crawler Backend...")
    
    # Chạy server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )

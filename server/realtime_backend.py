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
import os
import random
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urljoin, urlparse
import multiprocessing
import queue as std_queue
import signal

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
    PROXY_LIST = [
        # Thêm proxy của bạn vào đây (tùy chọn)
        # "http://proxy1:port",
        # "http://proxy2:port",
        # "http://proxy3:port",
        # "http://username:password@proxy4:port"
    ]
    PROXY_TIMEOUT = 10  # Timeout cho proxy requests
    MAX_FREE_PROXIES = 10  # Số lượng proxy free tối đa
    PROXY_FETCH_INTERVAL = 10  # Thời gian fetch proxy mới (giây)
    
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
# PROXY MANAGER
# =============================================================================

def _mp_free_proxy_producer(base_url: str, out_q: multiprocessing.Queue, stop_event: multiprocessing.Event, backoff_max: float = 60.0):
    """Tiến trình producer: liên tục fetch proxy free và đẩy vào hàng đợi."""
    # Đảm bảo tiến trình thoát khi nhận tín hiệu
    signal.signal(signal.SIGTERM, lambda *_: stop_event.set())
    signal.signal(signal.SIGINT, lambda *_: stop_event.set())
    try:
        try:
            from fp.fp import FreeProxy
        except ImportError:
            from fp import FreeProxy
    except Exception:
        FreeProxy = None  # type: ignore
    backoff = 1.0
    while not stop_event.is_set():
        try:
            proxy_str = None
            if FreeProxy is not None:
                try:
                    proxy = FreeProxy(url=base_url)
                    proxy_str = proxy.get()
                except Exception:
                    proxy_str = None
            if proxy_str:
                if not proxy_str.startswith('http'):
                    proxy_str = f"http://{proxy_str}"
                try:
                    out_q.put(proxy_str, block=False)
                except Exception:
                    time.sleep(0.1)
                backoff = 1.0
                time.sleep(0.05)
            else:
                time.sleep(backoff)
                backoff = min(backoff_max, backoff * 2)
        except KeyboardInterrupt:
            break
        except Exception:
            time.sleep(backoff)
            backoff = min(backoff_max, backoff * 2)

class ProxyManager:
    """Quản lý proxy: user proxies (nếu bật) và pool free-proxy chạy nền (multiprocess)."""
    
    def __init__(self):
        self.proxy_list = [proxy for proxy in Config.PROXY_LIST if proxy.strip()]
        self.current_proxy_index = 0
        self.logger = logging.getLogger("ProxyManager")
        self.last_fetch_time = None
        # Pool proxy free chạy nền (tối đa MAX_FREE_PROXIES)
        self.free_proxies: List[str] = []
        self._pool_lock = asyncio.Lock()
        self._stopping = False
        # Multiprocessing producer/consumer
        self._mp_queue: Optional[multiprocessing.Queue] = None
        self._mp_proc: Optional[multiprocessing.Process] = None
        self._consumer_task: Optional[asyncio.Task] = None
        self._mp_stop: Optional[multiprocessing.Event] = None
    
    def get_random_proxy(self) -> Optional[str]:
        """Lấy proxy ngẫu nhiên"""
        if not self.proxy_list:
            return None
        
        if not self.proxy_list:
            return None
        
        return random.choice(self.proxy_list)
    
    def _parse_proxy_ip(self, proxy: str) -> str:
        """Parse IP/host từ proxy URL"""
        try:
            parsed = urlparse(proxy)
            if parsed.hostname:
                return parsed.hostname
            elif '@' in parsed.netloc:
                return parsed.netloc.split('@')[-1].split(':')[0]
            else:
                return parsed.netloc.split(':')[0]
        except:
            try:
                if '@' in proxy:
                    return proxy.split('@')[-1].split(':')[0]
                else:
                    return proxy.split('://')[-1].split(':')[0]
            except:
                return proxy
    
    def mark_proxy_failed(self, proxy: str):
        """Loại bỏ proxy lỗi khỏi pool free (producer sẽ tiếp tục bổ sung)."""
        if not proxy:
            return
        try:
            if proxy:
                proxy_ip = self.proxy_manager._parse_proxy_ip(proxy)
                self.logger.error(f"Error fetching via Proxy IP: {proxy_ip}")
            if proxy in self.free_proxies:
                self.free_proxies = [p for p in self.free_proxies if p != proxy]
        except Exception:
            pass

    def get_random_free_proxy(self) -> Optional[str]:
        """Chọn ngẫu nhiên proxy từ danh sách free_proxies (nếu có)."""
        if not self.free_proxies:
            return None
        return random.choice(self.free_proxies)

    # async def _get_free_proxy_from_library_async(self) -> Optional[str]:
    #     """Không dùng trong chế độ multiprocessing (chỉ để fallback nếu cần)."""
    #     if self._stopping:
    #         return None
    #     try:
    #         return await asyncio.wait_for(asyncio.to_thread(self.get_free_proxy_from_library), timeout=2.0)
    #     except (asyncio.TimeoutError, asyncio.CancelledError):
    #         return None

    async def _drain_queue_once(self):
        """Lấy proxy từ queue và cập nhật pool (không block)."""
        if self._mp_queue is None:
            return
        try:
            while len(self.free_proxies) < Config.MAX_FREE_PROXIES:
                try:
                    proxy = self._mp_queue.get_nowait()
                except std_queue.Empty:
                    break
                if not proxy:
                    break
                async with self._pool_lock:
                    if proxy not in self.free_proxies:
                        self.free_proxies.append(proxy)
                        if len(self.free_proxies) > Config.MAX_FREE_PROXIES:
                            self.free_proxies = self.free_proxies[-Config.MAX_FREE_PROXIES:]
        except Exception as e:
            self.logger.debug(f"Error draining proxy queue: {e}")

    async def _consumer_loop(self):
        """Tiêu thụ proxy từ queue để duy trì pool free_proxies."""
        self.logger.info("Starting free proxy consumer loop")
        try:
            # Drain ngay khi khởi động để có proxy sớm
            await self._drain_queue_once()
            while not self._stopping:
                await self._drain_queue_once()
                await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            self.logger.info("Free proxy consumer loop stopped")
            raise
        except Exception as e:
            self.logger.error(f"Free proxy consumer loop error: {e}")

    def start_free_proxy_fetcher(self):
        """Khởi động producer process và consumer loop cho pool proxy free."""
        if Config.USE_PROXY_ROTATION and len(Config.PROXY_LIST) > 0:
            return
        self._stopping = False
        # Khởi động producer nếu chưa
        if not (self._mp_proc and self._mp_proc.is_alive()):
            self._mp_queue = multiprocessing.Queue(maxsize=Config.MAX_FREE_PROXIES * 4)
            self._mp_stop = multiprocessing.Event()
            self._mp_proc = multiprocessing.Process(
                target=_mp_free_proxy_producer,
                args=(Config.BASE_URL, self._mp_queue, self._mp_stop, 60.0),
                daemon=True,
            )
            self._mp_proc.start()
        # Khởi động consumer nếu chưa
        if not self._consumer_task or self._consumer_task.done():
            self._consumer_task = asyncio.create_task(self._consumer_loop())

    async def stop_free_proxy_fetcher(self):
        """Dừng vòng lặp fetch proxy free và tiến trình producer."""
        self._stopping = True
        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        # Dừng tiến trình producer
        if self._mp_stop:
            try:
                self._mp_stop.set()
            except Exception:
                pass
        if self._mp_proc and self._mp_proc.is_alive():
            # Chờ tiến trình thoát nhẹ nhàng
            self._mp_proc.join(timeout=1.0)
        if self._mp_proc and self._mp_proc.is_alive():
            # Ép terminate nếu vẫn còn sống
            try:
                self._mp_proc.terminate()
            except Exception:
                pass
            self._mp_proc.join(timeout=1.0)
        if self._mp_proc and self._mp_proc.is_alive():
            # Kill cứng nếu vẫn chưa thoát
            try:
                self._mp_proc.kill()
            except Exception:
                pass
            self._mp_proc.join(timeout=0.5)
        self._mp_proc = None
        self._mp_queue = None
        self._mp_stop = None
    
    def get_free_proxy_from_library(self) -> Optional[str]:
        """Lấy proxy free từ thư viện free-proxy"""
        try:
            try:
                from fp.fp import FreeProxy
            except ImportError:
                from fp import FreeProxy
            
            # Kiểm tra cache và lọc bỏ proxy đã fail
            now = datetime.now()
            self.logger.info(f"Fetching new free proxy from library... | Time: {now}")
            # Lấy proxy mới từ thư viện
            # self.logger.debug("Fetching new free proxy from library...")
            proxy = FreeProxy(url=Config.BASE_URL,)
            proxy_str = proxy.get()
            
            if proxy_str:
                # Format: http://ip:port
                if not proxy_str.startswith('http'):
                    proxy_str = f"http://{proxy_str}"
                
                # proxy_ip = self._parse_proxy_ip(proxy_str)
                # self.logger.info(f"Got new free proxy from library - IP: {proxy_ip} | URL: {proxy_str}")
                return proxy_str
            else:
                self.logger.warning("No proxy available from free-proxy library")
                return None
                
        except ImportError:
            self.logger.error("free-proxy library not installed. Install with: pip install free-proxy")
            return None
        except Exception as e:
            self.logger.error(f"Error getting free proxy from library: {e}")
            return None

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
    
    def disconnect(self, websocket: WebSocket):
        """Ngắt kết nối WebSocket"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
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
            self.logger.warning("No active WebSocket connections to broadcast to")
            return
        
        try:
            message_str = json.dumps(message, ensure_ascii=False)
            message_type = message.get('type', 'unknown')
            message_count = message.get('count', 0) if 'count' in message else (len(message.get('data', [])) if 'data' in message else 0)
            # self.logger.info(f"Broadcasting {message_type} to {len(self.active_connections)} connection(s) with {message_count} items")
        except Exception as e:
            self.logger.error(f"Error serializing broadcast message: {e}")
            return
        
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
        
        if disconnected:
            self.logger.info(f"Removed {len(disconnected)} disconnected connections")
        


# =============================================================================
# CRAWLER CLASS
# =============================================================================

class WillhabenCrawler:
    """Crawler chính cho Willhaben.at"""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
        self.proxy_manager = ProxyManager()
        self.seen_ids: Set[str] = set()
        self.all_listings: List[Dict[str, Any]] = []  # Lưu trữ tất cả listings đã crawl
        self.new_listings_array: List[Dict[str, Any]] = []  # Array lưu new_listings để broadcast
        self.total_crawled = 0
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_agent = UserAgent()
        self.logger = logging.getLogger("WillhabenCrawler")
        self.is_running = False
        self.max_new_listings = 1000  # Giới hạn số lượng new_listings
    
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
    
    async def fetch_page(self, url: str,useProxy: bool = True) -> Optional[str]:
        """Fetch một trang web với proxy rotation"""
        if not self.session:
            await self.create_session()
        
        headers = self.get_random_headers()
        
        proxy = None
        
        if Config.USE_PROXY_ROTATION and len(Config.PROXY_LIST) > 0:
            proxy = self.proxy_manager.get_random_proxy()
            if proxy:
                proxy_ip = self.proxy_manager._parse_proxy_ip(proxy)
                self.logger.info(f"Fetching data using Proxy IP: {proxy_ip} | Proxy URL: {proxy}")
        elif useProxy:
            # Chọn proxy free từ danh sách nền (nếu có); nếu rỗng thì không dùng proxy
            proxy = self.proxy_manager.get_random_free_proxy()
            # log thong tin proxy cho toi
            try:
                pool_size = len(self.proxy_manager.free_proxies)
            except Exception:
                pool_size = 0
            self.logger.info(f"Free proxy pool size: {pool_size} | Mode: {'proxy' if proxy else 'None'}")
            if proxy:
                proxy_ip = self.proxy_manager._parse_proxy_ip(proxy)
                self.logger.info(f"Fetching data using Free Proxy IP: {proxy_ip} | Proxy URL: {proxy}")
        
        try:
            
            # Tạo timeout riêng cho proxy
            timeout = aiohttp.ClientTimeout(total=Config.PROXY_TIMEOUT if proxy else Config.REQUEST_TIMEOUT)
            
            async with self.session.get(url, headers=headers, proxy=proxy, timeout=timeout) as response:
                if response.status == 200:
                    content = await response.text()
                    # if proxy:
                    #     proxy_ip = self.proxy_manager._parse_proxy_ip(proxy)
                    #     self.logger.info(f"Successfully fetched data via Proxy IP: {proxy_ip} | URL: {url}")
                    # else:
                    #     self.logger.debug(f"Successfully fetched {url} via direct connection")
                    return content
                else:
                    # if proxy:
                    #     proxy_ip = self.proxy_manager._parse_proxy_ip(proxy)
                        # self.logger.warning(f"HTTP {response.status} for {url} via Proxy IP: {proxy_ip}")
                    # else:
                        # self.logger.warning(f"HTTP {response.status} for {url} via direct connection")
                    
                    self.proxy_manager.mark_proxy_failed(proxy)
                    
                    return await self.fetch_page(url,useProxy=False)
        except Exception as e:
            # if proxy:
            #     proxy_ip = self.proxy_manager._parse_proxy_ip(proxy)
            #     self.logger.error(f"Error fetching {url} via Proxy IP: {proxy_ip} | Error: {e}")
            # else:
            #     self.logger.error(f"Error fetching {url} via direct connection: {e}")
            
            self.proxy_manager.mark_proxy_failed(proxy)
            
            return await self.fetch_page(url,useProxy=False)
    
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
                
                for advert in advert_summary_list:
                    try:
                        car_model = self.extract_car_from_advert(advert)
                        if car_model and car_model.get('id'):
                            # Ghi advert vào file để trace theo ID
                            #self.log_advert_to_file(advert, car_model)
                            listings.append(car_model)
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
    
    def log_advert_to_file(self, advert: Dict[str, Any], car_model: Dict[str, Any]) -> None:
        """Ghi thông tin advert vào file để trace theo ID"""
        try:
            # Tạo thư mục logs nếu chưa có
            logs_dir = "logs"
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir)
            
            # Tạo tên file theo ID của advert
            advert_id = car_model.get('id', 'unknown')
            log_filename = os.path.join(logs_dir, f"advert_{advert_id}.json")
            
            # Chuẩn bị dữ liệu để ghi
            log_data = {
                'timestamp': datetime.now().isoformat(),
                'advert_id': advert_id,
                'car_model': car_model,
                'raw_advert': advert,
                'crawled_at': datetime.now().isoformat()
            }
            
            # Ghi vào file JSON
            with open(log_filename, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            
            
            # Cập nhật file tổng hợp
            self.update_summary_log(advert_id, car_model)
            
        except Exception as e:
            self.logger.error(f"Lỗi khi ghi advert vào file: {e}")
    
    def update_summary_log(self, advert_id: str, car_model: Dict[str, Any]) -> None:
        """Cập nhật file tổng hợp tất cả adverts đã tìm thấy"""
        try:
            logs_dir = "logs"
            summary_file = os.path.join(logs_dir, "adverts_summary.json")
            
            # Đọc dữ liệu hiện tại nếu file đã tồn tại
            summary_data = []
            if os.path.exists(summary_file):
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summary_data = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    summary_data = []
            
            # Thêm thông tin advert mới
            advert_entry = {
                'advert_id': advert_id,
                'title': car_model.get('title', ''),
                'make': car_model.get('car_info', {}).get('make', ''),
                'model': car_model.get('car_info', {}).get('model', ''),
                'year': car_model.get('car_info', {}).get('year', ''),
                'mileage': car_model.get('car_info', {}).get('mileage', ''),
                'fuel_type': car_model.get('car_info', {}).get('fuel_type_resolved', ''),
                'transmission': car_model.get('car_info', {}).get('transmission_resolved', ''),
                'price': car_model.get('pricing', {}).get('price_display', ''),
                'price_amount': car_model.get('pricing', {}).get('price_amount', ''),
                'location': car_model.get('location', {}).get('city', ''),
                'seller': car_model.get('seller', {}).get('org_name', ''),
                'url': car_model.get('url', ''),
                'first_seen': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat()
            }
            
            # Kiểm tra xem advert đã tồn tại chưa
            existing_index = None
            for i, entry in enumerate(summary_data):
                if entry.get('advert_id') == advert_id:
                    existing_index = i
                    break
            
            if existing_index is not None:
                # Cập nhật thời gian last_seen
                summary_data[existing_index]['last_seen'] = datetime.now().isoformat()
            else:
                # Thêm advert mới
                summary_data.append(advert_entry)
            
            # Ghi lại file tổng hợp
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            self.logger.error(f"Lỗi khi cập nhật summary log: {e}")
    
    def extract_car_from_advert(self, advert: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Trích xuất thông tin xe từ advert object thành model dữ liệu chi tiết"""
        try:
            # Tạo model dữ liệu chi tiết
            car_model = {
                # Thông tin cơ bản
                'id': str(advert.get('id', '')),
                'title': advert.get('description', ''),
                'url': advert.get('selfLink', ''),
                'seo_url': '',
                'crawled_at': datetime.now().isoformat(),
                
                # Thông tin trạng thái
                'status': {
                    'id': advert.get('advertStatus', {}).get('id', ''),
                    'description': advert.get('advertStatus', {}).get('description', ''),
                    'statusId': advert.get('advertStatus', {}).get('statusId', '')
                },
                
                # Thông tin phân loại
                'adTypeId': advert.get('adTypeId'),
                'productId': advert.get('productId'),
                'verticalId': advert.get('verticalId'),
                
                # Thông tin xe
                'car_info': {
                    'make': '',
                    'model': '',
                    'model_specification': '',
                    'year': '',
                    'mileage': '',
                    'fuel_type': '',
                    'fuel_type_resolved': '',
                    'transmission': '',
                    'transmission_resolved': '',
                    'condition': '',
                    'condition_resolved': '',
                    'car_type': '',
                    'exterior_color': '',
                    'engine_power': '',
                    'no_of_seats': '',
                    'warranty': '',
                    'warranty_resolved': ''
                },
                
                # Thông tin giá cả
                'pricing': {
                    'price': '',
                    'price_display': '',
                    'price_amount': '',
                    'is_private': False,
                    'motor_price_bonus_trade_in': False,
                    'motor_price_bonus_finance': False
                },
                
                # Thông tin địa điểm
                'location': {
                    'address': '',
                    'postcode': '',
                    'city': '',
                    'state': '',
                    'country': '',
                    'coordinates': '',
                    'district': ''
                },
                
                # Thông tin người bán
                'seller': {
                    'org_id': '',
                    'org_name': '',
                    'org_uuid': '',
                    'is_private': False,
                    'is_autodealer': False,
                    'logo_url': ''
                },
                
                # Thông tin hình ảnh
                'images': {
                    'main_image': '',
                    'thumbnail': '',
                    'all_images': [],
                    'image_count': 0
                },
                
                # Thông tin thiết bị/trang bị
                'equipment': {
                    'equipment_ids': '',
                    'equipment_resolved': []
                },
                
                # Thông tin thời gian
                'timing': {
                    'published': '',
                    'published_string': '',
                    'last_updated': '',
                    'is_bumped': False
                },
                
                # Thông tin bổ sung
                'additional': {
                    'defects_liability': False,
                    'condition_report': False,
                    'body_dyn': '',
                    'source': '',
                    'ad_uuid': '',
                    'fnmmocount': 0
                }
            }
            
            # Trích xuất thông tin từ attributes
            if 'attributes' in advert and advert['attributes']:
                attributes = advert['attributes'].get('attribute', [])
                for attr in attributes:
                    if 'name' in attr and 'values' in attr and attr['values']:
                        attr_name = attr['name']
                        attr_value = attr['values'][0] if attr['values'] else ''
                        
                        # Thông tin xe
                        if attr_name == 'CAR_MODEL/MAKE':
                            car_model['car_info']['make'] = attr_value
                        elif attr_name == 'CAR_MODEL/MODEL':
                            car_model['car_info']['model'] = attr_value
                        elif attr_name == 'CAR_MODEL/MODEL_SPECIFICATION':
                            car_model['car_info']['model_specification'] = attr_value
                        elif attr_name == 'YEAR_MODEL':
                            car_model['car_info']['year'] = attr_value
                        elif attr_name == 'MILEAGE':
                            car_model['car_info']['mileage'] = attr_value
                        elif attr_name == 'ENGINE/FUEL':
                            car_model['car_info']['fuel_type'] = attr_value
                        elif attr_name == 'ENGINE/FUEL_RESOLVED':
                            car_model['car_info']['fuel_type_resolved'] = attr_value
                        elif attr_name == 'TRANSMISSION':
                            car_model['car_info']['transmission'] = attr_value
                        elif attr_name == 'TRANSMISSION_RESOLVED':
                            car_model['car_info']['transmission_resolved'] = attr_value
                        elif attr_name == 'CONDITION':
                            car_model['car_info']['condition'] = attr_value
                        elif attr_name == 'CONDITION_RESOLVED':
                            car_model['car_info']['condition_resolved'] = attr_value
                        elif attr_name == 'CAR_TYPE':
                            car_model['car_info']['car_type'] = attr_value
                        elif attr_name == 'EXTERIORCOLOURMAIN':
                            car_model['car_info']['exterior_color'] = attr_value
                        elif attr_name == 'ENGINE/EFFECT':
                            car_model['car_info']['engine_power'] = attr_value
                        elif attr_name == 'NOOFSEATS':
                            car_model['car_info']['no_of_seats'] = attr_value
                        elif attr_name == 'WARRANTY':
                            car_model['car_info']['warranty'] = attr_value
                        elif attr_name == 'WARRANTY_RESOLVED':
                            car_model['car_info']['warranty_resolved'] = attr_value
                        
                        # Thông tin giá cả
                        elif attr_name == 'PRICE':
                            car_model['pricing']['price'] = attr_value
                        elif attr_name == 'PRICE_FOR_DISPLAY':
                            car_model['pricing']['price_display'] = attr_value
                        elif attr_name == 'PRICE/AMOUNT':
                            car_model['pricing']['price_amount'] = attr_value
                        elif attr_name == 'ISPRIVATE':
                            car_model['pricing']['is_private'] = attr_value == '1'
                        elif attr_name == 'MOTOR_PRICE_BONUS/TRADE_IN':
                            car_model['pricing']['motor_price_bonus_trade_in'] = attr_value.lower() == 'true'
                        elif attr_name == 'MOTOR_PRICE_BONUS/FINANCE':
                            car_model['pricing']['motor_price_bonus_finance'] = attr_value.lower() == 'true'
                        
                        # Thông tin địa điểm
                        elif attr_name == 'ADDRESS':
                            car_model['location']['address'] = attr_value
                        elif attr_name == 'POSTCODE':
                            car_model['location']['postcode'] = attr_value
                        elif attr_name == 'LOCATION':
                            car_model['location']['city'] = attr_value
                        elif attr_name == 'STATE':
                            car_model['location']['state'] = attr_value
                        elif attr_name == 'COUNTRY':
                            car_model['location']['country'] = attr_value
                        elif attr_name == 'COORDINATES':
                            car_model['location']['coordinates'] = attr_value
                        elif attr_name == 'DISTRICT':
                            car_model['location']['district'] = attr_value
                        
                        # Thông tin người bán
                        elif attr_name == 'ORGID':
                            car_model['seller']['org_id'] = attr_value
                        elif attr_name == 'ORGNAME':
                            car_model['seller']['org_name'] = attr_value
                        elif attr_name == 'ORG_UUID':
                            car_model['seller']['org_uuid'] = attr_value
                        elif attr_name == 'ISPRIVATE':
                            car_model['seller']['is_private'] = attr_value == '1'
                        elif attr_name == 'AUTDEALER':
                            car_model['seller']['is_autodealer'] = attr_value == '1'
                        elif attr_name == 'AD_SEARCHRESULT_LOGO':
                            car_model['seller']['logo_url'] = f"https://cache.willhaben.at/{attr_value}"
                        
                        # Thông tin thiết bị
                        elif attr_name == 'EQUIPMENT':
                            car_model['equipment']['equipment_ids'] = attr_value
                        elif attr_name == 'EQUIPMENT_RESOLVED':
                            car_model['equipment']['equipment_resolved'] = attr['values']
                        
                        # Thông tin thời gian
                        elif attr_name == 'PUBLISHED':
                            car_model['timing']['published'] = attr_value
                        elif attr_name == 'PUBLISHED_String':
                            car_model['timing']['published_string'] = attr_value
                        elif attr_name == 'LAST_UPDATED':
                            car_model['timing']['last_updated'] = attr_value
                        elif attr_name == 'IS_BUMPED':
                            car_model['timing']['is_bumped'] = attr_value == '1'
                        
                        # Thông tin bổ sung
                        elif attr_name == 'DEFECTS_LIABILITY':
                            car_model['additional']['defects_liability'] = attr_value == '1'
                        elif attr_name == 'CONDITION_REPORT':
                            car_model['additional']['condition_report'] = attr_value == '1'
                        elif attr_name == 'BODY_DYN':
                            car_model['additional']['body_dyn'] = attr_value
                        elif attr_name == 'SOURCE':
                            car_model['additional']['source'] = attr_value
                        elif attr_name == 'AD_UUID':
                            car_model['additional']['ad_uuid'] = attr_value
                        elif attr_name == 'fnmmocount':
                            car_model['additional']['fnmmocount'] = int(attr_value) if attr_value.isdigit() else 0
                        elif attr_name == 'SEO_URL':
                            car_model['seo_url'] = attr_value
            
            # Trích xuất thông tin hình ảnh
            if 'advertImageList' in advert and 'advertImage' in advert['advertImageList']:
                images = advert['advertImageList']['advertImage']
                if images:
                    # Kiểm tra nếu images là list hoặc dict
                    if isinstance(images, list):
                        if len(images) > 0:
                            first_image = images[0]
                            if isinstance(first_image, dict):
                                car_model['images']['main_image'] = first_image.get('mainImageUrl', first_image.get('href', ''))
                                car_model['images']['thumbnail'] = first_image.get('thumbnailImageUrl', first_image.get('mainImageUrl', first_image.get('href', '')))
                                car_model['images']['all_images'] = [img.get('mainImageUrl', img.get('href', '')) for img in images if isinstance(img, dict)]
                            else:
                                car_model['images']['main_image'] = str(first_image)
                                car_model['images']['thumbnail'] = str(first_image)
                    elif isinstance(images, dict):
                        car_model['images']['main_image'] = images.get('mainImageUrl', images.get('href', ''))
                        car_model['images']['thumbnail'] = images.get('thumbnailImageUrl', images.get('mainImageUrl', images.get('href', '')))
                    car_model['images']['image_count'] = len(images) if isinstance(images, list) else 1
            
            # Nếu không có ảnh từ advertImageList, thử tìm trong các field khác
            if not car_model['images']['main_image']:
                # Thử tìm trong attributes
                if 'attributes' in advert and advert['attributes']:
                    attributes = advert['attributes'].get('attribute', [])
                    for attr in attributes:
                        if 'name' in attr and 'values' in attr and attr['values']:
                            attr_name = attr['name']
                            if 'IMAGE' in attr_name.upper() or 'PHOTO' in attr_name.upper() or 'PICTURE' in attr_name.upper():
                                attr_value = attr['values'][0] if attr['values'] else ''
                                if attr_value:
                                    car_model['images']['main_image'] = attr_value
                                    car_model['images']['thumbnail'] = attr_value
                                    break
            
            return car_model
            
        except Exception as e:
            self.logger.error(f"Lỗi khi extract car model từ advert: {e}")
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
        html = await self.fetch_page(Config.BASE_URL)
        if not html:
            return []
        
        # Thử parse từ __NEXT_DATA__ trước (phương pháp mới)
        listings = self.parse_next_data(html)
        
        # Nếu không có dữ liệu từ __NEXT_DATA__, fallback về phương pháp cũ
        if not listings:
            listings = self.parse_car_listings(html)
        
        # Phát hiện tin mới
        new_listings = []
        for listing in listings:
            if listing['id'] not in self.seen_ids:
                self.seen_ids.add(listing['id'])
                new_listings.append(listing)
                # Thêm vào đầu danh sách all_listings (item mới nhất ở đầu)
                self.all_listings.insert(0, listing)
                # Giới hạn số lượng listings để tránh tốn bộ nhớ (giữ lại 1000 item mới nhất)
                if len(self.all_listings) > 1000:
                    self.all_listings = self.all_listings[:1000]
                # Log thông tin chi tiết hơn
                car_info = listing.get('car_info', {})
                pricing = listing.get('pricing', {})
                price_display = pricing.get('price_display', pricing.get('price', 'N/A'))
                make = car_info.get('make', 'N/A')
                model = car_info.get('model', 'N/A')
                year = car_info.get('year', 'N/A')
                # self.logger.info(f"New listing found: {make} {model} ({year}) - {price_display}")
        
        self.total_crawled += len(listings)
        
        return new_listings
    
    async def crawl_loop(self):
        """Vòng lặp crawl chính"""
        self.is_running = True
        
        while self.is_running:
            try:
                # Thực hiện crawl
                new_listings = await self.crawl_once()
                
                # Cập nhật new_listings array nếu có listing mới
                if new_listings:
                    self.update_new_listings_array(new_listings)
                    
                    # Log thông tin của new_listings_array
                    if self.new_listings_array:
                        self.logger.info(f"new_listings_array hiện có {len(self.new_listings_array)} items:")
                        for i, item in enumerate(self.new_listings_array[:10], 1):  # Log 10 items đầu tiên
                            item_id = item.get('id', 'N/A')
                            item_title = item.get('title', 'N/A')
                            # self.logger.info(f"  [{i}] ID: {item_id} | Title: {item_title}")
                        # if len(self.new_listings_array) > 10:
                            # self.logger.info(f"  ... và {len(self.new_listings_array) - 10} items khác")
                    
                    # Broadcast toàn bộ array cho WebSocket
                    broadcast_data = {
                        'type': 'new_listings_update',
                        'data': self.new_listings_array,
                        'timestamp': datetime.now().isoformat(),
                        'count': len(self.new_listings_array)
                    }
                    # self.logger.info(f"Broadcasting new_listings_update with {len(self.new_listings_array)} items")
                    await self.websocket_manager.broadcast(broadcast_data)
                
                # Random delay để tránh bị chặn
                delay = random.uniform(Config.MIN_DELAY, Config.MAX_DELAY)
                await asyncio.sleep(Config.CRAWL_INTERVAL + delay)
                
            except Exception as e:
                self.logger.error(f"Error in crawl loop: {e}")
                await asyncio.sleep(Config.CRAWL_INTERVAL)
    
    def update_new_listings_array(self, new_listings: List[Dict[str, Any]]):
        """Cập nhật new_listings array: thêm mới vào đầu, loại bỏ duplicate dựa trên ID"""
        if not new_listings:
            return
        
        # Lấy danh sách ID hiện tại để kiểm tra duplicate
        existing_ids = {listing.get('id', '') for listing in self.new_listings_array}
        
        # Convert các listing mới và thêm vào đầu danh sách
        for listing in new_listings:
            listing_id = listing.get('id', '')
            
            # Kiểm tra nếu ID đã tồn tại, loại bỏ item cũ
            if listing_id and listing_id in existing_ids:
                # Remove item cũ có cùng ID
                self.new_listings_array = [
                    item for item in self.new_listings_array 
                    if item.get('id', '') != listing_id
                ]
            
            # Convert listing sang format WebSocket
            websocket_data = self.convert_car_model_for_websocket(listing)
            
            # Thêm vào đầu danh sách
            self.new_listings_array.insert(0, websocket_data)
            existing_ids.add(listing_id)
        
        # Giới hạn số lượng để tránh tốn bộ nhớ
        if len(self.new_listings_array) > self.max_new_listings:
            self.new_listings_array = self.new_listings_array[:self.max_new_listings]
    
    def stop(self):
        """Dừng crawler"""
        self.is_running = False
    
    def convert_car_model_for_websocket(self, car_model: Dict[str, Any]) -> Dict[str, Any]:
        """Chuyển đổi car_model phức tạp thành format đơn giản cho WebSocket"""
        try:
            # Lấy thông tin từ car_model nested structure
            car_info = car_model.get('car_info', {})
            pricing = car_model.get('pricing', {})
            location = car_model.get('location', {})
            seller = car_model.get('seller', {})
            images = car_model.get('images', {})
            timing = car_model.get('timing', {})
            
            # Lấy ảnh với nhiều fallback
            image_url = images.get('main_image', '') or images.get('thumbnail', '')
            if not image_url and 'all_images' in images and len(images['all_images']) > 0:
                image_url = images['all_images'][0]
            
            # Xử lý crawled_at - đảm bảo là string
            crawled_at = car_model.get('crawled_at', '')
            if crawled_at:
                if isinstance(crawled_at, datetime):
                    crawled_at = crawled_at.isoformat()
                elif not isinstance(crawled_at, str):
                    crawled_at = str(crawled_at)
            
            # Xử lý last_updated - đảm bảo là string
            last_updated = timing.get('last_updated', '')
            if last_updated:
                if isinstance(last_updated, datetime):
                    last_updated = last_updated.isoformat()
                elif not isinstance(last_updated, str):
                    last_updated = str(last_updated)
            
            return {
                'id': car_model.get('id', ''),
                'title': car_model.get('title', ''),
                'price': pricing.get('price_display', pricing.get('price', '')),
                'year': car_info.get('year', ''),
                'mileage': car_info.get('mileage', ''),
                'fuel': car_info.get('fuel_type_resolved', car_info.get('fuel_type', '')),
                'brand': car_info.get('make', ''),
                'model': car_info.get('model', ''),
                'location': location.get('city', location.get('address', '')),
                'seller': seller.get('org_name', ''),
                'url': car_model.get('url', ''),
                'image_url': image_url,
                'crawled_at': crawled_at,
                'source': 'willhaben.at',
                'transmission': car_info.get('transmission_resolved', car_info.get('transmission', '')),
                'last_updated': last_updated
            }
        except Exception as e:
            self.logger.error(f"Lỗi khi convert car_model cho WebSocket: {e}")
            # Fallback về format cơ bản
            return {
                'id': car_model.get('id', ''),
                'title': car_model.get('title', ''),
                'price': 'N/A',
                'year': 'N/A',
                'mileage': 'N/A',
                'fuel': 'N/A',
                'brand': 'N/A',
                'model': 'N/A',
                'location': 'N/A',
                'seller': 'N/A',
                'url': car_model.get('url', ''),
                'image_url': '',
                'crawled_at': car_model.get('crawled_at', ''),
                'source': 'willhaben.at',
                'transmission': 'N/A',
                'last_updated': ''
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
    # Tạo crawler session
    await crawler.create_session()

    # Khởi động fetch proxy free (multiprocessing producer + async consumer)
    crawler.proxy_manager.start_free_proxy_fetcher()
    
    # Bắt đầu crawler loop
    asyncio.create_task(crawler.crawl_loop())


@app.on_event("shutdown")
async def shutdown_event():
    """Dọn dẹp khi ứng dụng tắt"""
    # Dừng crawler
    crawler.stop()
    
    # Đóng session
    await crawler.close_session()
    # Dừng vòng lặp fetch proxy free và tiến trình producer
    await crawler.proxy_manager.stop_free_proxy_fetcher()


@app.get("/")
async def root():
    """Trang chủ"""
    return {
        "message": "Willhaben.at Realtime Crawler Backend",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "test": "/test",
            "websocket": "/ws"
        }
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
            .listing-image {
                width: 150px;
                height: 100px;
                object-fit: cover;
                border-radius: 4px;
                margin-right: 15px;
                float: left;
            }
            .listing-content {
                overflow: hidden;
            }
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
                <h3>🆕 New Listings (Real-time)</h3>
                <div style="margin-bottom: 10px;">
                    <strong>New Items Count:</strong> <span id="new-items">0</span> | 
                    <strong>Last Update:</strong> <span id="last-update">Never</span>
                </div>
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
                        if (data.type === 'welcome') {
                            console.log('Welcome message:', data.message);
                        } else if (data.type === 'initial_listings' || data.type === 'new_listings_update') {
                            // Nhận array và hiển thị trực tiếp
                            if (data.data && Array.isArray(data.data)) {
                                console.log(`Received ${data.type}: ${data.data.length} items`);
                                displayListings(data.data);
                            } else {
                                console.warn('Invalid data format:', data);
                            }
                            newItems = data.count || (data.data ? data.data.length : 0);
                            const newItemsEl = document.getElementById('new-items');
                            if (newItemsEl) {
                                newItemsEl.textContent = newItems;
                            }
                            if (data.type === 'new_listings_update') {
                                const lastUpdateEl = document.getElementById('last-update');
                                if (lastUpdateEl) {
                                    lastUpdateEl.textContent = new Date().toLocaleTimeString();
                                }
                            }
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

            function displayListings(listings) {
                const messagesDiv = document.getElementById('messages');
                
                if (!listings || !Array.isArray(listings) || listings.length === 0) {
                    console.warn('displayListings: Invalid or empty listings array');
                    return;
                }
                
                console.log(`displayListings: Rendering ${listings.length} listings`);
                
                // Xóa danh sách cũ
                messagesDiv.innerHTML = '';
                
                // listings từ server có mới nhất ở đầu (index 0)
                // Để hiển thị cũ nhất ở trên, mới nhất ở dưới:
                // Duyệt từ cuối array về đầu và thêm vào đầu DOM
                for (let i = listings.length - 1; i >= 0 ; i--) {
                    const listing = listings[i];
                    if (!listing || !listing.id) {
                        console.warn('Skipping invalid listing:', listing);
                        continue;
                    }
                    
                    const listingDiv = document.createElement('div');
                    listingDiv.className = 'listing';
                    listingDiv.setAttribute('data-id', listing.id); // Để debug dễ hơn
                    
                    // Tạo HTML cho ảnh
                    const imageHtml = listing.image_url ? 
                        `<img src="${listing.image_url}" alt="${listing.title || 'Car'}" class="listing-image" onerror="this.style.display='none'">` : 
                        '';
                    
                    listingDiv.innerHTML = `
                        ${imageHtml}
                        <div class="listing-content">
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
                            <div class="timestamp">Found at: ${new Date(listing.crawled_at || Date.now()).toLocaleString()}</div>
                        </div>
                    `;
                    
                    // Thêm vào đầu danh sách (cũ nhất sẽ ở trên)
                    messagesDiv.insertBefore(listingDiv, messagesDiv.firstChild);
                }
                
                console.log(`displayListings: Rendered ${messagesDiv.children.length} items in DOM`);
                
                // Giới hạn số lượng tin hiển thị (giữ lại 50 tin mới nhất ở cuối)
                while (messagesDiv.children.length > 50) {
                    messagesDiv.removeChild(messagesDiv.firstChild);
                }
            }

            // Bắt đầu kết nối khi trang load
            connect();
            
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
        
        # Gửi new_listings_array ban đầu nếu có
        new_listings_copy = crawler.new_listings_array.copy()
        if new_listings_copy:
            # Không đảo ngược ở server, để frontend tự xử lý
            # new_listings_array có mới nhất ở đầu
            initial_message = {
                'type': 'initial_listings',
                'data': new_listings_copy,  # Gửi nguyên vẹn, không đảo ngược
                'timestamp': datetime.now().isoformat(),
                'count': len(new_listings_copy)
            }
            # logger.info(f"Sending initial_listings to new client: {len(new_listings_copy)} items")
            await websocket_manager.send_personal_message(
                json.dumps(initial_message),
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
    # Chạy server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )

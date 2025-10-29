# Willhaben.at Realtime Crawler Backend

Backend Python realtime crawl dữ liệu từ trang web Willhaben.at sử dụng FastAPI + aiohttp + WebSocket để phát hiện và gửi tin mới realtime.

## 🚀 Tính năng

- ✅ **Realtime Crawling**: Crawl dữ liệu từ Willhaben.at mỗi 3 giây
- ✅ **Diff Detection**: Phát hiện tin mới bằng cách lưu cache ID các tin đã thấy
- ✅ **WebSocket Realtime**: Gửi tin mới realtime qua WebSocket đến client
- ✅ **Async Workers**: Nhiều worker async để crawl song song
- ✅ **Anti-Detection**: Random delay, user-agent rotation, proxy rotation, auto-fetch free proxy để tránh bị chặn
- ✅ **Health Check**: Endpoint `/health` trả về số lượng tin đã thấy
- ✅ **Test Page**: Trang `/test` demo WebSocket trong trình duyệt
- ✅ **Logging**: Logging chi tiết và có thể mở rộng
- ✅ **Scalable**: Sẵn sàng tích hợp Redis, Firebase, Database

## 📋 Yêu cầu hệ thống

- Python 3.8+
- pip hoặc conda

## 🛠️ Cài đặt

### 1. Clone hoặc tải project

```bash
# Nếu bạn có git
git clone <repository-url>
cd Willhaben

# Hoặc tải file realtime_backend.py và requirements.txt
```

### 2. Cài đặt dependencies

```bash
# Cách đơn giản nhất (sử dụng html.parser)
pip install -r requirements.txt

# Nếu gặp lỗi lxml, xem INSTALL.md để biết cách khắc phục
```

### 3. Chạy ứng dụng

```bash
# Cách 1: Chạy trực tiếp
python realtime_backend.py

# Cách 2: Sử dụng uvicorn (khuyến nghị)
uvicorn realtime_backend:app --reload --host 0.0.0.0 --port 8000
```

## 🌐 Endpoints

### HTTP Endpoints

- **GET /** - Trang chủ với thông tin API
- **GET /health** - Health check và thống kê
- **GET /test** - Trang test WebSocket trong trình duyệt

### WebSocket Endpoint

- **WS /ws** - WebSocket cho realtime updates

## 📱 Tích hợp Android App

### Kết nối WebSocket

```kotlin
// Android Kotlin example
val wsUrl = "ws://your-server-ip:8000/ws"
val webSocket = OkHttpClient().newWebSocket(
    Request.Builder().url(wsUrl).build(),
    object : WebSocketListener() {
        override fun onMessage(webSocket: WebSocket, text: String) {
            try {
                val data = JSONObject(text)
                if (data.getString("type") == "new_listing") {
                    val listing = data.getJSONObject("data")
                    // Xử lý tin mới
                    handleNewListing(listing)
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }
)
```

### Cấu trúc dữ liệu tin mới

```json
{
  "type": "new_listing",
  "data": {
    "id": "123456789",
    "title": "BMW 320d xDrive",
    "price": "€ 25.900",
    "year": "2019",
    "km": "45.000 km",
    "link": "https://www.willhaben.at/iad/gebrauchtwagen/auto/...",
    "image_url": "https://...",
    "crawled_at": "2024-01-01T12:00:00",
    "source": "willhaben.at"
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

## 🔧 Cấu hình

### Thay đổi cấu hình trong file `realtime_backend.py`

```python
class Config:
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
    USE_PROXY_ROTATION = True  # Bật proxy rotation
    AUTO_FETCH_FREE_PROXY = True  # Tự động lấy proxy free
    PROXY_LIST = [
        # Proxy thủ công (tùy chọn)
        # "http://proxy1:port",
        # "http://proxy2:port",
        # "http://username:password@proxy3:port"
    ]
    PROXY_TIMEOUT = 15  # Timeout cho proxy
    MAX_FREE_PROXIES = 50  # Số lượng proxy free tối đa
    PROXY_FETCH_INTERVAL = 300  # Thời gian fetch proxy mới (giây)
```

## 📊 Monitoring

### Health Check Response

```json
{
  "status": "healthy",
  "crawler_running": true,
  "total_seen_items": 150,
  "total_crawled": 150,
  "new_items_found": 5,
  "uptime_seconds": 3600,
  "last_crawl_time": "2024-01-01T12:00:00",
  "websocket_connections": 2
}
```

### Logs

Ứng dụng sẽ tạo file log `willhaben_crawler.log` với thông tin chi tiết:

```
2024-01-01 12:00:00 - WillhabenCrawler - INFO - Starting crawl cycle...
2024-01-01 12:00:01 - WillhabenCrawler - INFO - Found 20 potential car listings
2024-01-01 12:00:02 - WillhabenCrawler - INFO - New listing found: BMW 320d - € 25.900
2024-01-01 12:00:03 - WebSocketManager - INFO - Broadcasted message to 2 connections
```

## 🚀 Mở rộng

### Thêm Redis Cache

```python
import redis
import json

class RedisCache:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    async def store_listing(self, listing_id: str, data: dict):
        self.redis_client.setex(f"listing:{listing_id}", 3600, json.dumps(data))
    
    async def get_listing(self, listing_id: str):
        data = self.redis_client.get(f"listing:{listing_id}")
        return json.loads(data) if data else None
```

### Thêm Database

```python
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class CarListing(Base):
    __tablename__ = "car_listings"
    
    id = Column(String, primary_key=True)
    title = Column(String)
    price = Column(String)
    year = Column(String)
    km = Column(String)
    link = Column(String)
    image_url = Column(String)
    crawled_at = Column(DateTime)
    source = Column(String)
```

### Proxy Rotation + Auto-Fetch Free Proxy (Đã tích hợp sẵn)

Backend đã tích hợp đầy đủ tính năng proxy:

```python
# Cấu hình proxy trong Config
USE_PROXY_ROTATION = True
AUTO_FETCH_FREE_PROXY = True  # Tự động lấy proxy free
PROXY_LIST = [
    # Proxy thủ công (tùy chọn)
    "http://proxy1:port",
    "http://proxy2:port", 
    "http://username:password@proxy3:port"
]

# Endpoints quản lý proxy
GET /proxy/stats      # Xem thống kê proxy
GET /proxy/list       # Xem danh sách proxy
POST /proxy/fetch     # Fetch proxy free thủ công
POST /proxy/reset     # Reset proxy bị lỗi
```

**Tính năng tự động:**
- ✅ Tự động fetch proxy free từ 4+ nguồn
- ✅ Test proxy và chỉ giữ lại proxy hoạt động
- ✅ Fetch proxy mới mỗi 5 phút
- ✅ Tự động failover khi proxy bị lỗi

Xem chi tiết trong file `FREE_PROXY_GUIDE.md` và `PROXY_CONFIG.md`

## 🐛 Troubleshooting

### Lỗi thường gặp

1. **Lỗi lxml build**: Xem file `INSTALL.md` để biết cách khắc phục chi tiết
   ```bash
   # Giải pháp nhanh: Sử dụng html.parser
   pip install -r requirements.txt
   ```

2. **Import Error**: Đảm bảo đã cài đặt tất cả dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. **WebSocket Connection Failed**: Kiểm tra firewall và port 8000
   ```bash
   # Kiểm tra port có đang được sử dụng
   lsof -i :8000
   ```

4. **Crawling không hoạt động**: Kiểm tra network và URL
   ```bash
   curl -I https://www.willhaben.at/iad/gebrauchtwagen/auto/gebrauchtwagenboerse
   ```

### Debug Mode

Để bật debug mode, thay đổi trong `realtime_backend.py`:

```python
class Config:
    LOG_LEVEL = logging.DEBUG  # Thay đổi từ INFO thành DEBUG
```

## 📝 License

MIT License - Xem file LICENSE để biết thêm chi tiết.

## 🤝 Contributing

1. Fork project
2. Tạo feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Mở Pull Request

## 📞 Support

Nếu gặp vấn đề, hãy tạo issue trên GitHub hoặc liên hệ qua email.

---

**Lưu ý**: Đảm bảo tuân thủ Terms of Service của Willhaben.at khi sử dụng crawler này.

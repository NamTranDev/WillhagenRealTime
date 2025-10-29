# 🆓 FREE PROXY AUTO-FETCH GUIDE

## Tính năng tự động lấy proxy free

Backend đã được tích hợp tính năng tự động fetch proxy free từ các nguồn công khai để bạn không cần cấu hình proxy thủ công.

### 🚀 Cách bật tính năng

```python
class Config:
    # Proxy settings
    USE_PROXY_ROTATION = True  # Bật proxy rotation
    AUTO_FETCH_FREE_PROXY = True  # Bật tự động lấy proxy free
    MAX_FREE_PROXIES = 50  # Số lượng proxy free tối đa
    PROXY_FETCH_INTERVAL = 300  # Thời gian fetch proxy mới (giây)
```

### 📡 Nguồn proxy free

Backend tự động fetch từ các nguồn sau:

1. **Proxy-List.download**: `https://www.proxy-list.download/api/v1/get?type=http`
2. **ProxyScrape**: `https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all`
3. **GitHub - TheSpeedX**: `https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt`
4. **GitHub - clarketm**: `https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt`

### 🔧 Endpoints quản lý proxy

- **GET /proxy/stats** - Xem thống kê proxy chi tiết
- **GET /proxy/list** - Xem danh sách proxy hiện tại
- **POST /proxy/fetch** - Fetch proxy free thủ công
- **POST /proxy/reset** - Reset proxy bị lỗi

### 📊 Thống kê proxy

```json
{
  "total_proxies": 25,
  "available_proxies": 20,
  "failed_proxies": 5,
  "proxy_rotation_enabled": true,
  "auto_fetch_enabled": true,
  "last_fetch_time": "2024-01-01T12:00:00",
  "manual_proxies": 0,
  "free_proxies": 25
}
```

### 🎯 Cách sử dụng

#### 1. Tự động (Khuyến nghị)
```python
# Trong Config
AUTO_FETCH_FREE_PROXY = True
USE_PROXY_ROTATION = True
```

Backend sẽ tự động:
- Fetch proxy free khi khởi động
- Fetch proxy mới mỗi 5 phút
- Test proxy và chỉ giữ lại proxy hoạt động
- Tự động failover khi proxy bị lỗi

#### 2. Thủ công
```bash
# Fetch proxy free ngay lập tức
curl -X POST http://localhost:8000/proxy/fetch

# Xem danh sách proxy
curl http://localhost:8000/proxy/list

# Reset proxy bị lỗi
curl -X POST http://localhost:8000/proxy/reset
```

#### 3. Qua trang test
Truy cập http://localhost:8000/test và sử dụng các nút:
- **Fetch Free Proxies**: Lấy proxy mới
- **Reset Failed**: Reset proxy bị lỗi

### 🔍 Monitoring

#### Logs proxy
```
2024-01-01 12:00:00 - FreeProxyManager - INFO - Starting to fetch free proxies...
2024-01-01 12:00:01 - FreeProxyManager - INFO - Fetched 15 proxies from https://api.proxyscrape.com/...
2024-01-01 12:00:02 - FreeProxyManager - INFO - Found 12 working proxies
2024-01-01 12:00:03 - ProxyManager - INFO - Added 12 free proxies. Total proxies: 12
```

#### Health check
```bash
curl http://localhost:8000/health
```

Response sẽ bao gồm:
```json
{
  "proxy_rotation": {
    "enabled": true,
    "total_proxies": 25,
    "available_proxies": 20,
    "failed_proxies": 5
  }
}
```

### ⚡ Tính năng nâng cao

#### 1. Proxy Testing
- Tự động test proxy với httpbin.org/ip
- Chỉ giữ lại proxy hoạt động
- Timeout 10 giây cho mỗi test

#### 2. Smart Rotation
- Random selection từ danh sách proxy
- Automatic failover khi proxy fail
- Reset failed proxies khi cần

#### 3. Rate Limiting
- Delay 1-3 giây giữa các requests fetch
- Fetch interval 5 phút mặc định
- Tối đa 50 proxy free

### 🛠️ Cấu hình nâng cao

```python
class Config:
    # Proxy sources (có thể thêm nguồn khác)
    FREE_PROXY_SOURCES = [
        "https://www.proxy-list.download/api/v1/get?type=http",
        "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
        # Thêm nguồn của bạn
        "https://your-proxy-source.com/proxies.txt"
    ]
    
    # Giới hạn proxy
    MAX_FREE_PROXIES = 100  # Tăng số lượng proxy
    
    # Tần suất fetch
    PROXY_FETCH_INTERVAL = 600  # Fetch mỗi 10 phút
    
    # Timeout
    PROXY_TIMEOUT = 15  # Timeout cho proxy requests
```

### 🚨 Lưu ý quan trọng

1. **Proxy Free không ổn định**: Proxy free có thể bị chặn hoặc không hoạt động
2. **Rate Limiting**: Không fetch quá thường xuyên để tránh bị chặn
3. **Testing**: Luôn test proxy trước khi sử dụng
4. **Backup**: Nên có proxy paid làm backup

### 🔧 Troubleshooting

#### Proxy không hoạt động
```bash
# Kiểm tra logs
tail -f willhaben_crawler.log | grep -i proxy

# Reset proxy bị lỗi
curl -X POST http://localhost:8000/proxy/reset

# Fetch proxy mới
curl -X POST http://localhost:8000/proxy/fetch
```

#### Không fetch được proxy
```bash
# Kiểm tra network
curl -I https://api.proxyscrape.com/v2/

# Kiểm tra logs
grep "FreeProxyManager" willhaben_crawler.log
```

### 📈 Performance Tips

1. **Tăng số lượng proxy**: `MAX_FREE_PROXIES = 100`
2. **Giảm fetch interval**: `PROXY_FETCH_INTERVAL = 180` (3 phút)
3. **Tăng timeout**: `PROXY_TIMEOUT = 20`
4. **Monitor logs**: Theo dõi logs để tối ưu

### 🎉 Kết luận

Với tính năng auto-fetch proxy free, bạn có thể:
- ✅ Không cần cấu hình proxy thủ công
- ✅ Tự động có proxy mới mỗi 5 phút
- ✅ Proxy được test và chỉ giữ lại proxy hoạt động
- ✅ Tự động failover khi proxy bị lỗi
- ✅ Monitoring và quản lý qua API

Backend của bạn giờ đã hoàn toàn tự động và không cần cấu hình proxy! 🚀

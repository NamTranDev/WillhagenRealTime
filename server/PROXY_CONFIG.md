# 🔄 PROXY ROTATION CONFIGURATION

## Cách bật và cấu hình Proxy Rotation

### 1. Cấu hình trong realtime_backend.py

```python
class Config:
    # Proxy settings
    USE_PROXY_ROTATION = True  # Bật proxy rotation
    PROXY_LIST = [
        "http://proxy1.example.com:8080",
        "http://proxy2.example.com:8080", 
        "http://proxy3.example.com:8080",
        "http://username:password@proxy4.example.com:8080",
        "socks5://proxy5.example.com:1080"
    ]
    PROXY_TIMEOUT = 15  # Timeout cho proxy requests
```

### 2. Các loại proxy được hỗ trợ

- **HTTP Proxy**: `http://proxy:port`
- **HTTPS Proxy**: `https://proxy:port`
- **SOCKS5 Proxy**: `socks5://proxy:port`
- **Proxy với authentication**: `http://username:password@proxy:port`

### 3. Ví dụ cấu hình proxy

```python
PROXY_LIST = [
    # Free proxy (không khuyến nghị cho production)
    "http://103.152.112.162:80",
    "http://103.152.112.145:80",
    
    # Paid proxy services
    "http://username:password@premium-proxy.com:8080",
    "socks5://user:pass@socks-proxy.com:1080",
    
    # Residential proxies
    "http://residential-proxy.com:8080",
    "http://backup-proxy.com:3128"
]
```

### 4. Endpoints quản lý proxy

- **GET /proxy/stats** - Xem thống kê proxy
- **POST /proxy/reset** - Reset danh sách proxy bị lỗi
- **GET /health** - Xem trạng thái proxy trong health check

### 5. Monitoring proxy

```bash
# Xem thống kê proxy
curl http://localhost:8000/proxy/stats

# Reset proxy bị lỗi
curl -X POST http://localhost:8000/proxy/reset

# Xem health check với thông tin proxy
curl http://localhost:8000/health
```

### 6. Logs proxy

Proxy rotation sẽ được log chi tiết:

```
2024-01-01 12:00:00 - ProxyManager - INFO - Initialized with 5 proxies
2024-01-01 12:00:01 - WillhabenCrawler - DEBUG - Using proxy: http://proxy1:8080
2024-01-01 12:00:02 - WillhabenCrawler - DEBUG - Successfully fetched URL via http://proxy1:8080
2024-01-01 12:00:03 - ProxyManager - WARNING - Marked proxy as failed: http://proxy2:8080
```

### 7. Tính năng proxy rotation

- ✅ **Random Selection**: Chọn proxy ngẫu nhiên từ danh sách
- ✅ **Failover**: Tự động chuyển sang proxy khác khi fail
- ✅ **Health Check**: Theo dõi trạng thái proxy
- ✅ **Auto Reset**: Reset proxy bị lỗi khi cần
- ✅ **Timeout Management**: Timeout riêng cho proxy requests
- ✅ **Authentication**: Hỗ trợ proxy với username/password

### 8. Khuyến nghị

- **Development**: Sử dụng free proxy để test
- **Production**: Sử dụng paid proxy service đáng tin cậy
- **Backup**: Luôn có ít nhất 3-5 proxy backup
- **Monitoring**: Theo dõi logs và stats thường xuyên
- **Rotation**: Thay đổi proxy định kỳ để tránh bị chặn

### 9. Troubleshooting

**Proxy không hoạt động:**
```bash
# Kiểm tra proxy có khả dụng không
curl --proxy http://proxy:port http://httpbin.org/ip

# Kiểm tra logs
tail -f willhaben_crawler.log | grep -i proxy
```

**Tất cả proxy bị fail:**
```bash
# Reset proxy bị lỗi
curl -X POST http://localhost:8000/proxy/reset
```

**Proxy chậm:**
```python
# Tăng timeout
PROXY_TIMEOUT = 30  # Tăng từ 15 lên 30 giây
```

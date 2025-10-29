# 🚀 QUICK START GUIDE

## Cài đặt và chạy nhanh

### 1. Cài đặt dependencies
```bash
# Cách đơn giản nhất (sử dụng html.parser)
pip install -r requirements.txt

# Nếu gặp lỗi lxml, xem INSTALL.md
```

### 2. Chạy server
```bash
# Cách 1: Sử dụng script khởi động
python start.py

# Cách 2: Chạy trực tiếp
python realtime_backend.py

# Cách 3: Sử dụng uvicorn
uvicorn realtime_backend:app --reload --host 0.0.0.0 --port 8000
```

### 3. Truy cập ứng dụng
- **Trang chủ**: http://localhost:8000
- **Test WebSocket**: http://localhost:8000/test
- **Health Check**: http://localhost:8000/health
- **WebSocket**: ws://localhost:8000/ws

## 📱 Tích hợp Android

### WebSocket URL
```
ws://your-server-ip:8000/ws
```

### Cấu trúc tin nhắn
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

## 🐳 Docker

### Build và chạy
```bash
# Build image
docker build -t willhaben-crawler .

# Chạy container
docker run -p 8000:8000 willhaben-crawler

# Hoặc sử dụng docker-compose
docker-compose up -d
```

## ⚙️ Cấu hình

Chỉnh sửa các thông số trong file `realtime_backend.py`:

```python
class Config:
    CRAWL_INTERVAL = 3.0  # Thời gian giữa các lần crawl
    MIN_DELAY = 0.5       # Delay tối thiểu
    MAX_DELAY = 2.0       # Delay tối đa
    REQUEST_TIMEOUT = 10  # Timeout requests
```

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Logs
```bash
tail -f willhaben_crawler.log
```

## 🔧 Troubleshooting

### Lỗi lxml build
```bash
# Giải pháp nhanh: Sử dụng html.parser
pip install -r requirements.txt

# Chi tiết: Xem INSTALL.md
```

### Lỗi import
```bash
pip install -r requirements.txt
```

### Port đã được sử dụng
```bash
# Thay đổi port
python start.py --port 9000
```

### WebSocket không kết nối được
- Kiểm tra firewall
- Đảm bảo server đang chạy
- Kiểm tra URL WebSocket

## 📞 Support

- Đọc README.md để biết thêm chi tiết
- Kiểm tra logs để debug
- Tạo issue nếu gặp vấn đề

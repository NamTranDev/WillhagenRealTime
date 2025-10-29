# Willhaben Crawler Configuration
# Cấu hình cho Willhaben.at Realtime Crawler

# =============================================================================
# CRAWLER SETTINGS
# =============================================================================

# URL mục tiêu để crawl
BASE_URL = "https://www.willhaben.at/iad/gebrauchtwagen/auto/gebrauchtwagenboerse"

# Thời gian giữa các lần crawl (giây)
CRAWL_INTERVAL = 3.0

# Số worker async song song
MAX_WORKERS = 5

# Timeout cho HTTP requests (giây)
REQUEST_TIMEOUT = 10

# =============================================================================
# ANTI-DETECTION SETTINGS
# =============================================================================

# Delay tối thiểu giữa requests (giây)
MIN_DELAY = 0.5

# Delay tối đa giữa requests (giây)
MAX_DELAY = 2.0

# Có sử dụng user-agent rotation không
USER_AGENT_ROTATION = True

# =============================================================================
# WEBSOCKET SETTINGS
# =============================================================================

# Số kết nối WebSocket tối đa
MAX_CONNECTIONS = 100

# =============================================================================
# LOGGING SETTINGS
# =============================================================================

# Mức độ logging (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL = "INFO"

# Format của log
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# File log
LOG_FILE = "willhaben_crawler.log"

# =============================================================================
# SERVER SETTINGS
# =============================================================================

# Host để bind server
HOST = "0.0.0.0"

# Port để chạy server
PORT = 8000

# =============================================================================
# PROXY SETTINGS (Tùy chọn)
# =============================================================================

# Danh sách proxy để rotation (để trống nếu không sử dụng)
PROXY_LIST = [
    # "http://proxy1:port",
    # "http://proxy2:port",
    # "http://proxy3:port"
]

# Có sử dụng proxy rotation không
USE_PROXY_ROTATION = False

# =============================================================================
# DATABASE SETTINGS (Tùy chọn - cho tương lai)
# =============================================================================

# Cấu hình database (chưa implement)
DATABASE_URL = "sqlite:///willhaben.db"

# Cấu hình Redis (chưa implement)
REDIS_URL = "redis://localhost:6379/0"

# =============================================================================
# NOTIFICATION SETTINGS (Tùy chọn)
# =============================================================================

# Webhook URL để gửi thông báo (chưa implement)
WEBHOOK_URL = ""

# Email settings (chưa implement)
EMAIL_SMTP_SERVER = ""
EMAIL_SMTP_PORT = 587
EMAIL_USERNAME = ""
EMAIL_PASSWORD = ""
EMAIL_RECIPIENTS = []

# =============================================================================
# FILTER SETTINGS (Tùy chọn)
# =============================================================================

# Lọc theo giá tối thiểu (EUR)
MIN_PRICE = 0

# Lọc theo giá tối đa (EUR)
MAX_PRICE = 100000

# Lọc theo năm sản xuất tối thiểu
MIN_YEAR = 2000

# Lọc theo năm sản xuất tối đa
MAX_YEAR = 2024

# Lọc theo kilomet tối đa
MAX_KM = 200000

# Từ khóa để lọc (để trống nếu không lọc)
KEYWORDS_FILTER = [
    # "BMW",
    # "Mercedes",
    # "Audi"
]

# Từ khóa loại trừ
EXCLUDE_KEYWORDS = [
    # "unfall",
    # "schaden"
]

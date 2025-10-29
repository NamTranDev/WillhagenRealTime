# 🛠️ HƯỚNG DẪN CÀI ĐẶT CHI TIẾT

## Lỗi lxml và cách khắc phục

### Vấn đề
Lỗi `Building wheel for lxml (pyproject.toml) ... error` xảy ra khi thiếu các dependencies hệ thống cần thiết để build lxml.

### Giải pháp

#### Cách 1: Sử dụng html.parser (Khuyến nghị - Đơn giản nhất)

```bash
# Cài đặt dependencies cơ bản (không có lxml)
pip install -r requirements.txt
```

#### Cách 2: Cài đặt lxml với system dependencies

**macOS:**
```bash
# Cài đặt system dependencies
brew install libxml2 libxslt

# Cài đặt Python dependencies
pip install -r requirements-with-lxml.txt
```

**Ubuntu/Debian:**
```bash
# Cài đặt system dependencies
sudo apt-get update
sudo apt-get install libxml2-dev libxslt-dev python3-dev

# Cài đặt Python dependencies
pip install -r requirements-with-lxml.txt
```

**CentOS/RHEL:**
```bash
# Cài đặt system dependencies
sudo yum install libxml2-devel libxslt-devel python3-devel
# hoặc cho CentOS 8+
sudo dnf install libxml2-devel libxslt-devel python3-devel

# Cài đặt Python dependencies
pip install -r requirements-with-lxml.txt
```

**Windows:**
```bash
# Sử dụng conda (khuyến nghị cho Windows)
conda install lxml

# Hoặc tải pre-compiled wheel
pip install --only-binary=lxml lxml
```

#### Cách 3: Sử dụng conda (Khuyến nghị cho Windows)

```bash
# Tạo environment mới
conda create -n willhaben-crawler python=3.11

# Activate environment
conda activate willhaben-crawler

# Cài đặt dependencies
conda install fastapi uvicorn aiohttp websockets beautifulsoup4 lxml fake-useragent
pip install asyncio-throttle python-multipart aiofiles
```

## Kiểm tra cài đặt

```bash
# Kiểm tra Python version
python --version

# Kiểm tra pip
pip --version

# Test import các packages
python -c "import fastapi, aiohttp, bs4, fake_useragent; print('All packages imported successfully!')"
```

## Troubleshooting

### Lỗi "Microsoft Visual C++ 14.0 is required" (Windows)
```bash
# Cài đặt Visual Studio Build Tools
# Hoặc sử dụng conda
conda install lxml
```

### Lỗi "fatal error: 'libxml/xmlversion.h' file not found" (macOS)
```bash
# Cài đặt libxml2
brew install libxml2

# Set environment variables
export LDFLAGS="-L$(brew --prefix libxml2)/lib"
export CPPFLAGS="-I$(brew --prefix libxml2)/include"
pip install lxml
```

### Lỗi "No module named '_lxml'" (Linux)
```bash
# Cài đặt system dependencies
sudo apt-get install libxml2-dev libxslt-dev python3-dev

# Reinstall lxml
pip uninstall lxml
pip install lxml
```

## Performance Comparison

| Parser | Speed | Memory Usage | Features |
|--------|-------|--------------|----------|
| html.parser | Slow | Low | Basic |
| lxml | Fast | Medium | Advanced |
| html5lib | Slowest | High | Most compatible |

**Khuyến nghị:**
- Development: Sử dụng html.parser (đơn giản)
- Production: Sử dụng lxml (hiệu suất tốt hơn)

## Chạy ứng dụng sau khi cài đặt

```bash
# Kiểm tra dependencies
python start.py --check

# Cài đặt dependencies nếu cần
python start.py --install

# Chạy server
python start.py
```

## Docker (Không cần cài đặt dependencies)

```bash
# Build và chạy với Docker
docker build -t willhaben-crawler .
docker run -p 8000:8000 willhaben-crawler
```

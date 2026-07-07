# Hướng dẫn Cài đặt & Cấu hình (macOS & Windows)

Tài liệu này hướng dẫn chi tiết cách cài đặt các thành phần phụ thuộc và khởi chạy ứng dụng **AI Local Support** trên hệ điều hành **macOS** và **Windows**.

---

## 📋 Yêu cầu chung
Trước khi bắt đầu, hãy đảm bảo hệ thống của bạn đã cài đặt các công cụ sau:
- **Python 3.8 - 3.12**
- **Ollama** (Đã chạy ở máy local) -> Tải tại [ollama.com](https://ollama.com)
- **Tesseract OCR** (Tùy chọn, để hỗ trợ nhận diện text trên hình ảnh đối với model không hỗ trợ vision)
  - macOS: `brew install tesseract`
  - Windows: Tải bộ cài đặt `.exe` từ [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) và thêm đường dẫn `C:\Program Files\Tesseract-OCR` vào biến môi trường `PATH`.

---

## 🍎 Hướng dẫn cài đặt trên macOS

### Bước 1: Clone dự án và khởi tạo môi trường ảo
Mở Terminal và chạy các lệnh sau:
```bash
# Di chuyển vào thư mục dự án
cd ai-local-supporter

# Khởi tạo môi trường ảo Python
python3 -m venv .venv

# Kích hoạt môi trường ảo
source .venv/bin/activate

# Nâng cấp pip và cài đặt dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 2: Tải các model Ollama
Đảm bảo ứng dụng Ollama đang chạy, sau đó kéo các model LLM và Embedding về:
```bash
# Tải model LLM chính để chat & phân tích (ví dụ: qwen2.5-coder)
ollama pull qwen2.5-coder:14b

# BẮT BUỘC: Tải model nhúng vector (embedding) phục vụ tìm kiếm RAG
ollama pull nomic-embed-text
```

### Bước 3: Cài đặt và khởi chạy Redis Server
Redis được dùng làm message broker cho Celery. Trên macOS, bạn có hai lựa chọn:

*   **Cách 1: Sử dụng Homebrew (Khuyên dùng)**
    ```bash
    brew install redis
    brew services start redis
    ```
*   **Cách 2: Sử dụng Docker**
    ```bash
    docker run -d -p 6379:6379 --name redis-broker redis:alpine
    ```

### Bước 4: Khởi chạy ứng dụng
Mở **2 tab Terminal** song song (cả 2 đều cần kích hoạt `.venv` trước khi chạy):

- **Terminal 1 (Celery Worker):**
  ```bash
  source .venv/bin/activate
  celery -A tasks.celery worker --loglevel=info
  ```
- **Terminal 2 (Flask Server):**
  ```bash
  source .venv/bin/activate
  python3 app.py
  ```

Mở trình duyệt truy cập: **http://127.0.0.1:5001**

---

## 💻 Hướng dẫn cài đặt trên Windows

### Bước 1: Khởi tạo môi trường ảo và cài đặt thư viện
Mở **PowerShell** hoặc **Command Prompt (CMD)** dưới quyền Admin và di chuyển vào thư mục dự án:
```powershell
# Di chuyển vào thư mục dự án
cd ai-local-supporter

# Khởi tạo môi trường ảo Python
python -m venv .venv
```

Kích hoạt môi trường ảo dựa trên trình thông dịch bạn sử dụng:
*   **Trên PowerShell:**
    ```powershell
    # Nếu gặp lỗi Execution Policy, hãy cấp quyền chạy script:
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
    
    # Kích hoạt venv
    .\.venv\Scripts\Activate.ps1
    ```
*   **Trên CMD:**
    ```cmd
    .venv\Scripts\activate.bat
    ```

Sau đó tiến hành cài đặt thư viện:
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 2: Tải các model Ollama
Đảm bảo ứng dụng Ollama đang chạy dưới Taskbar, sau đó tải các model cần thiết:
```powershell
ollama pull qwen2.5-coder:14b
ollama pull nomic-embed-text
```

### Bước 3: Cài đặt và Khởi chạy Redis Server
Có hai cách thiết lập Redis trên Windows:

*   **Cách 1: Sử dụng WSL 2 (Windows Subsystem for Linux - Khuyên dùng nếu không có Docker)**
    Nếu bạn sử dụng WSL 2 (Ví dụ: Ubuntu), bạn có thể chạy Redis trực tiếp bên trong Linux và kết nối từ Windows:
    
    1. Mở Ubuntu terminal trong WSL và chạy lệnh cài đặt Redis:
       ```bash
       sudo apt update
       sudo apt install redis-server
       ```
    2. **Quan trọng (Cấu hình cho phép kết nối từ Windows):** Do WSL 2 coi kết nối từ Windows host là kết nối từ xa, bạn cần tắt chế độ bảo vệ của Redis.
       
       Mở file cấu hình bằng quyền root:
       ```bash
       sudo nano /etc/redis/redis.conf
       ```
       Tìm dòng `protected-mode yes` (thường ở dòng 111) và sửa thành:
       ```conf
       protected-mode no
       ```
       Lưu file lại (`Ctrl+O` -> `Enter` -> `Ctrl+X`).
       
    3. Khởi động lại dịch vụ Redis trong WSL:
       ```bash
       sudo service redis-server restart
       ```
    4. Để chạy Redis tự động sau này mà không cần đăng nhập Ubuntu, bạn có thể khởi động nhanh từ Windows CMD/PowerShell bằng lệnh:
       ```powershell
       wsl -d Ubuntu redis-server --daemonize yes
       ```

*   **Cách 2: Sử dụng Docker Desktop**
    Nếu đã cài đặt Docker Desktop trên Windows, mở PowerShell và chạy:
    ```powershell
    docker run -d -p 6379:6379 --name redis-broker redis:alpine
    ```

### Bước 4: Khởi chạy ứng dụng
Mở **2 cửa sổ Terminal (CMD hoặc PowerShell)** song song (đảm bảo cả 2 đều đã kích hoạt `.venv`):

- **Terminal 1 (Celery Worker):**
  *Lưu ý quan trọng:* Trên Windows, Celery cần chạy với pool `solo` để tránh xung đột đa tiến trình (prefork):
  ```powershell
  celery -A tasks.celery worker --loglevel=info --pool=solo
  ```
- **Terminal 2 (Flask Server):**
  ```powershell
  python app.py
  ```

Mở trình duyệt truy cập: **http://127.0.0.1:5001**

---

## 🛠 Hướng dẫn Khắc phục sự cố (Troubleshooting)

### 1. Celery báo lỗi: `Error 10061 connecting to 127.0.0.1:6379`
- **Nguyên nhân**: Redis chưa được khởi chạy hoặc cổng mạng bị chặn.
- **Giải pháp**:
  - Đảm bảo Redis service đang chạy (`wsl redis-cli ping` trả về `PONG` hoặc `docker ps` hiển thị container đang chạy).
  - Nếu sử dụng WSL 2, hãy kiểm tra lại file `/etc/redis/redis.conf` đã đổi thành `protected-mode no` chưa và restart lại dịch vụ. 
  - File cấu hình [config.py](file:///d:/github/ai-local-supporter/config.py) mặc định tự động dò tìm IP ảo của WSL (`172.20.xxx.xxx`) và kết nối trực tiếp đến nó nếu loopback `127.0.0.1` bị Windows Firewall chặn.

### 2. Gặp lỗi build `chroma-hnswlib` khi cài đặt thư viện
- **Nguyên nhân**: Thiếu Microsoft Visual C++ compiler trên Windows.
- **Giải pháp**: Đảm bảo file `requirements.txt` sử dụng phiên bản `chromadb>=0.5.3` để pip tự tải bản precompiled binary (.whl) mà không cần build từ mã nguồn.

### 3. Lỗi liên quan đến thư viện `python-magic` trên Windows
- **Giải pháp**: Không cài đặt `python-magic` gốc vì nó yêu cầu file DLL hệ thống của Linux. Trong codebase đã sử dụng cơ chế fallback thông minh khác để nhận diện loại file tải lên mà không cần thư viện này.

### 4. Celery báo lỗi: `Connection closed by server` hoặc ngắt kết nối liên tục khi sử dụng Redis trên WSL 2
- **Nguyên nhân**: Trên Windows 11, WSL 2 có cơ chế tự động tạm dừng hoặc tắt máy ảo (auto-pause/auto-shutdown) sau 15–60 giây không hoạt động để tiết kiệm pin/RAM. Do kết nối chạy nền từ Windows Host của Celery không được tính là hoạt động trực tiếp trên WSL, máy ảo WSL 2 sẽ tự động đi ngủ và ngắt kết nối socket của Redis.
- **Giải pháp**:
  Tắt tính năng tự động tạm dừng của WSL 2 bằng cách tạo hoặc cập nhật cấu hình WSL toàn cục:
  1. Tạo file `.wslconfig` trong thư mục User Profile của Windows (đường dẫn: `C:\Users\<Tên_User>\.wslconfig`).
  2. Thêm nội dung sau vào file và lưu lại:
     ```ini
     [general]
     instanceIdleTimeout=-1

     [wsl2]
     vmIdleTimeout=-1
     ```
  3. Mở PowerShell hoặc CMD và chạy lệnh sau để tắt hoàn toàn WSL (WSL sẽ tự khởi chạy lại kèm cấu hình mới ở lần kết nối tiếp theo):
     ```powershell
     wsl --shutdown
     ```

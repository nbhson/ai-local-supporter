# AI Local Support

WebUI phân tích tài liệu và code sử dụng **Ollama** (AI local) với hỗ trợ đa ngôn ngữ (Tiếng Việt/Tiếng Anh).

## 🚀 Tính năng

### 📄 Phân tích Tài liệu
- **Upload file**: Hỗ trợ PDF, DOCX, TXT, MD, CSV, JSON, XML, YAML
- **Hình ảnh**: Hỗ trợ PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP
- **Vision Model**: Phân tích ảnh trực tiếp với qwen2.5-vl, llava, moondream
- **OCR Fallback**: Tesseract OCR cho model không hỗ trợ vision
- 💬 **Chat với tài liệu**: Đặt câu hỏi về nội dung, AI trả lời dựa trên tài liệu
- 🎯 **Câu hỏi gợi ý**: Tóm tắt, điểm chính, kết luận

### 💻 Phân tích Code
- **Paste code**: Hỗ trợ mọi ngôn ngữ lập trình
- 🔍 **Phân tích cú pháp**: Ngôn ngữ, mục đích, thành phần chính
- ⚠️ **Phát hiện lỗi**: Vấn đề tiềm ẩn và cải tiến
- ⚡ **Đề xuất tối ưu**: Cải thiện performance và chất lượng
- 💬 **Chat về code**: Đặt câu hỏi chi tiết về logic

### 📁 Dự án (Project Workspace Agent)
- 🤖 **AI Coding Agent**: Hoạt động như một Software Engineer thực thụ dựa trên mô hình **ReAct (Reasoning and Action)**.
- ⚙️ **Tự động hóa hoàn toàn (Auto-planning)**: AI tự động lên kế hoạch và thực thi công việc mà không cần người dùng chọn file thủ công.
- 🛠️ **Hệ thống Tools cục bộ**: AI tự động tìm kiếm file, đọc/ghi đè/tạo file mới, duyệt cấu trúc thư mục, và chạy thử nghiệm (RUN_COMMAND) ngay trên dự án.
- 🔄 **Realtime Interactive UI**: Timeline hiển thị chi tiết các bước suy nghĩ (thoughts), tool gọi và logs, kèm theo khả năng cập nhật code tự động lên Editor Monaco.

### 💬 Trò chuyện tự do
- **Hỏi đáp đa năng**: Trò chuyện tự do với AI không cần ngữ cảnh tài liệu hoặc mã nguồn
- 🎯 **Câu hỏi gợi ý**: Gợi ý nhanh các chủ đề công nghệ, viết lách, kế hoạch du lịch
- 🔄 **Lưu trữ lịch sử**: Lưu trữ lịch sử hội thoại tự động vào SQLite

### 🎨 Giao diện
- 🌐 **Đa ngôn ngữ**: Tiếng Việt / Tiếng Anh
- 🎯 **Đa model**: Chọn bất kỳ model Ollama nào đã cài
- 🎨 **Dark mode**: Giao diện tối, responsive
- 📱 **Drag & drop**: Upload file dễ dàng

## 📋 Yêu cầu

- **Python 3.8+**
- **Ollama** (đã cài và chạy) - [ollama.ai](https://ollama.ai)
- **Model Ollama** (ví dụ: `qwen2.5-coder:14b`, `deepseek-r1:14b`, `qwen2.5-vl:7b`)
- **Model Embedding cho RAG**: `nomic-embed-text`
- **Redis Server** (làm message broker cho Celery)
- **Tesseract OCR** (tùy chọn, cho OCR fallback) - [github.com/tesseract-ocr](https://github.com/tesseract-ocr/tesseract)

## ⚙️ Cài đặt & Chạy ứng dụng

> [!TIP]
> Để xem chi tiết các bước thiết lập và khắc phục lỗi chi tiết đối với từng hệ điều hành, hãy tham khảo tài liệu: [INSTALLATION.md](file:///d:/github/ai-local-supporter/INSTALLATION.md).

### 1. Clone project và di chuyển vào thư mục dự án

```bash
git clone <your-repo-url>
cd ai-local-support
```

### 2. Khởi tạo môi trường ảo & Cài đặt thư viện Python

Khuyến nghị sử dụng môi trường ảo (`venv`) để tránh xung đột thư viện hệ thống:

```bash
# Khởi tạo môi trường ảo (.venv)
python3 -m venv .venv

# Kích hoạt môi trường ảo
# Trên macOS/Linux:
source .venv/bin/activate
# Trên Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Trên Windows (CMD):
.venv\Scripts\activate.bat

# Nâng cấp pip và cài đặt các dependencies từ requirements.txt
pip install --upgrade pip
pip install -r requirements.txt

# hoặc
python3 -m pip install -r requirements.txt
```

> [!IMPORTANT]
> **Lưu ý đối với Windows:**
> - Nếu chạy trên PowerShell, bạn phải sử dụng tiền tố đường dẫn rõ ràng và phần mở rộng của script: `.\.venv\Scripts\Activate.ps1`.
> - Nếu gặp lỗi thông báo script bị vô hiệu hóa (*Execution Policy*), hãy cấp quyền chạy script trong phiên làm việc hiện tại bằng lệnh: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`.
> - Nếu gặp lỗi build `chroma-hnswlib` (yêu cầu *Microsoft Visual C++ 14.0 or greater*), hãy đảm bảo rằng file `requirements.txt` sử dụng phiên bản `chromadb>=0.5.3` (hoặc mới hơn). Điều này cho phép pip tải xuống các bản precompiled binary wheels (hỗ trợ `abi3` ổn định cho Python 3.12) mà không cần biên dịch lại từ mã nguồn C++.
> - Thư viện `python-magic` đã được comment lại trong `requirements.txt` vì không sử dụng trực tiếp trong code của dự án và có thể gây lỗi cài đặt hoặc chạy trên Windows do thiếu các file thư viện động hệ thống (`libmagic` DLLs).

### 3. Cài đặt các model Ollama

Đảm bảo bạn đã cài đặt và chạy ứng dụng **Ollama** trên máy. Sau đó kéo các model sau về:

```bash
# Kiểm tra danh sách các model hiện tại
ollama list

# Tải model LLM mặc định cho việc chat & phân tích tài liệu/code (ví dụ)
ollama pull qwen2.5-coder:14b

# BẮT BUỘC: Tải model embedding để phục vụ tính năng RAG tìm kiếm ngữ cảnh
ollama pull nomic-embed-text
```

### 4. Cài đặt & Khởi chạy Redis Server

Redis đóng vai trò làm message broker để truyền tải các tác vụ xử lý tài liệu chạy ngầm từ Flask app qua Celery worker.

*   **macOS (sử dụng Homebrew):**
    ```bash
    brew install redis
    brew services start redis
    ```
*   **Docker (khuyên dùng cho mọi OS):**
    ```bash
    docker run -d -p 6379:6379 --name redis-broker redis:alpine
    ```
*   **Windows (sử dụng WSL - khuyên dùng nếu không có Docker):**
    Nếu bạn đã cài đặt WSL (Windows Subsystem for Linux), bạn có thể cài đặt và khởi chạy Redis trực tiếp từ Linux terminal của WSL (ví dụ: Ubuntu):
    ```bash
    # Cài đặt Redis trong WSL
    sudo apt update
    sudo apt install redis-server

    # Khởi động dịch vụ Redis
    sudo service redis-server start
    ```
    *Lưu ý:* WSL 2 sẽ tự động ánh xạ cổng `6379` từ môi trường ảo về `localhost` của Windows. Do đó, các ứng dụng trên Windows của bạn có thể truy cập Redis trực tiếp qua cổng `6379` mà không cần cấu hình gì thêm.

*   **Kiểm tra & Giám sát hoạt động của Redis (Review Redis):**
    ```bash
    # Gửi lệnh PING để kiểm tra kết nối (nếu trả về PONG là thành công)
    redis-cli ping

    # Giám sát các luồng dữ liệu truyền nhận theo thời gian thực
    redis-cli monitor

    # Xem logs của Redis container (nếu chạy qua Docker)
    docker logs redis-broker
    ```

### 5. Khởi chạy hệ thống

Để ứng dụng hoạt động đầy đủ, bạn cần mở **2 terminal** chạy song song 2 thành phần (đều cần kích hoạt môi trường ảo `.venv` trước khi chạy):

**Terminal 1: Khởi chạy Celery Worker (xử lý tài liệu ngầm, OCR, RAG Indexing)**
- **Trên macOS/Linux:**
  ```bash
  # Kích hoạt venv trước
  source .venv/bin/activate
  # Chạy worker
  celery -A tasks.celery worker --loglevel=info
  ```
- **Trên Windows:**
  Celery trên Windows cần chạy với pool `solo` do cơ chế prefork mặc định không tương thích tốt:
  ```bash
  # Kích hoạt venv trước (CMD hoặc PowerShell)
  .venv\Scripts\activate
  # Chạy worker với pool solo
  celery -A tasks.celery worker --loglevel=info --pool=solo
  ```

**Terminal 2: Khởi chạy Flask Web Application**
```bash
# Kích hoạt venv trước
source .venv/bin/activate
# Khởi chạy server
python3 app.py
```

Sau khi cả 2 thành phần khởi động thành công, mở trình duyệt tại: **http://127.0.0.1:5001**

### 6. Cấu hình (Tùy chọn)

Bạn có thể thay đổi các cấu hình như Model mặc định, URL cổng kết nối, Redis Broker URL bằng cách truyền các biến môi trường hoặc sửa trực tiếp trong file [config.py](file:///Users/nguyenson/Github/ai-local-support/config.py):

| Biến môi trường | Ý nghĩa | Giá trị mặc định |
|---|---|---|
| `OLLAMA_URL` | URL kết nối tới Ollama | `http://localhost:11434/api` |
| `DEFAULT_MODEL` | Model LLM mặc định phân tích và chat | `qwen2.5-coder:14b` |
| `EMBEDDING_MODEL` | Model nhúng vector cho cơ sở dữ liệu RAG | `nomic-embed-text` |
| `DATABASE_URL` | URI kết nối cơ sở dữ liệu SQLite | `sqlite:///ai_local_support.db` |
| `CELERY_BROKER_URL` | URL của Redis Broker dành cho Celery | `redis://localhost:6379/0` |


## 🎮 Cách sử dụng

### 📄 Phân tích Tài liệu
1. **Chọn tab "Tài liệu"**
2. **Chọn model** AI từ dropdown
3. **Chọn ngôn ngữ**: Tiếng Việt / Tiếng Anh
4. **Upload file**: Kéo-thả hoặc click vào vùng upload
5. **Xem phân tích**: AI tự động phân tích và hiển thị kết quả
6. **Đặt câu hỏi**: Nhập câu hỏi về nội dung tài liệu
7. **Xóa session**: Click icon thùng rác để upload file mới

### 💻 Phân tích Code
1. **Chọn tab "Code"**
2. **Chọn ngôn ngữ** code từ dropdown (Tự động, Python, JavaScript, ...)
3. **Paste code** vào textarea
4. **Click "Phân tích Code"** hoặc Ctrl+Enter
5. **Xem phân tích**: AI phân tích cú pháp, logic, vấn đề
6. **Đặt câu hỏi**: Hỏi về chi tiết code
7. **Xóa session**: Click icon thùng rác để paste code mới

### 💬 Trò chuyện tự do
1. **Chọn tab "Trò chuyện"**
2. **Chọn model** AI và **Ngôn ngữ** mong muốn từ sidebar
3. **Nhập câu hỏi** và bắt đầu trò chuyện trực tiếp với AI
4. **Xóa session**: Click icon thùng rác để xóa lịch sử cuộc trò chuyện và bắt đầu phiên mới

### 📁 Dự án / Project Workspace
1. **Chọn tab "Dự án"**
2. **Nhập đường dẫn tuyệt đối** tới dự án của bạn (ví dụ: `/path/to/project`) và click **"Mở cục bộ"**.
3. **Gửi yêu cầu chỉnh sửa**: Ví dụ: *"Thêm logging vào file server.py và chạy lệnh pytest để kiểm tra"*.
4. **Quan sát Agent làm việc**: AI sẽ tự lập kế hoạch, tìm file, đọc nội dung, thực hiện thay đổi, chạy lệnh và hoàn thành nhiệm vụ. Cây thư mục và Editor sẽ tự động reload code mới ngay khi Agent chỉnh sửa.


## 📁 Cấu trúc project

Cấu trúc dự án đã được tối ưu hóa theo dạng Module hóa để dễ dàng bảo trì và mở rộng:

```
ai-local-support/
├── app.py                  # Khởi chạy Flask Web Server & API
├── celery_app.py           # Cấu hình khởi tạo Celery App
├── tasks.py                # Định nghĩa các tác vụ Celery chạy ngầm (xử lý file, OCR, RAG Indexing)
├── config.py               # Các cấu hình tham số hệ thống (model, db path, upload limit...)
├── requirements.txt        # Danh sách các thư viện Python phụ thuộc
├── README.md               # Hướng dẫn cài đặt & sử dụng
├── INSTALLATION.md         # Hướng dẫn cài đặt chi tiết trên macOS & Windows
├── ARCHITECTURE.md         # Tài liệu giải thích kiến trúc chi tiết của dự án
├── blueprints/             # Quản lý các API endpoint được phân tách theo module
│   ├── __init__.py
│   ├── doc.py              # Xử lý API liên quan đến Tài liệu (Upload, Chat RAG, Trạng thái)
│   ├── code.py             # Xử lý API liên quan đến Code (Phân tích, Chat Code)
│   └── chat.py             # Xử lý API liên quan đến Trò chuyện tự do (Khởi tạo, Chat, Xóa session)
├── services/               # Lớp xử lý logic nghiệp vụ nghiệp vụ (Business Logic)
│   ├── __init__.py
│   ├── database.py         # Khởi tạo instance SQLAlchemy
│   ├── models.py           # Định nghĩa cấu trúc các bảng Database (SQLite Schema)
│   ├── document_service.py # Xử lý đọc file PDF, Word, TXT, nén ảnh, chạy Tesseract OCR
│   ├── ollama_service.py   # Tích hợp và gọi các API kết nối Ollama Local
│   └── rag_service.py      # Xử lý nhúng vector và tìm kiếm ngữ cảnh với ChromaDB
├── templates/              # Thư mục chứa giao diện HTML
│   └── index.html          # Giao diện chính ứng dụng Single Page
├── static/                 # Thư mục tài nguyên tĩnh
│   ├── style.css           # Định nghĩa giao diện tối (Dark theme) hiện đại
│   └── app.js              # Xử lý logic frontend và streaming kết quả từ API
├── uploads/                # Thư mục chứa file upload (được tạo tự động)
└── chroma_db/              # Thư mục lưu trữ database vector ChromaDB (được tạo tự động)
```

## 🔌 API Endpoints

### Document Module
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/doc/upload` | Tải lên tài liệu/ảnh mới (bắt đầu một session) |
| GET | `/api/doc/status/<session_id>` | Kiểm tra trạng thái xử lý tài liệu ngầm của Celery |
| POST | `/api/doc/chat` | Chat/hỏi đáp (RAG/Vision) với tài liệu trong session |
| POST | `/api/doc/session/<session_id>/clear` | Xóa lịch sử chat trong session nhưng giữ file đã upload |

### Code Module
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/code/analyze` | Gửi code để phân tích ban đầu (bắt đầu một session) |
| POST | `/api/code/chat` | Chat/hỏi đáp về logic, lỗi, tối ưu hóa của đoạn code trong session |
| POST | `/api/code/session/<session_id>/clear` | Xóa lịch sử chat về đoạn code trong session |

### Chat Module
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/chat/init` | Khởi tạo một phiên trò chuyện tự do mới |
| POST | `/api/chat/chat` | Trò chuyện tự do và nhận phản hồi dạng stream từ model |
| POST | `/api/chat/session/<session_id>/clear` | Xóa lịch sử trò chuyện tự do trong session |

### Common
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/` | Trả về giao diện WebUI chính |
| GET | `/api/models` | Lấy danh sách các model Ollama đã tải về ở máy local |

## 🛠 Công nghệ

- **Backend**: Python Flask
- **Frontend**: HTML, CSS, JavaScript (thuần)
- **AI**: Ollama (local LLM)
- **Document Processing**: PyPDF2, python-docx
- **OCR**: Tesseract (tùy chọn)
- **Image Processing**: Pillow (PIL)

## 📝 Ghi chú

- File upload tối đa **50MB** (có thể cấu hình lại trong [config.py](file:///Users/nguyenson/Github/ai-local-support/config.py)).
- Hệ thống hỗ trợ RAG (cơ sở dữ liệu vector ChromaDB) giúp đọc tài liệu dài không giới hạn số trang. Chat với Code sẽ giới hạn độ dài mã nguồn gửi lên ở mức **15,000 ký tự**.
- Dữ liệu session và lịch sử hội thoại được lưu trữ bền vững trong cơ sở dữ liệu SQLite (`ai_local_support.db`) thay vì lưu trong RAM, khởi động lại server không bị mất chat history.
- Port mặc định là **5001** để tránh xung đột với dịch vụ AirPlay Receiver mặc định trên macOS Catalina trở lên.
- Hỗ trợ **đa ngôn ngữ** (Tiếng Việt và Tiếng Anh) cho cả hướng dẫn hệ thống lẫn phản hồi của trợ lý AI.
- Vision models cần GPU đủ mạnh để xử lý ảnh, nếu tài nguyên hạn chế nên sử dụng OCR fallback.

## 🐛 Troubleshooting

**Tài liệu cứ hiển thị "Đang phân tích..." (processing) mãi không đổi trạng thái?**
- Đảm bảo bạn đã khởi chạy Redis Server thành công (`docker ps` hoặc `brew services list`).
- Kiểm tra kết nối tới Redis bằng cách chạy lệnh: `redis-cli ping` (phản hồi `PONG` là hoạt động tốt).
- Bạn có thể xem các task đang chuyển tải qua Redis theo thời gian thực bằng lệnh: `redis-cli monitor`.
- Đảm bảo bạn đã khởi chạy Celery worker bằng lệnh: `celery -A tasks.celery worker --loglevel=info` trong môi trường ảo `.venv` đã kích hoạt.
- Kiểm tra log của Celery worker để xem có lỗi gì khi import thư viện hoặc lỗi kết nối Redis/Ollama không.

**Celery báo lỗi `redis.exceptions.ConnectionError: Connection closed by server` hoặc mất kết nối liên tục khi kết nối với Redis trên WSL 2?**
- **Nguyên nhân**: Trên Windows 11, WSL 2 tự động tạm dừng hoặc tắt máy ảo (auto-pause/auto-shutdown) sau 15–60 giây rảnh rỗi để tối ưu hóa hiệu năng và pin. Các kết nối chạy nền từ Windows Host của Celery không được WSL 2 tính là hoạt động trực tiếp, khiến máy ảo WSL 2 đi ngủ và đóng kết nối socket của Redis.
- **Giải pháp**:
  Tạo hoặc chỉnh sửa file cấu hình WSL toàn cục tại `C:\Users\<Tên_User>\.wslconfig` (trong thư mục User Profile của Windows) với nội dung:
  ```ini
  [general]
  instanceIdleTimeout=-1

  [wsl2]
  vmIdleTimeout=-1
  ```
  Sau đó chạy lệnh sau trong cmd/PowerShell của Windows để áp dụng cấu hình:
  ```powershell
  wsl --shutdown
  ```

**Port 5001 đã được sử dụng?**
```bash
# Kiểm tra process đang dùng port
lsof -i :5001

# Kill process đang chiếm dụng port
kill -9 <PID>
```

**Ollama không kết nối được?**
```bash
# Kiểm tra dịch vụ Ollama có phản hồi danh sách model không
ollama list

# Khởi động lại ứng dụng Ollama Desktop hoặc chạy lệnh sau để khởi động service:
ollama serve
```

**OCR không hoạt động khi upload ảnh với model thường?**
- Đảm bảo bạn đã cài đặt thư viện hệ thống Tesseract OCR:
  *   **macOS:** `brew install tesseract tesseract-lang` (cần cài bản `-lang` để hỗ trợ tiếng Việt)
  *   **Ubuntu:** `sudo apt-get install tesseract-ocr tesseract-ocr-vie`
  *   **Windows:** Tải file cài đặt (installer `.exe`) từ [UB Mannheim Tesseract Wiki](https://github.com/UB-Mannheim/tesseract/wiki). Trong quá trình cài đặt, chọn tải thêm gói ngôn ngữ **Vietnamese** (tiếng Việt). Sau khi cài đặt hoàn tất, bạn cần thêm đường dẫn của thư mục cài đặt (mặc định là `C:\Program Files\Tesseract-OCR`) vào biến môi trường hệ thống **PATH** và khởi động lại terminal.
- Kiểm tra xem Tesseract đã hoạt động trong Terminal:
```bash
# Kiểm tra phiên bản
tesseract --version

# Kiểm tra các ngôn ngữ OCR được hỗ trợ (cần thấy 'vie' và 'eng')
tesseract --list-langs
```

**Vision model không nhận diện được ảnh?**
- Đảm bảo model bạn chọn nằm trong tập hợp các vision model hỗ trợ (ví dụ: `qwen2.5-vl`, `llava`, `moondream`).
- Kiểm tra xem GPU của máy có bị quá tải VRAM dẫn đến model bị tắt (killed) giữa chừng không.
- Thử chuyển sang dùng model không phải vision (như `qwen2.5-coder`) để kích hoạt tính năng **OCR fallback** sử dụng Tesseract.

## 📄 License

MIT License

## 👨‍💻 Author

AI Local Support - Powered by Ollama + Flask
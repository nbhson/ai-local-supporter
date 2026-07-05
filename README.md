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

### 🎨 Giao diện
- 🌐 **Đa ngôn ngữ**: Tiếng Việt / Tiếng Anh
- 🎯 **Đa model**: Chọn bất kỳ model Ollama nào đã cài
- 🎨 **Dark mode**: Giao diện tối, responsive
- 📱 **Drag & drop**: Upload file dễ dàng

## 📋 Yêu cầu

- **Python 3.8+**
- **Ollama** (đã cài và chạy) - [ollama.ai](https://ollama.ai)
- **Model Ollama** (ví dụ: `qwen2.5-coder:14b`, `deepseek-r1:14b`, `qwen2.5-vl:7b`)
- **Tesseract OCR** (tùy chọn, cho OCR fallback) - [github.com/tesseract-ocr](https://github.com/tesseract-ocr/tesseract)

## ⚙️ Cài đặt

### 1. Clone project

```bash
git clone <your-repo-url>
cd ai-local-support
```

### 2. Cài đặt Python dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Cài model Ollama (nếu chưa có)

```bash
# Liệt kê model đã cài
ollama list

# Model cho document analysis
ollama pull qwen2.5-coder:14b

# Model cho code analysis
ollama pull deepseek-r1:14b

# Model cho vision/image analysis (tùy chọn)
ollama pull qwen2.5-vl:7b
ollama pull llava
```

### 4. Cài Tesseract OCR (tùy chọn, cho OCR fallback)

**macOS:**
```bash
brew install tesseract
brew install tesseract-lang  # Cho hỗ trợ tiếng Việt
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-vie  # Cho hỗ trợ tiếng Việt
```

### 5. Chạy ứng dụng

```bash
python3 app.py
```

Mở trình duyệt tại: **http://127.0.0.1:5001**

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

## 📁 Cấu trúc project

```
ai-local-support/
├── app.py                  # Backend Flask (API + Ollama integration)
├── requirements.txt        # Python dependencies
├── README.md               # Tài liệu hướng dẫn
├── uploads/                # Thư mục lưu file upload (tự động tạo)
├── templates/
│   └── index.html          # Giao diện chính (HTML + JS)
└── static/
    └── style.css           # CSS styling (dark theme)
```

## 🔌 API Endpoints

### Document Module
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/doc/upload` | Upload file + phân tích |
| POST | `/api/doc/chat` | Chat về tài liệu |
| POST | `/api/doc/session/<id>/clear` | Xóa lịch sử chat |

### Code Module
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/code/analyze` | Phân tích code |
| POST | `/api/code/chat` | Chat về code |
| POST | `/api/code/session/<id>/clear` | Xóa lịch sử chat |

### Common
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/` | Trang chủ WebUI |
| GET | `/api/models` | Danh sách model Ollama |

## 🛠 Công nghệ

- **Backend**: Python Flask
- **Frontend**: HTML, CSS, JavaScript (thuần)
- **AI**: Ollama (local LLM)
- **Document Processing**: PyPDF2, python-docx
- **OCR**: Tesseract (tùy chọn)
- **Image Processing**: Pillow (PIL)

## 📝 Ghi chú

- File upload tối đa **50MB**
- Nội dung file dài sẽ được cắt ngắn (15,000 ký tự) để phù hợp context window
- Dữ liệu session lưu trong RAM (mất khi restart server)
- Port mặc định là **5001** (tránh xung đột với AirPlay Receiver trên macOS)
- Hỗ trợ **đa ngôn ngữ**: Tiếng Việt và Tiếng Anh
- Vision models cần GPU đủ mạnh để xử lý ảnh

## 🐛 Troubleshooting

**Port 5001 đã được sử dụng?**
```bash
# Kiểm tra process đang dùng port
lsof -i :5001

# Kill process
kill -9 <PID>
```

**Ollama không kết nối được?**
```bash
# Kiểm tra Ollama đang chạy
ollama list

# Khởi động Ollama nếu cần
ollama serve
```

**OCR không hoạt động?**
```bash
# Kiểm tra Tesseract đã cài
tesseract --version

# Kiểm tra ngôn ngữ đã cài
tesseract --list-langs

# Cài thêm ngôn ngữ nếu cần (ví dụ: tiếng Việt)
brew install tesseract-lang  # macOS
sudo apt-get install tesseract-ocr-vie  # Ubuntu
```

**Vision model không nhận diện được ảnh?**
- Đảm bảo model là vision model: `qwen2.5-vl`, `llava`, `moondream`, `bakllava`, `cog-vlm`
- Kiểm tra GPU có đủ VRAM không
- Thử dùng OCR fallback nếu vision model không hoạt động

## 📄 License

MIT License

## 👨‍💻 Author

AI Local Support - Powered by Ollama + Flask
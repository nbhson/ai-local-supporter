# AI Local Support

WebUI phân tích tài liệu và code sử dụng **Ollama** (AI local) với hỗ trợ đa ngôn ngữ (Tiếng Việt/Tiếng Anh).

---

## 📖 Tài liệu hướng dẫn (Documentation)

- 🚀 **[Hướng dẫn Cài đặt & Khắc phục sự cố](INSTALLATION.md)**: Chi tiết cách cài đặt các thành phần phụ thuộc, tải model Ollama, thiết lập Redis và giải quyết các lỗi thường gặp trên macOS và Windows.
- 📐 **[Tài liệu Kiến trúc Hệ thống](ARCHITECTURE.md)**: Giải thích chi tiết về sơ đồ kiến trúc, các design pattern áp dụng, cấu trúc thư mục dự án, cấu trúc cơ sở dữ liệu và các API endpoints của hệ thống.
- ⚡ **[So sánh hiệu năng: CLI vs. App](OLLAMA_CLI_VS_APP.md)**: Giải thích tại sao chạy Ollama qua dòng lệnh nhanh hơn qua giao diện App/Web và cách tối ưu hóa.


---

## 🚀 Tính năng chính

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

---

## 🎮 Cách sử dụng nhanh

1. **Phân tích Tài liệu**: Chọn tab "Tài liệu", chọn model/ngôn ngữ, upload file và bắt đầu chat với tài liệu.
2. **Phân tích Code**: Chọn tab "Code", dán đoạn mã nguồn cần phân tích, chọn ngôn ngữ và bấm nút phân tích, sau đó chat để hỏi sâu hơn.
3. **Trò chuyện tự do**: Chọn tab "Trò chuyện", chọn model/ngôn ngữ ở sidebar và bắt đầu trò chuyện trực tiếp không cần ngữ cảnh.
4. **Dự án (Project Workspace)**: Chọn tab "Dự án", nhập đường dẫn tuyệt đối tới thư mục dự án và bắt đầu ra lệnh cho Coding Agent (ví dụ: *"Thêm logging vào file server.py và chạy thử"*).

---

## 🛠 Công nghệ sử dụng

- **Backend**: Python Flask, Celery
- **Frontend**: HTML, CSS, JavaScript (thuần)
- **AI / LLM**: Ollama (Local LLM), FastEmbed (Local CPU-based Embedding)
- **Database**: SQLite (Session history), ChromaDB (Vector DB)
- **Message Broker**: Redis (Celery task queue)
- **OCR Engine**: Tesseract OCR (Fallback)

---

## 📄 License

MIT License

## 👨‍💻 Author

AI Local Support - Powered by Ollama + Flask
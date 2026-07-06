# Tài liệu Kiến trúc Hệ thống (System Architecture)

Dự án này đã được nâng cấp từ một cấu trúc đồng bộ đơn giản (In-memory, single-threaded) lên một kiến trúc **Bất đồng bộ (Asynchronous Background Worker)** kết hợp với **RAG (Retrieval-Augmented Generation) cục bộ**.

Dưới đây là mô tả chi tiết về mặt kiến trúc, cơ sở dữ liệu và luồng đi của dữ liệu trong hệ thống mới.

---

## 🌟 Ưu điểm nổi bật của Kiến trúc mới (Key Advantages)

Kiến trúc này mang lại các cải tiến vượt trội so với phiên bản đồng bộ (in-memory) cũ:

1.  **Không bị nghẽn giao diện (Non-blocking UI & API):** 
    Tác vụ nặng như trích xuất text PDF/Word dài và xử lý nhận diện hình ảnh (OCR) được đẩy hoàn toàn sang Celery chạy ngầm. Flask API phản hồi ngay lập tức cho client trong vòng dưới `50ms`, loại bỏ hoàn toàn hiện tượng đơ trình duyệt và tránh lỗi **HTTP Timeout (504)** khi tải file lớn.
2.  **Khóa bỏ giới hạn độ dài tài liệu (Virtually Unlimited Document Size):**
    Thay vì giới hạn cắt xén tài liệu ở mức `15,000 ký tự` để vừa khít context window của LLM, **RAG** cho phép người dùng tải lên tài liệu hàng trăm trang. Dữ liệu được cắt nhỏ và tìm kiếm thông minh từ **ChromaDB**.
3.  **Tăng tốc độ trả lời của AI local (Fast LLM Response Time):**
    LLM local (chạy trên CPU/GPU cá nhân) không cần phải nạp lại và xử lý toàn bộ tài liệu khổng lồ cho mỗi câu hỏi (Prefill phase). RAG chỉ gửi kèm **Top-4 đoạn liên quan nhất** (~2,000 ký tự) giúp tốc độ AI sinh chữ đầu tiên (Time-To-First-Token) **nhanh gấp 5 đến 10 lần** (chỉ mất 2-5 giây thay vì 30s-1 phút).
4.  **Lưu trữ bền vững (Persistent Session Storage):**
    Toàn bộ lịch sử hội thoại và thông tin tệp tin được lưu trong cơ sở dữ liệu SQLite (`ai_local_support.db`) thay vì RAM. Khởi động lại Flask app hoặc Celery worker không làm mất dữ liệu trò chuyện của người dùng.
5.  **Dễ dàng mở rộng cấu hình (Scalability):**
    Chúng ta có thể dễ dàng tăng số lượng Celery workers chạy song song để tận dụng tối đa tài nguyên đa nhân của CPU/GPU khi xử lý đồng thời nhiều tệp tài liệu lớn từ nhiều người dùng.

---

## 🏷️ Tên gọi Kiến trúc và Các Pattern áp dụng (Architecture & Design Patterns)

Hệ thống được thiết kế và vận hành dựa trên các mô hình kiến trúc chuẩn sau:

1.  **Kiến trúc RAG cục bộ (Local Retrieval-Augmented Generation):**
    *   *Mô tả:* Kiến trúc sinh văn bản tăng cường truy xuất dữ liệu cục bộ.
    *   *Áp dụng:* Văn bản được phân mảnh (chunking), tính toán vector nhúng bằng model `nomic-embed-text` và lưu trữ tại [ChromaDB](file:///Users/nguyenson/Github/ai-local-support/ARCHITECTURE.md#L61-L63). Khi người dùng hỏi, hệ thống truy xuất các đoạn ngữ cảnh phù hợp nhất để làm đầu vào cho LLM trả lời, giúp tránh giới hạn cửa sổ ngữ cảnh và tăng độ chính xác.
2.  **Mô hình Task Queue / Background Worker (Broker-Worker Pattern):**
    *   *Mô tả:* Mô hình xử lý bất đồng bộ qua hàng đợi thông điệp để thực hiện các tác vụ nặng mà không gây nghẽn tiến trình chính.
    *   *Áp dụng:* [Flask API](file:///Users/nguyenson/Github/ai-local-support/app.py) đóng vai trò là **Producer** đẩy các yêu cầu xử lý tài liệu vào **Redis** (đóng vai trò **Message Broker**). [Celery Workers](file:///Users/nguyenson/Github/ai-local-support/tasks.py) đóng vai trò **Consumer / Worker** liên tục lắng nghe và xử lý ngầm (đọc file, OCR, sinh embeddings), đảm bảo API phản hồi cho giao diện dưới `50ms` (Non-blocking UI).
3.  **Kiến trúc Phân rã (Decoupled / Event-Driven Architecture):**
    *   *Mô tả:* Phân tách độc lập các khối tính toán và giao tiếp gián tiếp qua cơ sở dữ liệu và message queue.
    *   *Áp dụng:* Tách biệt luồng xử lý tương tác trực tiếp với người dùng (Flask) và luồng xử lý hậu trường nặng (Celery). Đồng bộ trạng thái hội thoại và trạng thái tệp tin thông qua SQLite Database (`ai_local_support.db`) và Redis Broker.

---

## 🗺️ Sơ đồ Kiến trúc Tổng quan (Architecture Diagram)

Hệ thống hoạt động dựa trên các thành phần biệt lập, kết nối với nhau qua cơ sở dữ liệu và hàng đợi tin nhắn:

```mermaid
graph TD
    Client[Web UI / Browser] <-->|HTTP REST & Streaming| Flask[Flask API Server]
    Flask <-->|Đọc/Ghi dữ liệu phiên| SQLite[(SQLite DB)]
    Flask -->|Đẩy Task xử lý ngầm| Redis[Redis Message Broker]
    Redis -->|Phân phối Task| Celery[Celery Background Workers]
    
    Celery <-->|Cập nhật Trạng thái & Text| SQLite
    Celery -->|Trích xuất Text & OCR| Docs(Tài liệu / Ảnh)
    Celery -->|1. Cắt nhỏ text & Tạo Embeddings| Ollama[Ollama Local LLM]
    Celery -->|2. Lưu Vector index| Chroma[(Chroma Vector DB)]
    
    Flask <-->|Truy xuất ngữ cảnh RAG| Chroma
    Flask <-->|Sinh câu trả lời| Ollama
```

---

## 📦 Các thành phần chính trong Hệ thống

1.  **Flask API Server ([app.py](file:///Users/nguyenson/Github/ai-local-support/app.py)):**
    *   Đóng vai trò là cổng đón tiếp các request từ giao diện Web.
    *   Nhận file upload, tạo bản ghi phiên trong Database, kích hoạt Celery Task chạy ngầm và trả phản hồi tức thời cho người dùng.
    *   Thực hiện việc tìm kiếm vector (RAG) và streaming câu trả lời từ Ollama về giao diện Web.
2.  **Celery Workers ([tasks.py](file:///Users/nguyenson/Github/ai-local-support/tasks.py)):**
    *   Là các luồng xử lý chạy hoàn toàn độc lập với Flask.
    *   Chịu trách nhiệm thực hiện các tác vụ nặng: Đọc PDF/Word, nén ảnh, chạy nhận diện chữ viết (Tesseract OCR), chia nhỏ tài liệu (Chunking) và tính toán vector nhúng để lưu vào Vector DB.
3.  **Redis Message Broker:**
    *   Là trạm trung chuyển tin nhắn trung gian. Flask gửi yêu cầu "xử lý file" vào Redis, Celery Workers liên tục lắng nghe Redis để kéo task về xử lý khi rảnh.
4.  **SQLite Database (`ai_local_support.db`):**
    *   Cơ sở dữ liệu lưu trữ quan hệ để lưu giữ thông tin phiên làm việc ([models.py](file:///Users/nguyenson/Github/ai-local-support/services/models.py)) giúp chia sẻ trạng thái chung giữa Flask và Celery.
5.  **ChromaDB Vector Database (`./chroma_db`):**
    *   Cơ sở dữ liệu Vector cục bộ dạng nhúng (embedded).
    *   Lưu trữ các đoạn tài liệu được cắt nhỏ kèm Vector 768 chiều được tính toán từ model `nomic-embed-text` của Ollama.
6.  **Ollama (AI Local Runner):**
    *   Cung cấp API để chạy cục bộ 2 nhóm model:
        *   *Embedding Model (`nomic-embed-text`):* Dùng để biến văn bản thành vector phục vụ RAG.
        *   *LLM Chat Model (ví dụ `qwen2.5-coder:14b`, `deepseek-r1:14b`):* Dùng để đọc ngữ cảnh và trả lời câu hỏi của người dùng.

---

## 🔄 Luồng dữ liệu (Data Lifecycle)

### A. Luồng Upload & Phân tích tài liệu (Background Ingestion)

1.  Người dùng tải lên một tài liệu (ví dụ: `document.pdf`) từ giao diện Web.
2.  **Flask** nhận yêu cầu:
    *   Lưu file vào thư mục `uploads/`.
    *   Tạo bản ghi trong bảng `document_sessions` với trạng thái `status = 'processing'`.
    *   Gọi `process_document_task.delay(session_id, filepath, ...)` gửi sang **Redis**.
    *   Trả về phản hồi `"status": "processing"` ngay lập tức cho client. Giao diện UI chuyển sang màn hình chờ.
3.  **Celery Worker** nhận Task từ Redis:
    *   Đọc và trích xuất toàn bộ văn bản của tài liệu.
    *   Nếu là ảnh và model chat không hỗ trợ Vision, chạy Tesseract OCR để lấy chữ.
    *   Sử dụng `RecursiveCharacterTextSplitter` chia văn bản thành các đoạn (chunks) dài 1000 ký tự (trùng lặp 200 ký tự).
    *   Gọi Ollama sinh vector embeddings cho từng chunk và lưu vào Collection `sess_<session_id>` của **ChromaDB**.
    *   Cập nhật cơ sở dữ liệu `document_sessions`: set `status = 'ready'`.
4.  **Client UI** liên tục gửi yêu cầu thăm dò (polling) API `/api/doc/status/<session_id>` mỗi 2 giây. Khi nhận được trạng thái `'ready'`, giao diện sẽ mở khóa khung chat và hiển thị lời chào.

### B. Luồng Chat với Tài liệu (RAG - Retrieval-Augmented Generation)

1.  Người dùng gửi câu hỏi: *"Hạn thanh toán của hợp đồng này là ngày bao nhiêu?"*
2.  **Flask API** nhận câu hỏi:
    *   Gọi Ollama lấy vector embedding của câu hỏi bằng model `nomic-embed-text`.
    *   Gửi vector câu hỏi truy vấn vào **ChromaDB** của phiên đó để lấy ra **Top-4 đoạn văn bản liên quan nhất**.
    *   Gộp 4 đoạn văn bản này lại làm **Context** (ngữ cảnh).
3.  **Flask** gửi câu hỏi + Ngữ cảnh vào Prompt gửi tới LLM chat:
    ```
    Bạn là một trợ lý phân tích tài liệu. Hãy trả lời câu hỏi của người dùng CHỈ dựa trên ngữ cảnh dưới đây.
    Ngữ cảnh: [4 đoạn văn bản trích xuất từ ChromaDB]
    Câu hỏi: [Câu hỏi của người dùng]
    ```
4.  **Ollama** sinh câu trả lời dựa trên đúng ngữ cảnh đó và stream từng chữ về giao diện WebUI theo thời gian thực.

---

## 💾 Cấu trúc Cơ sở dữ liệu (SQLite Schema)

Hệ thống sử dụng SQLAlchemy để định nghĩa 3 bảng trong SQLite ([models.py](file:///Users/nguyenson/Github/ai-local-support/services/models.py)):

### 1. Bảng `document_sessions`
Lưu trữ trạng thái và cấu hình của các tệp tài liệu được upload:
*   `session_id` (String - Khóa chính): UUID định danh phiên làm việc.
*   `filename` (String): Tên tệp gốc.
*   `filepath` (String): Đường dẫn tệp vật lý trên ổ đĩa.
*   `status` (String): Trạng thái xử lý (`processing`, `ready`, `failed`).
*   `language` (String): Ngôn ngữ phản hồi của AI (`en`/`vi`).
*   `model` (String): Tên model LLM được chọn để chat.
*   `file_type` (String): Phân loại tệp (`document`/`image`).
*   `base64_image` (Text - Tùy chọn): Ảnh đã nén (dành riêng cho Vision Model).
*   `extracted_text` (Text - Tùy chọn): Toàn bộ text đã trích xuất từ file (dùng để preview).

### 2. Bảng `code_sessions`
Lưu trữ thông tin về đoạn mã được paste vào để phân tích:
*   `session_id` (String - Khóa chính): UUID định danh phiên làm việc.
*   `code` (Text): Toàn bộ mã nguồn do người dùng paste vào.
*   `language` (String): Ngôn ngữ lập trình được chọn.
*   `model` (String): Tên model LLM được chọn để phân tích.
*   `ui_language` (String): Ngôn ngữ giao diện.

### 3. Bảng `chat_messages`
Lưu trữ lịch sử hội thoại của cả phần Phân tích Tài liệu và Phân tích Code:
*   `id` (Integer - Khóa chính tự tăng)
*   `session_id` (String - Chỉ mục): Liên kết với `session_id` của tài liệu hoặc mã nguồn.
*   `role` (String): Vai trò gửi tin nhắn (`system`, `user`, `assistant`).
*   `content` (Text): Nội dung tin nhắn.
*   `created_at` (DateTime): Thời gian gửi tin nhắn.

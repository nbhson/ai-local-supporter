# So sánh Các Kỹ thuật AI Engineering và Dự án Hiện tại

Tài liệu này so sánh 15 kỹ năng và kỹ thuật trong bảng của bạn với hai khía cạnh:
1. **Dự án hiện tại (`AI Local Support`)**: Hệ thống ứng dụng (WebUI, RAG, Coding Agent) được xây dựng trong mã nguồn của repo này.
2. **AI Agent Antigravity (Tôi)**: Hệ thống AI đang pair-programming trực tiếp với bạn thông qua IDE.

---

## Bảng So sánh Chi tiết

| # | Skill / Kỹ thuật | Cách Áp dụng trong Dự án Hiện tại (`AI Local Support`) | Cách Áp dụng của AI Agent Antigravity (Tôi) | Nhận xét & Điểm khác biệt chính |
|---|---|---|---|---|
| **1** | **Agent Engineering** | Tự phát triển một **AI Coding Agent** chạy vòng lặp **ReAct** (`agent_service.py`). Không dùng SDK ngoài mà tự định cấu hình `system_prompt` chứa Role, cây thư mục và cú pháp gọi Tool tùy chỉnh. | Sử dụng hệ thống hướng dẫn toàn cục (`AGENTS.md`) và thư viện kỹ năng cục bộ (`.agents/skills/`) để tự mở rộng khả năng của Agent tùy theo ngữ cảnh. | Dự án tự xây dựng Agent gọn nhẹ bằng Python thuần, trong khi tôi được tối ưu bởi hệ thống Skill & Rule hướng đối tượng từ nền tảng IDE. |
| **2** | **Prompt Engineering** | Định nghĩa system prompt tĩnh nhưng chứa các tham số động (như cây thư mục dự án). Yêu cầu LLM trả về cấu trúc đặc biệt dạng `[TOOL_NAME: args]`. | Sử dụng XML/Markdown tag để phân chia rõ ràng các phần suy nghĩ, lập kế hoạch, phản hồi và định cấu hình JSON Schema cho các tool call. | Dự án dùng cú pháp regex tự chế để phân tích cú pháp tool call từ text thô thay vì dùng JSON Schema của các API LLM tiêu chuẩn. |
| **3** | **Context Engineering** | **Quản lý cửa sổ ngữ cảnh (Context Window)**: Lắp ráp Prompt động bằng cách đưa Top-4 đoạn văn bản liên quan được lấy ra từ Retrieval Memory vào prompt cuối cùng gửi cho LLM. Trực tiếp cắt giảm/rút gọn kết quả trả về của các tool (như output của `RUN_COMMAND` được cắt gọn ở mức tối đa 15000 ký tự) để tránh tràn token. | Quản lý kích thước cửa sổ ngữ cảnh thông qua việc tự động lựa chọn file thông minh, nén ngữ cảnh và quản lý token đầu vào/đầu ra nghiêm ngặt. | Dự án quản lý ngữ cảnh ở mức độ cơ bản bằng cách chèn context tĩnh trích xuất từ DB và cắt ngắn text thô để tránh tràn. |
| **4** | **Workflow Engineering** | Triển khai vòng lặp **ReAct** thủ công (tối đa 10 lượt) bằng vòng lặp Python. Cho phép Agent gọi song song nhiều tool cùng lúc trong một lượt chạy. | Sử dụng **Planning Mode** (lên kế hoạch kỹ lưỡng `implementation_plan.md` -> tạo `task.md` TODO list -> duyệt -> thực thi -> cập nhật walkthrough). | Dự án sử dụng vòng lặp tuyến tính ReAct cơ bản, chưa có Plan Mode và Human-in-the-loop để người dùng duyệt từng bước hoặc sửa kế hoạch. |
| **5** | **Tool Engineering** | Đóng gói công cụ theo mẫu **Command Pattern** (`agent_tool_service.py`) gồm các tool cục bộ: `READ_FILE`, `WRITE_FILE`, `LIST_DIR`, `SEARCH_FILES`, `RUN_COMMAND`, `FINISH`. | Cung cấp hệ thống Tools phong phú: đọc/ghi file nâng cao, tìm kiếm web, terminal sandbox (`run_command`), browser automation (`browser_subagent`). | Cả hai đều cấp cho AI các tool tương tác hệ thống. Dự án giới hạn trong 6 tool lập trình cơ bản chạy bằng subprocess nội bộ. |
| **6** | **Memory Engineering** | Triển khai cả 2 loại bộ nhớ:<br>1. **Retrieval Memory**: Thực hiện phân mảnh (**Chunking**), tạo Vector nhúng (**Embeddings**) thông qua FastEmbed trên CPU và lập chỉ mục trong vector DB **ChromaDB** phục vụ truy xuất RAG.<br>2. **Session Memory**: Lưu trữ lâu bền lịch sử chat và trạng thái session qua cơ sở dữ liệu SQLite (`chat_messages`, `document_sessions`). | Tích hợp bộ nhớ hội thoại tự động, kết hợp RAG trên kho tri thức cục bộ và vector cache trên toàn hệ thống IDE. | Dự án áp dụng đầy đủ cả **Session Memory** (SQLite) và **Retrieval Memory** (ChromaDB + Chunking + Embeddings) làm nền tảng cho việc ghi nhớ và truy xuất tri thức. |
| **7** | **Knowledge Engineering** | Lưu trữ tài liệu kiến trúc hệ thống bằng các file markdown cấu trúc rõ ràng: `README.md`, `ARCHITECTURE.md`, `INSTALLATION.md`. | Truy xuất tri thức cục bộ từ thư mục `knowledge` (hệ thống **Knowledge Items - KI** chứa các snapshot tài liệu, rule của dự án). | Dự án tổ chức tri thức ở dạng tài liệu tĩnh cho con người đọc, trong khi tôi có thể đọc các file cấu trúc KI để hiểu các "gotchas" của dự án. |
| **8** | **Task Engineering** | Nhiệm vụ phân rã task được đẩy hoàn toàn cho LLM tự thực hiện thông qua block suy nghĩ `<think>...</think>` ở mỗi lượt chạy của ReAct. | Tự động tạo, theo dõi và cập nhật file `task.md` (TODO list dạng checklist) để đảm bảo không bỏ sót bước nào. | Tôi sử dụng cấu trúc WBS và Checklist tường minh để quản lý tiến độ, còn Agent của dự án quản lý ngầm trong context LLM. |
| **9** | **Review Engineering** | Hiện tại **chưa tích hợp** quy trình tự động review mã nguồn hoặc phân tích Git Diff trước khi hoàn thành task. | Kiểm tra mã nguồn bằng các linting rule và phân tích các thay đổi trước khi viết lại file. | Dự án không có tầng kiểm tra code review tự động cho Agent. |
| **10** | **Verification Engineering** | Agent có thể gọi `RUN_COMMAND` để chạy test (ví dụ: `pytest tests/test_basic.py`) nhằm tự kiểm tra code sau khi sửa. | Tự động hoặc hướng dẫn người dùng chạy thử nghiệm, xây dựng dự án và kiểm thử trước khi bàn giao (Walkthrough). | Cả hai đều áp dụng vòng lặp kiểm tra-sửa lỗi (Test-Fail-Fix Loop). Dự án có sẵn một bộ pytest cơ bản cho việc này. |
| **11** | **Multi-Agent Engineering** | **Chưa áp dụng**. Chỉ chạy cấu trúc Single-Agent chạy tuần tự. | Triển khai các **Subagents** chuyên biệt (như Browser Subagent) để giải quyết các nhánh nhiệm vụ khó một cách độc lập. | Dự án chưa có cơ chế điều phối đa Agent (Multi-Agent). |
| **12** | **Automation Engineering** | Sử dụng **Celery** + **Redis** để tự động hóa các tiến trình xử lý ngầm nặng (trích xuất text, OCR, tạo embeddings) một cách bất đồng bộ. | Tự động kích hoạt các trigger và timers thông qua hệ thống lập lịch (`schedule`). | Dự án áp dụng tự động hóa tốt ở tầng xử lý nền (Celery/Redis worker) để tăng tốc độ phản hồi UI. |
| **13** | **Evaluation Engineering** | **Chưa áp dụng** hệ thống tự động đo lường độ chính xác (Hallucination), tỷ lệ build thành công hay latency trong code. | Theo dõi sát sao các chỉ số token, chi phí và thời gian phản hồi của model. | Điểm trống của cả dự án hiện tại là chưa có bộ Benchmark/Eval Suite tự động cho AI. |
| **14** | **Guardrail Engineering** | Triển khai hàm `safe_join_project_path` bảo vệ khỏi tấn công **Path Traversal** và bỏ qua các file lớn (>500KB) hoặc thư mục hệ thống nguy hại. | Cấp quyền chặt chẽ thông qua các cảnh báo bảo mật, giới hạn truy cập file ngoài thư mục workspace, và tool `ask_permission`. | Cả hai đều áp dụng cơ chế bảo vệ đường dẫn hệ thống để AI không đọc/ghi nhầm file nhạy cảm ngoài workspace. |
| **15** | **Observability Engineering** | Phát tín hiệu **Server-Sent Events (SSE)** đẩy trực tiếp suy nghĩ (thought), cuộc gọi tool và logs công cụ lên màn hình Timeline thời gian thực trên Web UI. | Ghi vết chi tiết cuộc gọi tool, lịch sử prompt và trace execution của các subagents. | Dự án có thiết kế UI timeline rất trực quan giúp người dùng cuối dễ dàng quan sát luồng tư duy của AI (Highly interactive). |

---

## 🔌 Bản đồ Ánh xạ Kỹ thuật từ ARCHITECTURE.md sang AI Engineering Skills

Dưới đây là bảng ánh xạ chi tiết từng kỹ thuật kiến trúc, tối ưu và mẫu thiết kế được ghi nhận trong tệp [ARCHITECTURE.md](file:///Users/nguyenson/Github/ai-local-support/ARCHITECTURE.md) tương ứng với 15 kỹ năng AI Engineering:

| Kỹ thuật / Thiết kế trong ARCHITECTURE.md | Thuộc Skill AI Engineering | Giải thích cách thức áp dụng thực tế trong Code |
|---|---|---|
| **1. Kiến trúc RAG cục bộ** | **Memory Engineering** & **Context Engineering** | Phân mảnh tài liệu (**Chunking**) và sinh **Embeddings** cục bộ bằng FastEmbed lưu vào **ChromaDB** phục vụ RAG (Retrieval Memory), sau đó trích xuất Top-4 ngữ cảnh chèn vào prompt (Context Engineering). |
| **2. Mô hình Task Queue / Background Worker** | **Automation Engineering** | Đẩy các tác vụ nặng (trích xuất text, OCR, embedding) vào Redis Broker để Celery Workers xử lý ngầm, giữ Flask API phản hồi cực nhanh (<50ms). |
| **3. Kiến trúc Phân rã (Decoupled / Event-Driven)** | **Automation Engineering** | Phân tách Flask (Producer) và Celery (Consumer) thông qua SQLite và Redis, đảm bảo hệ thống tự động hóa bất đồng bộ hoạt động ổn định. |
| **4. Application Factory Pattern** | **Knowledge Engineering** | Sử dụng `create_app()` trong [app_factory.py](file:///Users/nguyenson/Github/ai-local-support/app_factory.py) giúp module hóa dự án, tạo lập Coding Guidelines mạch lạc để Agent AI dễ phân tích cấu trúc. |
| **5. Repository Pattern** | **Memory Engineering** | Các class trong [repositories.py](file:///Users/nguyenson/Github/ai-local-support/services/repositories.py) đóng gói toàn bộ giao tác ghi vào SQLite (Session Memory), giúp tách biệt tầng logic nghiệp vụ với quản lý dữ liệu lưu trữ. |
| **6. Strategy & Factory Pattern** | **Context Engineering** | Sử dụng `ExtractorFactory` để tự động chọn thuật toán trích xuất text sạch theo đuôi file, đóng vai trò chuẩn bị đầu vào chất lượng cao cho ngữ cảnh RAG. |
| **7. Command Pattern** | **Tool Engineering** | Đóng gói các lệnh của Agent thành các class kế thừa `BaseAgentTool` trong [agent_tool_service.py](file:///Users/nguyenson/Github/ai-local-support/services/agent_tool_service.py), quản lý tập trung bằng `ToolRegistry` để Agent dễ gọi. |
| **8. Chống Path Traversal** | **Guardrail Engineering** | Hàm `safe_join_project_path` trong [helper_service.py](file:///Users/nguyenson/Github/ai-local-support/services/helper_service.py) ngăn không cho Agent đọc/ghi tập tin vượt ra ngoài thư mục dự án được cấu hình. |
| **9. Bộ nhớ Cache danh sách Models** | **Memory Engineering** | Sử dụng TTL Cache 60 giây trong [app_factory.py](file:///Users/nguyenson/Github/ai-local-support/app_factory.py) lưu danh sách model Ollama, đóng vai trò tối ưu hóa truy xuất bộ nhớ tạm thời cục bộ. |
| **10. Hệ thống Logging đồng bộ** | **Observability Engineering** | Cấu hình log chuẩn hóa ghi vết toàn bộ hoạt động trong [app_factory.py](file:///Users/nguyenson/Github/ai-local-support/app_factory.py) hỗ trợ debug luồng xử lý của Flask và Celery. |
| **11. Tối ưu hóa DNS Localhost** | **Automation & Tool Engineering** | Sử dụng IP `127.0.0.1` thay vì `localhost` để tránh delay phân giải DNS trên macOS, tăng tốc độ tương tác API giữa Agent và Ollama. |
| **12. Sinh Embeddings theo lô (Batch Processing)** | **Context Engineering** & **Automation** | Sinh embeddings theo lô (32 chunks) giúp tối ưu hóa phần cứng và giảm thời gian tạo chỉ mục ngữ nghĩa cho RAG. |
| **13. Tái sử dụng HTTP Connection Pooling** | **Tool Engineering** | Sử dụng `requests.Session()` dùng chung giúp tối ưu kết nối Keep-Alive khi các Tool của Agent hoặc RAG gọi API Ollama. |
| **14. Giới hạn độ sâu quét Workspace** | **Guardrail Engineering** | Giới hạn `max_depth=2` khi quét cây thư mục ban đầu tránh treo ứng dụng hoặc làm quá tải thông tin cây thư mục nạp vào ngữ cảnh Agent. |
| **15. SQLite WAL Mode** | **Memory Engineering** | Chế độ ghi nhật ký trước WAL (Write-Ahead Logging) cho phép luồng chính Flask và luồng ngầm Celery ghi dữ liệu song song vào SQLite (Session Memory) mà không bị xung đột khóa. |

---

## Sự khác biệt chính (Key Differences)

1. **Khung làm việc Agent (Agent Framework)**:
   * *Bảng của bạn*: Đề cập đến LangGraph, CrewAI, OpenAI SDK Workflows, MCP.
   * *Dự án hiện tại*: Không sử dụng bất kỳ framework Agent nào ở trên. Thay vào đó, nó tự xây dựng một công cụ **ReAct Loop thuần bằng Python** sử dụng regex để parse thẻ. Điều này giúp hệ thống nhẹ, dễ tích hợp với Ollama cục bộ nhưng hạn chế khả năng cấu hình các Agent phức tạp.
2. **Cơ chế gọi công cụ (Tool Calling)**:
   * *Bảng của bạn*: Đề cập đến Native Function/Tool Calling của các API lớn.
   * *Dự án hiện tại*: Do chạy các model Ollama cục bộ (vốn có thể không hỗ trợ tốt hoặc không ổn định với Native Tool Calling), dự án dùng cách thức **định dạng prompt đặc biệt** và parse text thô.
3. **Multi-agent & Kế hoạch (Task Decomposition)**:
   * Dự án hiện tại chạy ở mức độ Single-Agent đơn giản, chưa có cơ chế chia nhỏ nhiệm vụ dạng Workflow, State Machine, hay Planner Agent riêng biệt giống như cách tôi hoặc các framework nâng cao thực hiện.

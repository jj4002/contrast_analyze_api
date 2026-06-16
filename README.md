# ContractLens - Hệ thống AI rà soát hợp đồng tiếng Việt

## Yêu cầu
- Python 3.10+
- GROQ API Key (miễn phí tại console.groq.com)

## Cài đặt & Chạy

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # Thêm GROQ_API_KEY của bạn
uvicorn app.main:app --reload --port 8000
```

Mở trình duyệt tại `http://localhost:8000`

## API Endpoints
- `POST /api/v1/upload` - Tải lên hợp đồng (.doc, .docx, .pdf)
- `POST /api/v1/analyze` - Phân tích rủi ro pháp lý
- `POST /api/v1/chat` - Hỏi đáp về hợp đồng
- `GET /health` - Kiểm tra trạng thái

## Công nghệ
- **FastAPI** - Backend framework
- **Groq Llama 3.1 8B** - AI phân tích hợp đồng
- **ChromaDB + Vietnamese-SBERT** - RAG và tìm kiếm ngữ nghĩa
- **SQLite** - Lưu trữ dữ liệu

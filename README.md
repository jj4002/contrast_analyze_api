# ContractLens - Hệ thống AI rà soát hợp đồng tiếng Việt

## Yêu cầu
- Python 3.10+
- GROQ API Key (miễn phí tại console.groq.com)

## Cài đặt & Chạy

```bash
pip install -r requirements.txt
cp .env.example .env  # Thêm GROQ_API_KEY, DATABASE_URL, SUPABASE_URL, SUPABASE_SECRET_KEY của bạn
uvicorn main:app --reload --port 8000
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
- **FAISS + Vietnamese-SBERT** - RAG và tìm kiếm ngữ nghĩa
- **PostgreSQL (Supabase)** - Lưu trữ dữ liệu
- **Supabase Auth** - Xác thực người dùng

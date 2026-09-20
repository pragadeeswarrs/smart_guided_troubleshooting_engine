# PRISM Backend (Member 1 foundation)

```bash
cd prism_backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- Swagger docs: http://127.0.0.1:8000/docs
- UI: open `ui/index.html` directly, or http://127.0.0.1:8000/ui/
- Demo reset: `curl -X DELETE http://127.0.0.1:8000/v1/cache`

| File | Owner |
|---|---|
| `app/services/llm_service.py` | Member 2 |
| `app/services/search_service.py`, `app/cache_manager.py` (semantic upgrade) | Member 3 |
| `app/services/validation.py` | Member 4 |

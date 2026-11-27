# FastAPI service

The API owns business rules, authorization, validation, resource lifecycle, upload orchestration, and result publication.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload
```

Health endpoint: `GET /api/v1/health`. Domain routes and persistence are not implemented in this foundation commit.

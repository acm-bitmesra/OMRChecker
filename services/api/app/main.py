from fastapi import FastAPI

app = FastAPI(
    title="OMR Checker API",
    version="0.1.0",
    description="API for creating, scanning, reviewing, and evaluating OMR sheets.",
)


@app.get("/api/v1/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness endpoint; infrastructure readiness checks are added with integrations."""
    return {"status": "ok", "service": "omr-checker-api"}

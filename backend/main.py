from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, monitoring

app = FastAPI(
    title="AI Database Assistant",
    description="Agentic system with 6-layer guardrails for education database queries",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(monitoring.router, prefix="/api/v1", tags=["Monitoring"])


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "AI Database Assistant"}

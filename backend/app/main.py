from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers.auth import router as auth_router
from .routers.feedback import router as feedback_router
from .routers.interviews import router as interviews_router
from .routers.voice import router as voice_router

app = FastAPI(
    title="Mockwright API",
    description="Voice-first behavioral interview practice.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(interviews_router)
app.include_router(feedback_router)
app.include_router(voice_router)


@app.get("/health", tags=["health"])
def health_status():
    return {"status": "ok"}

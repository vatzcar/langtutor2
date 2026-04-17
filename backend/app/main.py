from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.admin.languages import router as admin_languages_router
from app.api.admin.personas import router as admin_personas_router
from app.api.admin.plans import router as admin_plans_router
from app.api.admin.users import router as admin_users_router
from app.api.admin.reports import router as admin_reports_router
from app.api.admin.logs import router as admin_logs_router
from app.api.admin.admin_users import router as admin_admin_users_router
from app.api.admin.roles import router as admin_roles_router
from app.api.admin.subscriptions import router as admin_subscriptions_router
from app.api.mobile.languages import router as mobile_languages_router
from app.api.mobile.users import router as mobile_users_router
from app.api.mobile.sessions import router as mobile_sessions_router
from app.api.mobile.chat import router as mobile_chat_router
from app.api.mobile.subscriptions import router as mobile_subscriptions_router
from app.api.mobile.plans import router as mobile_plans_router
from app.api.mobile.support import router as mobile_support_router
from app.api.internal import router as internal_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


app = FastAPI(title="LangTutor API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth
app.include_router(auth_router, prefix="/api/v1")

# Admin
app.include_router(admin_languages_router, prefix="/api/v1")
app.include_router(admin_personas_router, prefix="/api/v1")
app.include_router(admin_plans_router, prefix="/api/v1")
app.include_router(admin_users_router, prefix="/api/v1")
app.include_router(admin_reports_router, prefix="/api/v1")
app.include_router(admin_logs_router, prefix="/api/v1")
app.include_router(admin_admin_users_router, prefix="/api/v1")
app.include_router(admin_roles_router, prefix="/api/v1")
app.include_router(admin_subscriptions_router, prefix="/api/v1")

# Mobile
app.include_router(mobile_languages_router, prefix="/api/v1")
app.include_router(mobile_users_router, prefix="/api/v1")
app.include_router(mobile_sessions_router, prefix="/api/v1")
app.include_router(mobile_chat_router, prefix="/api/v1")
app.include_router(mobile_subscriptions_router, prefix="/api/v1")
app.include_router(mobile_plans_router, prefix="/api/v1")
app.include_router(mobile_support_router, prefix="/api/v1")

# Internal (agent-to-backend)
app.include_router(internal_router, prefix="/api/v1")


# Serve uploaded assets (language icons, persona images, etc.)
_uploads_dir = Path("uploads")
_uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")


@app.get("/health")
async def health_check():
    return {"status": "ok"}

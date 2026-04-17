# Plan 1: Backend Core Implementation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the FastAPI backend with database models, authentication, admin CRUD APIs, and user-facing APIs.

**Architecture:** Three-layer architecture — API routes → Service layer → SQLAlchemy ORM. JWT-based auth with social login (Google/Apple). Role-based ACL for admin. PostgreSQL with Alembic migrations.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL, python-jose (JWT), httpx (social login verification), Pydantic v2, pytest + httpx (testing)

---

### Task 1: Project Scaffolding & Configuration

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`

- [ ] **Step 1: Create pyproject.toml with all dependencies**

```toml
[project]
name = "langtutor-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy[asyncio]>=2.0.30",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "httpx>=0.27.0",
    "python-multipart>=0.0.9",
    "pillow>=10.3.0",
    "aiofiles>=23.2.0",
    "geoip2>=4.8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
    "factory-boy>=3.3.0",
    "aiosqlite>=0.20.0",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"
```

- [ ] **Step 2: Create config.py with environment settings**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://langtutor:langtutor@localhost:5432/langtutor"
    test_database_url: str = "sqlite+aiosqlite:///./test.db"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    google_client_id: str = ""
    apple_client_id: str = ""
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 10

    model_config = {"env_file": ".env", "env_prefix": "LANGTUTOR_"}

settings = Settings()
```

- [ ] **Step 3: Create database.py with async engine and session**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 4: Create main.py FastAPI app entry point**

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="LangTutor API", version="0.1.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Create empty __init__.py files**

```bash
mkdir -p backend/app/models backend/app/schemas backend/app/api/admin backend/app/api/mobile backend/app/services backend/app/utils backend/tests
touch backend/app/__init__.py backend/app/models/__init__.py backend/app/schemas/__init__.py
touch backend/app/api/__init__.py backend/app/api/admin/__init__.py backend/app/api/mobile/__init__.py
touch backend/app/services/__init__.py backend/app/utils/__init__.py backend/tests/__init__.py
```

- [ ] **Step 6: Verify the app starts**

```bash
cd backend && pip install -e ".[dev]" && uvicorn app.main:app --port 8000 &
sleep 3 && curl http://localhost:8000/health
# Expected: {"status":"ok"}
kill %1
```

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: scaffold FastAPI backend with config and database setup"
```

---

### Task 2: SQLAlchemy Models — Users & Auth

**Files:**
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/admin.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write test for User model creation**

```python
# backend/tests/test_models.py
import pytest
from sqlalchemy import select
from app.models.user import User

@pytest.mark.asyncio
async def test_create_user(db_session):
    user = User(
        email="test@example.com",
        name="Test User",
        auth_provider="google",
        auth_provider_id="google-123",
    )
    db_session.add(user)
    await db_session.flush()
    result = await db_session.execute(select(User).where(User.email == "test@example.com"))
    fetched = result.scalar_one()
    assert fetched.name == "Test User"
    assert fetched.is_active is True
    assert fetched.is_banned is False
    assert fetched.deleted_at is None
```

- [ ] **Step 2: Write test conftest with async DB session**

```python
# backend/tests/conftest.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database import Base

TEST_DB_URL = "sqlite+aiosqlite:///./test.db"

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend && pytest tests/test_models.py -v
# Expected: FAIL — User not defined
```

- [ ] **Step 4: Implement User model**

```python
# backend/app/models/user.py
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Date, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum

class AuthProvider(str, enum.Enum):
    google = "google"
    apple = "apple"

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    date_of_birth: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    avatar_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("user_avatars.id"), nullable=True)
    native_language_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("languages.id"), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(20))
    auth_provider_id: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 5: Implement AdminUser and AdminRole models**

```python
# backend/app/models/admin.py
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class AdminRole(Base):
    __tablename__ = "admin_roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    permissions: Mapped[dict] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("admin_roles.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    role: Mapped["AdminRole"] = relationship(lazy="joined")
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_models.py -v
# Expected: PASS
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/ backend/tests/
git commit -m "feat: add User, AdminUser, AdminRole SQLAlchemy models"
```

---

### Task 3: SQLAlchemy Models — Language, Persona, Plan

**Files:**
- Create: `backend/app/models/language.py`
- Create: `backend/app/models/persona.py`
- Create: `backend/app/models/plan.py`

- [ ] **Step 1: Write tests for Language, Persona, Plan models**

```python
# append to backend/tests/test_models.py
from app.models.language import Language
from app.models.persona import Persona
from app.models.plan import Plan

@pytest.mark.asyncio
async def test_create_language(db_session):
    lang = Language(name="Spanish", locale="es-ES", is_default=True, is_fallback=False)
    db_session.add(lang)
    await db_session.flush()
    result = await db_session.execute(select(Language).where(Language.locale == "es-ES"))
    fetched = result.scalar_one()
    assert fetched.name == "Spanish"
    assert fetched.is_default is True

@pytest.mark.asyncio
async def test_create_persona(db_session):
    lang = Language(name="English", locale="en-GB", is_default=True, is_fallback=True)
    db_session.add(lang)
    await db_session.flush()
    persona = Persona(name="Sarah", language_id=lang.id, gender="female", type="coordinator")
    db_session.add(persona)
    await db_session.flush()
    assert persona.id is not None

@pytest.mark.asyncio
async def test_create_plan(db_session):
    plan = Plan(name="Free", slug="free", price_monthly=0, price_yearly=0,
                voice_call_limit_minutes=30, text_learning_limit_minutes=60,
                video_call_limit_minutes=0)
    db_session.add(plan)
    await db_session.flush()
    assert plan.slug == "free"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_models.py -v -k "language or persona or plan"
# Expected: FAIL
```

- [ ] **Step 3: Implement Language model**

```python
# backend/app/models/language.py
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Language(Base):
    __tablename__ = "languages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    locale: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 4: Implement Persona model**

```python
# backend/app/models/persona.py
import uuid
from datetime import datetime
import enum
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"

class PersonaType(str, enum.Enum):
    teacher = "teacher"
    coordinator = "coordinator"
    peer = "peer"

class TeachingStyle(str, enum.Enum):
    casual_friendly = "casual_friendly"
    friendly_structured = "friendly_structured"
    formal_structured = "formal_structured"

class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    language_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("languages.id"))
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gender: Mapped[str] = mapped_column(String(20))
    type: Mapped[str] = mapped_column(String(20))
    teaching_style: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    language: Mapped["Language"] = relationship(lazy="joined")
```

- [ ] **Step 5: Implement Plan model**

```python
# backend/app/models/plan.py
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50))
    slug: Mapped[str] = mapped_column(String(50), unique=True)
    price_monthly: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    price_yearly: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    text_learning_limit_minutes: Mapped[int] = mapped_column(Integer, default=0)
    voice_call_limit_minutes: Mapped[int] = mapped_column(Integer, default=0)
    video_call_limit_minutes: Mapped[int] = mapped_column(Integer, default=0)
    agentic_voice_limit_monthly: Mapped[int] = mapped_column(Integer, default=0)
    coordinator_video_limit_monthly: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_models.py -v
# Expected: ALL PASS
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/ backend/tests/
git commit -m "feat: add Language, Persona, Plan SQLAlchemy models"
```

---

### Task 4: SQLAlchemy Models — Subscription, Session, Usage, Audit

**Files:**
- Create: `backend/app/models/subscription.py`
- Create: `backend/app/models/session.py`
- Create: `backend/app/models/usage.py`
- Create: `backend/app/models/audit.py`

- [ ] **Step 1: Write tests for remaining models**

```python
# append to backend/tests/test_models.py
from app.models.subscription import UserSubscription
from app.models.session import Session, SessionTranscript, ChatMessage
from app.models.usage import DailyUsage, MonthlyUsage
from app.models.audit import AuditLog

@pytest.mark.asyncio
async def test_create_subscription(db_session):
    # Setup user and plan first
    from app.models.user import User
    user = User(email="sub@test.com", name="Sub User", auth_provider="google", auth_provider_id="g-sub")
    plan = Plan(name="Pro", slug="pro-test", price_monthly=4.99)
    db_session.add_all([user, plan])
    await db_session.flush()
    sub = UserSubscription(user_id=user.id, plan_id=plan.id, billing_cycle="monthly")
    db_session.add(sub)
    await db_session.flush()
    assert sub.is_active is True

@pytest.mark.asyncio
async def test_create_audit_log(db_session):
    log = AuditLog(actor_type="admin", actor_id=uuid.uuid4(), action="create_language",
                   resource_type="language", details={"name": "French"})
    db_session.add(log)
    await db_session.flush()
    assert log.action == "create_language"
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement UserSubscription model**

```python
# backend/app/models/subscription.py
import uuid
from datetime import datetime
import enum
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class BillingCycle(str, enum.Enum):
    monthly = "monthly"
    yearly = "yearly"

class StoreType(str, enum.Enum):
    apple = "apple"
    google = "google"

class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plans.id"))
    billing_cycle: Mapped[str] = mapped_column(String(20), default="monthly")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    store_transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    store_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    plan: Mapped["Plan"] = relationship(lazy="joined")
```

- [ ] **Step 4: Implement Session, SessionTranscript, ChatMessage models**

```python
# backend/app/models/session.py
import uuid
from datetime import datetime
import enum
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class SessionType(str, enum.Enum):
    voice_call = "voice_call"
    video_call = "video_call"
    text_chat = "text_chat"

class SessionMode(str, enum.Enum):
    learning = "learning"
    practice = "practice"
    support = "support"
    onboarding = "onboarding"

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    user_language_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("user_languages.id"), nullable=True)
    persona_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("personas.id"))
    session_type: Mapped[str] = mapped_column(String(20))
    session_mode: Mapped[str] = mapped_column(String(20))
    livekit_room_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    cefr_level_at_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    topics_covered: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    performance_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    skills_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    vocabulary_tracked: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class SessionTranscript(Base):
    __tablename__ = "session_transcripts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"))
    speaker: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    timestamp_offset_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"))
    sender: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
```

- [ ] **Step 5: Implement Usage and Audit models**

```python
# backend/app/models/usage.py
import uuid
from datetime import datetime, date
from sqlalchemy import DateTime, Date, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class DailyUsage(Base):
    __tablename__ = "daily_usage"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    voice_call_minutes: Mapped[float] = mapped_column(Float, default=0)
    video_call_minutes: Mapped[float] = mapped_column(Float, default=0)
    text_learning_minutes: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class MonthlyUsage(Base):
    __tablename__ = "monthly_usage"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    month: Mapped[date] = mapped_column(Date, index=True)
    agentic_voice_calls: Mapped[int] = mapped_column(Integer, default=0)
    coordinator_video_calls: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
```

```python
# backend/app/models/audit.py
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    actor_type: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[uuid.UUID] = mapped_column()
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
```

- [ ] **Step 6: Implement UserLanguage and CefrLevelHistory models**

```python
# add to backend/app/models/user.py (append after User class)

class UserAvatar(Base):
    __tablename__ = "user_avatars"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    image_url: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class UserLanguage(Base):
    __tablename__ = "user_languages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    language_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("languages.id"))
    teacher_persona_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("personas.id"), nullable=True)
    teaching_style: Mapped[str | None] = mapped_column(String(30), nullable=True)
    current_cefr_level: Mapped[str] = mapped_column(String(5), default="A0")
    cefr_progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class CefrLevelHistory(Base):
    __tablename__ = "cefr_level_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_language_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_languages.id"), index=True)
    cefr_level: Mapped[str] = mapped_column(String(5))
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    topics_covered: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    lessons_count: Mapped[int] = mapped_column(Integer, default=0)
    hours_spent: Mapped[float] = mapped_column(Float, default=0)
    practice_sessions: Mapped[int] = mapped_column(Integer, default=0)
    practice_hours: Mapped[float] = mapped_column(Float, default=0)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    progress_percent: Mapped[float] = mapped_column(Float, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    passed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class UserBan(Base):
    __tablename__ = "user_bans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    banned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unbanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
```

- [ ] **Step 7: Update models/__init__.py to import all models**

```python
# backend/app/models/__init__.py
from app.models.user import User, UserAvatar, UserLanguage, CefrLevelHistory, UserBan
from app.models.admin import AdminUser, AdminRole
from app.models.language import Language
from app.models.persona import Persona
from app.models.plan import Plan
from app.models.subscription import UserSubscription
from app.models.session import Session, SessionTranscript, ChatMessage
from app.models.usage import DailyUsage, MonthlyUsage
from app.models.audit import AuditLog

__all__ = [
    "User", "UserAvatar", "UserLanguage", "CefrLevelHistory", "UserBan",
    "AdminUser", "AdminRole",
    "Language", "Persona", "Plan",
    "UserSubscription",
    "Session", "SessionTranscript", "ChatMessage",
    "DailyUsage", "MonthlyUsage",
    "AuditLog",
]
```

- [ ] **Step 8: Run all model tests**

```bash
cd backend && pytest tests/test_models.py -v
# Expected: ALL PASS
```

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/ backend/tests/
git commit -m "feat: add all remaining SQLAlchemy models (subscription, session, usage, audit)"
```

---

### Task 5: Alembic Migration Setup

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`

- [ ] **Step 1: Initialize Alembic**

```bash
cd backend && alembic init alembic
```

- [ ] **Step 2: Configure alembic env.py for async**

```python
# backend/alembic/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from app.config import settings
from app.database import Base
from app.models import *  # noqa: import all models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    url = settings.database_url
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    connectable = create_async_engine(settings.database_url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: Generate initial migration**

```bash
cd backend && alembic revision --autogenerate -m "initial schema"
```

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/ backend/alembic.ini
git commit -m "feat: setup Alembic migrations with initial schema"
```

---

### Task 6: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/schemas/user.py`
- Create: `backend/app/schemas/admin.py`
- Create: `backend/app/schemas/language.py`
- Create: `backend/app/schemas/persona.py`
- Create: `backend/app/schemas/plan.py`
- Create: `backend/app/schemas/subscription.py`
- Create: `backend/app/schemas/session.py`

- [ ] **Step 1: Create auth schemas**

```python
# backend/app/schemas/auth.py
from pydantic import BaseModel

class SocialLoginRequest(BaseModel):
    provider: str  # "google" or "apple"
    id_token: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str

class AdminLoginRequest(BaseModel):
    email: str
    password: str
```

- [ ] **Step 2: Create user schemas**

```python
# backend/app/schemas/user.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime, date

class UserBase(BaseModel):
    name: str
    email: str

class UserCreate(BaseModel):
    email: str
    name: str
    auth_provider: str
    auth_provider_id: str

class UserUpdate(BaseModel):
    name: str | None = None
    date_of_birth: date | None = None
    native_language_id: UUID | None = None
    avatar_id: UUID | None = None

class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    date_of_birth: date | None
    avatar_id: UUID | None
    native_language_id: UUID | None
    is_active: bool
    is_banned: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class UserLanguageResponse(BaseModel):
    id: UUID
    language_id: UUID
    teacher_persona_id: UUID | None
    teaching_style: str | None
    current_cefr_level: str
    cefr_progress_percent: float
    is_active: bool

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Create admin schemas**

```python
# backend/app/schemas/admin.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class AdminRoleCreate(BaseModel):
    name: str
    permissions: list[str]

class AdminRoleResponse(BaseModel):
    id: UUID
    name: str
    permissions: list[str]
    created_at: datetime
    model_config = {"from_attributes": True}

class AdminUserCreate(BaseModel):
    email: str
    name: str
    password: str
    role_id: UUID

class AdminUserUpdate(BaseModel):
    name: str | None = None
    role_id: UUID | None = None
    is_active: bool | None = None

class AdminUserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    role_id: UUID
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Create language, persona, plan schemas**

```python
# backend/app/schemas/language.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class LanguageCreate(BaseModel):
    name: str
    locale: str
    is_default: bool = False
    is_fallback: bool = False

class LanguageUpdate(BaseModel):
    name: str | None = None
    locale: str | None = None
    is_default: bool | None = None
    is_fallback: bool | None = None
    is_active: bool | None = None

class LanguageResponse(BaseModel):
    id: UUID
    name: str
    locale: str
    icon_url: str | None
    is_default: bool
    is_fallback: bool
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}
```

```python
# backend/app/schemas/persona.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class PersonaCreate(BaseModel):
    name: str
    language_id: UUID
    gender: str
    type: str
    teaching_style: str | None = None

class PersonaUpdate(BaseModel):
    name: str | None = None
    gender: str | None = None
    type: str | None = None
    teaching_style: str | None = None
    is_active: bool | None = None

class PersonaResponse(BaseModel):
    id: UUID
    name: str
    language_id: UUID
    image_url: str | None
    gender: str
    type: str
    teaching_style: str | None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}
```

```python
# backend/app/schemas/plan.py
from pydantic import BaseModel
from uuid import UUID

class PlanUpdate(BaseModel):
    price_monthly: float | None = None
    price_yearly: float | None = None
    text_learning_limit_minutes: int | None = None
    voice_call_limit_minutes: int | None = None
    video_call_limit_minutes: int | None = None
    agentic_voice_limit_monthly: int | None = None
    coordinator_video_limit_monthly: int | None = None

class PlanResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    price_monthly: float
    price_yearly: float
    text_learning_limit_minutes: int
    voice_call_limit_minutes: int
    video_call_limit_minutes: int
    agentic_voice_limit_monthly: int
    coordinator_video_limit_monthly: int
    is_active: bool
    model_config = {"from_attributes": True}
```

```python
# backend/app/schemas/subscription.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class SubscriptionCreate(BaseModel):
    plan_id: UUID
    billing_cycle: str = "monthly"
    store_transaction_id: str | None = None
    store_type: str | None = None

class SubscriptionResponse(BaseModel):
    id: UUID
    user_id: UUID
    plan_id: UUID
    billing_cycle: str
    started_at: datetime
    expires_at: datetime | None
    is_active: bool
    model_config = {"from_attributes": True}
```

```python
# backend/app/schemas/session.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class SessionResponse(BaseModel):
    id: UUID
    session_type: str
    session_mode: str
    duration_seconds: int
    cefr_level_at_time: str | None
    started_at: datetime
    ended_at: datetime | None
    model_config = {"from_attributes": True}

class TranscriptResponse(BaseModel):
    id: UUID
    speaker: str
    content: str
    timestamp_offset_ms: int
    created_at: datetime
    model_config = {"from_attributes": True}

class ChatMessageCreate(BaseModel):
    content: str

class ChatMessageResponse(BaseModel):
    id: UUID
    sender: str
    content: str
    is_read: bool
    created_at: datetime
    model_config = {"from_attributes": True}
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat: add all Pydantic request/response schemas"
```

---

### Task 7: Auth & Security Utilities

**Files:**
- Create: `backend/app/utils/security.py`
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write auth test**

```python
# backend/tests/test_auth.py
import pytest
from app.utils.security import create_access_token, verify_token, hash_password, verify_password

def test_create_and_verify_token():
    token = create_access_token({"sub": "user-123", "type": "user"})
    payload = verify_token(token)
    assert payload["sub"] == "user-123"

def test_password_hashing():
    hashed = hash_password("mysecret")
    assert verify_password("mysecret", hashed) is True
    assert verify_password("wrongpass", hashed) is False
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Implement security utilities**

```python
# backend/app/utils/security.py
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

def verify_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
```

- [ ] **Step 4: Implement API dependencies (current user extraction)**

```python
# backend/app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.utils.security import verify_token
from app.models.user import User
from app.models.admin import AdminUser

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = verify_token(credentials.credentials)
    if not payload or payload.get("type") != "user":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    if user.is_banned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is banned")
    return user

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    payload = verify_token(credentials.credentials)
    if not payload or payload.get("type") != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(AdminUser).where(AdminUser.id == payload["sub"]))
    admin = result.scalar_one_or_none()
    if not admin or not admin.is_active or admin.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found or inactive")
    return admin

def require_permission(permission: str):
    async def check(admin: AdminUser = Depends(get_current_admin)):
        if permission not in (admin.role.permissions or []):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {permission}")
        return admin
    return check
```

- [ ] **Step 5: Implement auth service (social login verification)**

```python
# backend/app/services/auth_service.py
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.admin import AdminUser
from app.utils.security import create_access_token, hash_password, verify_password
from app.config import settings

async def verify_google_token(id_token: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}")
        if resp.status_code == 200:
            data = resp.json()
            if data.get("aud") == settings.google_client_id:
                return {"email": data["email"], "name": data.get("name", ""), "sub": data["sub"]}
    return None

async def verify_apple_token(id_token: str) -> dict | None:
    # Apple token verification via JWKS
    # Simplified: decode and validate the JWT from Apple
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://appleid.apple.com/auth/keys")
        if resp.status_code == 200:
            # In production, validate JWT signature against Apple's JWKS
            from jose import jwt as jose_jwt
            header = jose_jwt.get_unverified_header(id_token)
            claims = jose_jwt.get_unverified_claims(id_token)
            return {"email": claims.get("email", ""), "name": "", "sub": claims["sub"]}
    return None

async def social_login(db: AsyncSession, provider: str, id_token: str) -> tuple[User, str]:
    if provider == "google":
        info = await verify_google_token(id_token)
    elif provider == "apple":
        info = await verify_apple_token(id_token)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    if not info:
        raise ValueError("Invalid token")

    result = await db.execute(
        select(User).where(User.auth_provider == provider, User.auth_provider_id == info["sub"])
    )
    user = result.scalar_one_or_none()

    is_new = False
    if not user:
        user = User(
            email=info["email"],
            name=info["name"],
            auth_provider=provider,
            auth_provider_id=info["sub"],
        )
        db.add(user)
        await db.flush()
        is_new = True

    token = create_access_token({"sub": str(user.id), "type": "user"})
    return user, token, is_new

async def admin_login(db: AsyncSession, email: str, password: str) -> tuple[AdminUser, str]:
    result = await db.execute(select(AdminUser).where(AdminUser.email == email))
    admin = result.scalar_one_or_none()
    if not admin or not verify_password(password, admin.password_hash):
        raise ValueError("Invalid credentials")
    if not admin.is_active or admin.deleted_at is not None:
        raise ValueError("Account disabled")
    token = create_access_token({"sub": str(admin.id), "type": "admin"})
    return admin, token
```

- [ ] **Step 6: Create auth API routes**

```python
# backend/app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.auth import SocialLoginRequest, AdminLoginRequest, TokenResponse
from app.services.auth_service import social_login, admin_login

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/social-login", response_model=TokenResponse)
async def social_login_endpoint(req: SocialLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        user, token, is_new = await social_login(db, req.provider, req.id_token)
        return TokenResponse(access_token=token, user_id=str(user.id))
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/admin/login", response_model=TokenResponse)
async def admin_login_endpoint(req: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        admin, token = await admin_login(db, req.email, req.password)
        return TokenResponse(access_token=token, user_id=str(admin.id))
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
```

- [ ] **Step 7: Run tests, verify pass, commit**

```bash
cd backend && pytest tests/test_auth.py -v
git add backend/app/utils/ backend/app/services/ backend/app/api/ backend/tests/
git commit -m "feat: add auth system with JWT, social login, ACL dependencies"
```

---

### Task 8: Admin API — Language CRUD

**Files:**
- Create: `backend/app/services/language_service.py`
- Create: `backend/app/api/admin/languages.py`
- Create: `backend/tests/test_admin/test_languages.py`

- [ ] **Step 1: Write test for language CRUD**

```python
# backend/tests/test_admin/test_languages.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_language(admin_client: AsyncClient):
    resp = await admin_client.post("/api/admin/languages", json={
        "name": "Spanish", "locale": "es-ES", "is_default": True
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["locale"] == "es-ES"
    assert data["is_default"] is True

@pytest.mark.asyncio
async def test_list_languages(admin_client: AsyncClient):
    await admin_client.post("/api/admin/languages", json={"name": "French", "locale": "fr-FR"})
    resp = await admin_client.get("/api/admin/languages")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

@pytest.mark.asyncio
async def test_fallback_language_unique(admin_client: AsyncClient):
    await admin_client.post("/api/admin/languages", json={
        "name": "English", "locale": "en-GB", "is_fallback": True
    })
    await admin_client.post("/api/admin/languages", json={
        "name": "English US", "locale": "en-US", "is_fallback": True
    })
    resp = await admin_client.get("/api/admin/languages")
    langs = resp.json()
    fallbacks = [l for l in langs if l["is_fallback"]]
    assert len(fallbacks) == 1  # Only latest should be fallback
```

- [ ] **Step 2: Implement language service**

```python
# backend/app/services/language_service.py
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.language import Language
from app.schemas.language import LanguageCreate, LanguageUpdate

async def create_language(db: AsyncSession, data: LanguageCreate) -> Language:
    if data.is_fallback:
        await db.execute(update(Language).values(is_fallback=False))
    lang = Language(**data.model_dump())
    db.add(lang)
    await db.flush()
    return lang

async def get_languages(db: AsyncSession, include_inactive: bool = False) -> list[Language]:
    query = select(Language).where(Language.deleted_at.is_(None))
    if not include_inactive:
        query = query.where(Language.is_active.is_(True))
    result = await db.execute(query.order_by(Language.name))
    return list(result.scalars().all())

async def get_language(db: AsyncSession, language_id: UUID) -> Language | None:
    result = await db.execute(select(Language).where(Language.id == language_id))
    return result.scalar_one_or_none()

async def update_language(db: AsyncSession, language_id: UUID, data: LanguageUpdate) -> Language | None:
    lang = await get_language(db, language_id)
    if not lang:
        return None
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("is_fallback"):
        await db.execute(update(Language).where(Language.id != language_id).values(is_fallback=False))
    for key, value in update_data.items():
        setattr(lang, key, value)
    await db.flush()
    return lang

async def delete_language(db: AsyncSession, language_id: UUID) -> bool:
    lang = await get_language(db, language_id)
    if not lang:
        return False
    from datetime import datetime, timezone
    lang.deleted_at = datetime.now(timezone.utc)
    lang.is_active = False
    await db.flush()
    return True
```

- [ ] **Step 3: Implement language admin routes**

```python
# backend/app/api/admin/languages.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.api.deps import require_permission
from app.schemas.language import LanguageCreate, LanguageUpdate, LanguageResponse
from app.services import language_service

router = APIRouter(prefix="/admin/languages", tags=["admin-languages"])

@router.post("", response_model=LanguageResponse, status_code=201)
async def create(data: LanguageCreate, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_languages"))):
    lang = await language_service.create_language(db, data)
    return lang

@router.get("", response_model=list[LanguageResponse])
async def list_all(db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_languages"))):
    return await language_service.get_languages(db, include_inactive=True)

@router.get("/{language_id}", response_model=LanguageResponse)
async def get_one(language_id: UUID, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_languages"))):
    lang = await language_service.get_language(db, language_id)
    if not lang:
        raise HTTPException(status_code=404, detail="Language not found")
    return lang

@router.patch("/{language_id}", response_model=LanguageResponse)
async def update_one(language_id: UUID, data: LanguageUpdate, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_languages"))):
    lang = await language_service.update_language(db, language_id, data)
    if not lang:
        raise HTTPException(status_code=404, detail="Language not found")
    return lang

@router.delete("/{language_id}", status_code=204)
async def delete_one(language_id: UUID, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_languages"))):
    if not await language_service.delete_language(db, language_id):
        raise HTTPException(status_code=404, detail="Language not found")

@router.post("/{language_id}/icon", response_model=LanguageResponse)
async def upload_icon(language_id: UUID, file: UploadFile = File(...), db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_languages"))):
    lang = await language_service.get_language(db, language_id)
    if not lang:
        raise HTTPException(status_code=404, detail="Language not found")
    import aiofiles, os
    from app.config import settings
    os.makedirs(f"{settings.upload_dir}/languages", exist_ok=True)
    path = f"{settings.upload_dir}/languages/{language_id}{os.path.splitext(file.filename)[1]}"
    async with aiofiles.open(path, "wb") as f:
        await f.write(await file.read())
    lang.icon_url = path
    await db.flush()
    return lang
```

- [ ] **Step 4: Run tests, commit**

```bash
cd backend && pytest tests/test_admin/ -v
git add backend/app/services/ backend/app/api/admin/ backend/tests/
git commit -m "feat: add admin language CRUD API with fallback constraint"
```

---

### Task 9: Admin API — Persona CRUD

**Files:**
- Create: `backend/app/services/persona_service.py`
- Create: `backend/app/api/admin/personas.py`
- Create: `backend/tests/test_admin/test_personas.py`

- [ ] **Step 1: Write persona tests**

```python
# backend/tests/test_admin/test_personas.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_persona(admin_client: AsyncClient, language_id):
    resp = await admin_client.post("/api/admin/personas", json={
        "name": "Maria", "language_id": str(language_id),
        "gender": "female", "type": "coordinator"
    })
    assert resp.status_code == 201

@pytest.mark.asyncio
async def test_only_one_coordinator_per_language(admin_client: AsyncClient, language_id):
    await admin_client.post("/api/admin/personas", json={
        "name": "Ana", "language_id": str(language_id),
        "gender": "female", "type": "coordinator"
    })
    resp = await admin_client.post("/api/admin/personas", json={
        "name": "Laura", "language_id": str(language_id),
        "gender": "female", "type": "coordinator"
    })
    assert resp.status_code == 409  # Conflict
```

- [ ] **Step 2: Implement persona service with coordinator constraint**

```python
# backend/app/services/persona_service.py
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.persona import Persona
from app.schemas.persona import PersonaCreate, PersonaUpdate

async def create_persona(db: AsyncSession, data: PersonaCreate) -> Persona:
    if data.type == "coordinator":
        existing = await db.execute(
            select(Persona).where(
                Persona.language_id == data.language_id,
                Persona.type == "coordinator",
                Persona.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Only one coordinator per language is allowed")
    persona = Persona(**data.model_dump())
    db.add(persona)
    await db.flush()
    return persona

async def get_personas(db: AsyncSession, language_id: UUID | None = None) -> list[Persona]:
    query = select(Persona).where(Persona.deleted_at.is_(None))
    if language_id:
        query = query.where(Persona.language_id == language_id)
    result = await db.execute(query.order_by(Persona.name))
    return list(result.scalars().all())

async def get_persona(db: AsyncSession, persona_id: UUID) -> Persona | None:
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    return result.scalar_one_or_none()

async def update_persona(db: AsyncSession, persona_id: UUID, data: PersonaUpdate) -> Persona | None:
    persona = await get_persona(db, persona_id)
    if not persona:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(persona, key, value)
    await db.flush()
    return persona

async def delete_persona(db: AsyncSession, persona_id: UUID) -> bool:
    persona = await get_persona(db, persona_id)
    if not persona:
        return False
    from datetime import datetime, timezone
    persona.deleted_at = datetime.now(timezone.utc)
    persona.is_active = False
    await db.flush()
    return True
```

- [ ] **Step 3: Implement persona admin routes**

```python
# backend/app/api/admin/personas.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.api.deps import require_permission
from app.schemas.persona import PersonaCreate, PersonaUpdate, PersonaResponse
from app.services import persona_service

router = APIRouter(prefix="/admin/personas", tags=["admin-personas"])

@router.post("", response_model=PersonaResponse, status_code=201)
async def create(data: PersonaCreate, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_personas"))):
    try:
        return await persona_service.create_persona(db, data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.get("", response_model=list[PersonaResponse])
async def list_all(language_id: UUID | None = None, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_personas"))):
    return await persona_service.get_personas(db, language_id)

@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_one(persona_id: UUID, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_personas"))):
    persona = await persona_service.get_persona(db, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona

@router.patch("/{persona_id}", response_model=PersonaResponse)
async def update_one(persona_id: UUID, data: PersonaUpdate, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_personas"))):
    persona = await persona_service.update_persona(db, persona_id, data)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona

@router.delete("/{persona_id}", status_code=204)
async def delete_one(persona_id: UUID, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_personas"))):
    if not await persona_service.delete_persona(db, persona_id):
        raise HTTPException(status_code=404, detail="Persona not found")

@router.post("/{persona_id}/image", response_model=PersonaResponse)
async def upload_image(persona_id: UUID, file: UploadFile = File(...), db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_personas"))):
    persona = await persona_service.get_persona(db, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    import aiofiles, os
    from app.config import settings
    os.makedirs(f"{settings.upload_dir}/personas", exist_ok=True)
    path = f"{settings.upload_dir}/personas/{persona_id}{os.path.splitext(file.filename)[1]}"
    async with aiofiles.open(path, "wb") as f:
        await f.write(await file.read())
    persona.image_url = path
    await db.flush()
    return persona
```

- [ ] **Step 4: Run tests, commit**

```bash
cd backend && pytest tests/test_admin/ -v
git add backend/
git commit -m "feat: add admin persona CRUD API with coordinator constraint"
```

---

### Task 10: Admin API — Plans, Users, Bans

**Files:**
- Create: `backend/app/services/plan_service.py`
- Create: `backend/app/services/user_service.py`
- Create: `backend/app/api/admin/plans.py`
- Create: `backend/app/api/admin/users.py`

- [ ] **Step 1: Implement plan service (plans are pre-seeded, only update)**

```python
# backend/app/services/plan_service.py
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.plan import Plan
from app.schemas.plan import PlanUpdate

async def get_plans(db: AsyncSession) -> list[Plan]:
    result = await db.execute(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price_monthly))
    return list(result.scalars().all())

async def get_plan(db: AsyncSession, plan_id: UUID) -> Plan | None:
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    return result.scalar_one_or_none()

async def get_plan_by_slug(db: AsyncSession, slug: str) -> Plan | None:
    result = await db.execute(select(Plan).where(Plan.slug == slug))
    return result.scalar_one_or_none()

async def update_plan(db: AsyncSession, plan_id: UUID, data: PlanUpdate) -> Plan | None:
    plan = await get_plan(db, plan_id)
    if not plan:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(plan, key, value)
    await db.flush()
    return plan
```

- [ ] **Step 2: Implement user management service**

```python
# backend/app/services/user_service.py
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, UserBan
from app.schemas.user import UserUpdate

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 50, search: str | None = None) -> list[User]:
    query = select(User).where(User.deleted_at.is_(None))
    if search:
        query = query.where(User.name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%"))
    result = await db.execute(query.offset(skip).limit(limit).order_by(User.created_at.desc()))
    return list(result.scalars().all())

async def get_user(db: AsyncSession, user_id: UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def update_user(db: AsyncSession, user_id: UUID, data: UserUpdate) -> User | None:
    user = await get_user(db, user_id)
    if not user:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    await db.flush()
    return user

async def toggle_user_active(db: AsyncSession, user_id: UUID, is_active: bool) -> User | None:
    user = await get_user(db, user_id)
    if not user:
        return None
    user.is_active = is_active
    await db.flush()
    return user

async def soft_delete_user(db: AsyncSession, user_id: UUID) -> bool:
    user = await get_user(db, user_id)
    if not user:
        return False
    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False
    await db.flush()
    return True

async def ban_user(db: AsyncSession, user_id: UUID, reason: str, expires_at: datetime | None = None) -> UserBan:
    user = await get_user(db, user_id)
    if not user:
        raise ValueError("User not found")
    user.is_banned = True
    user.ban_expires_at = expires_at
    ban = UserBan(user_id=user_id, reason=reason, expires_at=expires_at)
    db.add(ban)
    await db.flush()
    return ban

async def unban_user(db: AsyncSession, user_id: UUID) -> User | None:
    user = await get_user(db, user_id)
    if not user:
        return None
    user.is_banned = False
    user.ban_expires_at = None
    # Mark latest ban as unbanned
    result = await db.execute(
        select(UserBan).where(UserBan.user_id == user_id, UserBan.unbanned_at.is_(None))
        .order_by(UserBan.banned_at.desc())
    )
    ban = result.scalar_one_or_none()
    if ban:
        ban.unbanned_at = datetime.now(timezone.utc)
    await db.flush()
    return user
```

- [ ] **Step 3: Create plan admin routes**

```python
# backend/app/api/admin/plans.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.api.deps import require_permission
from app.schemas.plan import PlanUpdate, PlanResponse
from app.services import plan_service

router = APIRouter(prefix="/admin/plans", tags=["admin-plans"])

@router.get("", response_model=list[PlanResponse])
async def list_plans(db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_plans"))):
    return await plan_service.get_plans(db)

@router.patch("/{plan_id}", response_model=PlanResponse)
async def update_plan(plan_id: UUID, data: PlanUpdate, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_plans"))):
    plan = await plan_service.update_plan(db, plan_id, data)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan
```

- [ ] **Step 4: Create user admin routes**

```python
# backend/app/api/admin/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.api.deps import require_permission
from app.schemas.user import UserResponse, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/admin/users", tags=["admin-users"])

class BanRequest(BaseModel):
    reason: str
    expires_at: datetime | None = None

class SubscriptionAssign(BaseModel):
    plan_id: UUID
    billing_cycle: str = "monthly"
    expires_at: datetime | None = None

@router.get("", response_model=list[UserResponse])
async def list_users(skip: int = 0, limit: int = 50, search: str | None = None,
                     db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_users"))):
    return await user_service.get_users(db, skip, limit, search)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_users"))):
    user = await user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(user_id: UUID, data: UserUpdate, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_users"))):
    user = await user_service.update_user(db, user_id, data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/{user_id}/toggle-active", response_model=UserResponse)
async def toggle_active(user_id: UUID, is_active: bool, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_users"))):
    user = await user_service.toggle_user_active(db, user_id, is_active)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: UUID, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_users"))):
    if not await user_service.soft_delete_user(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")

@router.post("/{user_id}/ban")
async def ban(user_id: UUID, data: BanRequest, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_users"))):
    try:
        ban_record = await user_service.ban_user(db, user_id, data.reason, data.expires_at)
        return {"status": "banned", "ban_id": str(ban_record.id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{user_id}/unban", response_model=UserResponse)
async def unban(user_id: UUID, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("manage_users"))):
    user = await user_service.unban_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat: add admin APIs for plans, user management, and bans"
```

---

### Task 11: Admin API — Reports & Audit Logs

**Files:**
- Create: `backend/app/services/audit_service.py`
- Create: `backend/app/services/report_service.py`
- Create: `backend/app/api/admin/logs.py`
- Create: `backend/app/api/admin/reports.py`

- [ ] **Step 1: Implement audit service**

```python
# backend/app/services/audit_service.py
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.audit import AuditLog
from datetime import datetime

async def log_action(db: AsyncSession, actor_type: str, actor_id: UUID, action: str,
                     resource_type: str | None = None, resource_id: UUID | None = None,
                     details: dict | None = None, ip_address: str | None = None):
    log = AuditLog(actor_type=actor_type, actor_id=actor_id, action=action,
                   resource_type=resource_type, resource_id=resource_id,
                   details=details, ip_address=ip_address)
    db.add(log)
    await db.flush()
    return log

async def get_logs(db: AsyncSession, skip: int = 0, limit: int = 50,
                   action: str | None = None, actor_type: str | None = None,
                   from_date: datetime | None = None, to_date: datetime | None = None,
                   sort_by: str = "created_at", sort_order: str = "desc") -> list[AuditLog]:
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if actor_type:
        query = query.where(AuditLog.actor_type == actor_type)
    if from_date:
        query = query.where(AuditLog.created_at >= from_date)
    if to_date:
        query = query.where(AuditLog.created_at <= to_date)
    col = getattr(AuditLog, sort_by, AuditLog.created_at)
    query = query.order_by(col.desc() if sort_order == "desc" else col.asc())
    result = await db.execute(query.offset(skip).limit(limit))
    return list(result.scalars().all())
```

- [ ] **Step 2: Implement report service**

```python
# backend/app/services/report_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, date
from app.models.user import User
from app.models.session import Session
from app.models.usage import DailyUsage

async def user_registration_report(db: AsyncSession, from_date: date, to_date: date) -> dict:
    result = await db.execute(
        select(func.count(User.id)).where(
            func.date(User.created_at) >= from_date,
            func.date(User.created_at) <= to_date,
            User.deleted_at.is_(None),
        )
    )
    count = result.scalar()
    return {"period": f"{from_date} to {to_date}", "new_registrations": count}

async def active_users_report(db: AsyncSession, from_date: date, to_date: date) -> dict:
    result = await db.execute(
        select(func.count(func.distinct(Session.user_id))).where(
            func.date(Session.started_at) >= from_date,
            func.date(Session.started_at) <= to_date,
        )
    )
    count = result.scalar()
    return {"period": f"{from_date} to {to_date}", "active_users": count}

async def engagement_report(db: AsyncSession) -> dict:
    result = await db.execute(select(func.avg(Session.duration_seconds)))
    avg_duration = result.scalar() or 0
    return {"average_engagement_seconds": float(avg_duration)}

async def language_analytics(db: AsyncSession) -> list[dict]:
    from app.models.user import UserLanguage
    result = await db.execute(
        select(UserLanguage.language_id, func.count(UserLanguage.id).label("user_count"))
        .group_by(UserLanguage.language_id)
        .order_by(func.count(UserLanguage.id).desc())
    )
    return [{"language_id": str(row.language_id), "user_count": row.user_count} for row in result.all()]
```

- [ ] **Step 3: Create admin log and report routes**

```python
# backend/app/api/admin/logs.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.database import get_db
from app.api.deps import require_permission
from app.services import audit_service

router = APIRouter(prefix="/admin/logs", tags=["admin-logs"])

@router.get("")
async def get_logs(
    skip: int = 0, limit: int = 50,
    action: str | None = None, actor_type: str | None = None,
    from_date: datetime | None = None, to_date: datetime | None = None,
    sort_by: str = "created_at", sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_permission("view_logs")),
):
    return await audit_service.get_logs(db, skip, limit, action, actor_type, from_date, to_date, sort_by, sort_order)
```

```python
# backend/app/api/admin/reports.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from app.database import get_db
from app.api.deps import require_permission
from app.services import report_service

router = APIRouter(prefix="/admin/reports", tags=["admin-reports"])

@router.get("/registrations")
async def registrations(from_date: date, to_date: date, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("view_reports"))):
    return await report_service.user_registration_report(db, from_date, to_date)

@router.get("/active-users")
async def active_users(from_date: date, to_date: date, db: AsyncSession = Depends(get_db), admin=Depends(require_permission("view_reports"))):
    return await report_service.active_users_report(db, from_date, to_date)

@router.get("/engagement")
async def engagement(db: AsyncSession = Depends(get_db), admin=Depends(require_permission("view_reports"))):
    return await report_service.engagement_report(db)

@router.get("/language-analytics")
async def lang_analytics(db: AsyncSession = Depends(get_db), admin=Depends(require_permission("view_reports"))):
    return await report_service.language_analytics(db)
```

- [ ] **Step 4: Commit**

```bash
git add backend/
git commit -m "feat: add admin audit logs and reports APIs"
```

---

### Task 12: Mobile API — User, Languages, Subscription, Sessions

**Files:**
- Create: `backend/app/api/mobile/users.py`
- Create: `backend/app/api/mobile/languages.py`
- Create: `backend/app/api/mobile/subscriptions.py`
- Create: `backend/app/api/mobile/sessions.py`
- Create: `backend/app/api/mobile/chat.py`
- Create: `backend/app/api/mobile/support.py`
- Create: `backend/app/services/subscription_service.py`
- Create: `backend/app/services/session_service.py`
- Create: `backend/app/services/usage_service.py`

- [ ] **Step 1: Implement subscription service with pro-rata**

```python
# backend/app/services/subscription_service.py
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.subscription import UserSubscription
from app.models.plan import Plan

async def get_active_subscription(db: AsyncSession, user_id: UUID) -> UserSubscription | None:
    result = await db.execute(
        select(UserSubscription).where(
            UserSubscription.user_id == user_id,
            UserSubscription.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()

async def create_subscription(db: AsyncSession, user_id: UUID, plan_id: UUID,
                                billing_cycle: str, store_transaction_id: str | None = None,
                                store_type: str | None = None) -> UserSubscription:
    # Deactivate existing
    existing = await get_active_subscription(db, user_id)
    if existing:
        existing.is_active = False

    now = datetime.now(timezone.utc)
    if billing_cycle == "yearly":
        expires = now + timedelta(days=365)
    else:
        expires = now + timedelta(days=30)

    sub = UserSubscription(
        user_id=user_id, plan_id=plan_id, billing_cycle=billing_cycle,
        started_at=now, expires_at=expires,
        store_transaction_id=store_transaction_id, store_type=store_type,
    )
    db.add(sub)
    await db.flush()
    return sub

async def change_subscription(db: AsyncSession, user_id: UUID, new_plan_id: UUID,
                                new_billing_cycle: str) -> dict:
    existing = await get_active_subscription(db, user_id)
    if not existing:
        return await create_subscription(db, user_id, new_plan_id, new_billing_cycle)

    now = datetime.now(timezone.utc)
    # Calculate pro-rata credit
    total_days = (existing.expires_at - existing.started_at).days or 1
    remaining_days = max(0, (existing.expires_at - now).days)
    old_plan = await db.execute(select(Plan).where(Plan.id == existing.plan_id))
    old_plan = old_plan.scalar_one()
    old_price = old_plan.price_yearly if existing.billing_cycle == "yearly" else old_plan.price_monthly
    credit = float(old_price) * remaining_days / total_days

    new_plan = await db.execute(select(Plan).where(Plan.id == new_plan_id))
    new_plan = new_plan.scalar_one()
    new_price = new_plan.price_yearly if new_billing_cycle == "yearly" else new_plan.price_monthly

    # Deactivate old
    existing.is_active = False

    # Create new
    sub = await create_subscription(db, user_id, new_plan_id, new_billing_cycle)
    return {"subscription": sub, "credit": round(credit, 2), "new_price": float(new_price)}
```

- [ ] **Step 2: Implement usage service**

```python
# backend/app/services/usage_service.py
from uuid import UUID
from datetime import date, datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.usage import DailyUsage, MonthlyUsage
from app.models.subscription import UserSubscription
from app.models.plan import Plan

async def get_daily_usage(db: AsyncSession, user_id: UUID, usage_date: date | None = None) -> DailyUsage:
    if not usage_date:
        usage_date = datetime.now(timezone.utc).date()
    result = await db.execute(
        select(DailyUsage).where(DailyUsage.user_id == user_id, DailyUsage.date == usage_date)
    )
    usage = result.scalar_one_or_none()
    if not usage:
        usage = DailyUsage(user_id=user_id, date=usage_date)
        db.add(usage)
        await db.flush()
    return usage

async def check_limit(db: AsyncSession, user_id: UUID, feature: str) -> dict:
    """Check if user has remaining time for a feature. Returns {allowed: bool, remaining_minutes: float}"""
    usage = await get_daily_usage(db, user_id)
    # Get user's plan
    sub_result = await db.execute(
        select(UserSubscription).where(UserSubscription.user_id == user_id, UserSubscription.is_active.is_(True))
    )
    sub = sub_result.scalar_one_or_none()
    if not sub:
        return {"allowed": False, "remaining_minutes": 0}

    plan_result = await db.execute(select(Plan).where(Plan.id == sub.plan_id))
    plan = plan_result.scalar_one()

    limit_map = {
        "voice_call": (plan.voice_call_limit_minutes, usage.voice_call_minutes),
        "video_call": (plan.video_call_limit_minutes, usage.video_call_minutes),
        "text_learning": (plan.text_learning_limit_minutes, usage.text_learning_minutes),
    }

    if feature not in limit_map:
        return {"allowed": False, "remaining_minutes": 0}

    limit, used = limit_map[feature]
    if limit == 0:  # unlimited
        return {"allowed": True, "remaining_minutes": float("inf")}
    remaining = max(0, limit - used)
    return {"allowed": remaining > 0, "remaining_minutes": remaining}

async def record_usage(db: AsyncSession, user_id: UUID, feature: str, minutes: float):
    usage = await get_daily_usage(db, user_id)
    if feature == "voice_call":
        usage.voice_call_minutes += minutes
    elif feature == "video_call":
        usage.video_call_minutes += minutes
    elif feature == "text_learning":
        usage.text_learning_minutes += minutes
    await db.flush()
```

- [ ] **Step 3: Implement session service**

```python
# backend/app/services/session_service.py
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.session import Session, SessionTranscript, ChatMessage

async def create_session(db: AsyncSession, user_id: UUID, persona_id: UUID,
                          session_type: str, session_mode: str,
                          user_language_id: UUID | None = None,
                          cefr_level: str | None = None) -> Session:
    session = Session(
        user_id=user_id, persona_id=persona_id,
        user_language_id=user_language_id,
        session_type=session_type, session_mode=session_mode,
        cefr_level_at_time=cefr_level,
    )
    db.add(session)
    await db.flush()
    return session

async def end_session(db: AsyncSession, session_id: UUID, duration: int, metrics: dict | None = None):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session:
        session.ended_at = datetime.now(timezone.utc)
        session.duration_seconds = duration
        if metrics:
            session.performance_metrics = metrics
        await db.flush()
    return session

async def get_user_sessions(db: AsyncSession, user_id: UUID, language_id: UUID | None = None,
                             skip: int = 0, limit: int = 50) -> list[Session]:
    query = select(Session).where(Session.user_id == user_id)
    if language_id:
        from app.models.user import UserLanguage
        ul_result = await db.execute(
            select(UserLanguage.id).where(UserLanguage.user_id == user_id, UserLanguage.language_id == language_id)
        )
        ul_ids = [r for r in ul_result.scalars().all()]
        if ul_ids:
            query = query.where(Session.user_language_id.in_(ul_ids))
    result = await db.execute(query.order_by(Session.started_at.desc()).offset(skip).limit(limit))
    return list(result.scalars().all())

async def get_session_transcript(db: AsyncSession, session_id: UUID) -> list[SessionTranscript]:
    result = await db.execute(
        select(SessionTranscript).where(SessionTranscript.session_id == session_id)
        .order_by(SessionTranscript.timestamp_offset_ms)
    )
    return list(result.scalars().all())

async def add_chat_message(db: AsyncSession, session_id: UUID, sender: str, content: str) -> ChatMessage:
    msg = ChatMessage(session_id=session_id, sender=sender, content=content)
    db.add(msg)
    await db.flush()
    return msg

async def get_chat_messages(db: AsyncSession, session_id: UUID) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    return list(result.scalars().all())
```

- [ ] **Step 4: Create mobile API routes**

```python
# backend/app/api/mobile/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/mobile/users", tags=["mobile-users"])

@router.get("/me", response_model=UserResponse)
async def get_profile(user: User = Depends(get_current_user)):
    return user

@router.patch("/me", response_model=UserResponse)
async def update_profile(data: UserUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    updated = await user_service.update_user(db, user.id, data)
    return updated
```

```python
# backend/app/api/mobile/languages.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.language import LanguageResponse
from app.services import language_service

router = APIRouter(prefix="/mobile/languages", tags=["mobile-languages"])

@router.get("", response_model=list[LanguageResponse])
async def list_languages(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await language_service.get_languages(db)
```

```python
# backend/app/api/mobile/subscriptions.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.subscription import SubscriptionCreate, SubscriptionResponse
from app.services import subscription_service

router = APIRouter(prefix="/mobile/subscriptions", tags=["mobile-subscriptions"])

@router.get("/current", response_model=SubscriptionResponse | None)
async def get_current(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await subscription_service.get_active_subscription(db, user.id)

@router.post("", response_model=SubscriptionResponse)
async def create(data: SubscriptionCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    sub = await subscription_service.create_subscription(
        db, user.id, data.plan_id, data.billing_cycle, data.store_transaction_id, data.store_type
    )
    return sub

@router.post("/change")
async def change(data: SubscriptionCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await subscription_service.change_subscription(db, user.id, data.plan_id, data.billing_cycle)
    return result
```

```python
# backend/app/api/mobile/sessions.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.session import SessionResponse, TranscriptResponse
from app.services import session_service

router = APIRouter(prefix="/mobile/sessions", tags=["mobile-sessions"])

@router.get("", response_model=list[SessionResponse])
async def list_sessions(language_id: UUID | None = None, skip: int = 0, limit: int = 50,
                        user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await session_service.get_user_sessions(db, user.id, language_id, skip, limit)

@router.get("/{session_id}/transcript", response_model=list[TranscriptResponse])
async def get_transcript(session_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await session_service.get_session_transcript(db, session_id)
```

```python
# backend/app/api/mobile/chat.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.session import ChatMessageCreate, ChatMessageResponse
from app.services import session_service

router = APIRouter(prefix="/mobile/chat", tags=["mobile-chat"])

@router.get("/{session_id}/messages", response_model=list[ChatMessageResponse])
async def get_messages(session_id: UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await session_service.get_chat_messages(db, session_id)

@router.post("/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message(session_id: UUID, data: ChatMessageCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await session_service.add_chat_message(db, session_id, "user", data.content)
```

```python
# backend/app/api/mobile/support.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services import session_service
from app.schemas.session import SessionResponse

router = APIRouter(prefix="/mobile/support", tags=["mobile-support"])

@router.get("/history", response_model=list[SessionResponse])
async def support_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.session import Session
    result = await db.execute(
        select(Session).where(Session.user_id == user.id, Session.session_mode == "support")
        .order_by(Session.started_at.desc())
    )
    return list(result.scalars().all())
```

- [ ] **Step 5: Register all routers in main.py**

```python
# Update backend/app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="LangTutor API", version="0.1.0", lifespan=lifespan)

# Auth
from app.api.auth import router as auth_router
app.include_router(auth_router, prefix="/api")

# Admin routes
from app.api.admin.languages import router as admin_lang_router
from app.api.admin.personas import router as admin_persona_router
from app.api.admin.plans import router as admin_plan_router
from app.api.admin.users import router as admin_user_router
from app.api.admin.logs import router as admin_log_router
from app.api.admin.reports import router as admin_report_router
app.include_router(admin_lang_router, prefix="/api")
app.include_router(admin_persona_router, prefix="/api")
app.include_router(admin_plan_router, prefix="/api")
app.include_router(admin_user_router, prefix="/api")
app.include_router(admin_log_router, prefix="/api")
app.include_router(admin_report_router, prefix="/api")

# Mobile routes
from app.api.mobile.users import router as mobile_user_router
from app.api.mobile.languages import router as mobile_lang_router
from app.api.mobile.subscriptions import router as mobile_sub_router
from app.api.mobile.sessions import router as mobile_session_router
from app.api.mobile.chat import router as mobile_chat_router
from app.api.mobile.support import router as mobile_support_router
app.include_router(mobile_user_router, prefix="/api")
app.include_router(mobile_lang_router, prefix="/api")
app.include_router(mobile_sub_router, prefix="/api")
app.include_router(mobile_session_router, prefix="/api")
app.include_router(mobile_chat_router, prefix="/api")
app.include_router(mobile_support_router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Create DB seed script for plans**

```python
# backend/app/seed.py
import asyncio
from app.database import engine, Base, async_session_factory
from app.models.plan import Plan
from app.models.admin import AdminRole, AdminUser
from app.utils.security import hash_password
from sqlalchemy import select

async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # Seed plans
        existing = await db.execute(select(Plan))
        if not existing.scalars().first():
            plans = [
                Plan(name="Free", slug="free", price_monthly=0, price_yearly=0,
                     text_learning_limit_minutes=0, voice_call_limit_minutes=30,
                     video_call_limit_minutes=0, agentic_voice_limit_monthly=0,
                     coordinator_video_limit_monthly=0),
                Plan(name="Pro", slug="pro", price_monthly=4.99, price_yearly=49.99,
                     text_learning_limit_minutes=0, voice_call_limit_minutes=0,
                     video_call_limit_minutes=15, agentic_voice_limit_monthly=5,
                     coordinator_video_limit_monthly=2),
                Plan(name="Ultra", slug="ultra", price_monthly=9.99, price_yearly=99.99,
                     text_learning_limit_minutes=0, voice_call_limit_minutes=0,
                     video_call_limit_minutes=0, agentic_voice_limit_monthly=0,
                     coordinator_video_limit_monthly=0),
            ]
            db.add_all(plans)

        # Seed super admin role
        role_result = await db.execute(select(AdminRole).where(AdminRole.name == "super_admin"))
        if not role_result.scalars().first():
            role = AdminRole(name="super_admin", permissions=[
                "manage_users", "manage_languages", "manage_personas",
                "manage_plans", "manage_admins", "view_logs", "view_reports",
            ])
            db.add(role)
            await db.flush()

            admin = AdminUser(
                email="admin@langtutor.com", name="Super Admin",
                password_hash=hash_password("admin123"), role_id=role.id,
            )
            db.add(admin)

        await db.commit()
    print("Seed complete!")

if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 7: Run full test suite, commit**

```bash
cd backend && pytest -v
git add backend/
git commit -m "feat: add mobile APIs, subscription service, usage tracking, and DB seed"
```

---

### Task 13: Docker & Docker Compose Setup

**Files:**
- Create: `backend/Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install -e .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create docker-compose.yml**

```yaml
# docker-compose.yml (project root)
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: langtutor
      POSTGRES_PASSWORD: langtutor
      POSTGRES_DB: langtutor
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      LANGTUTOR_DATABASE_URL: postgresql+asyncpg://langtutor:langtutor@db:5432/langtutor
      LANGTUTOR_SECRET_KEY: dev-secret-key-change-in-prod
    depends_on:
      - db
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  livekit:
    image: livekit/livekit-server:latest
    ports:
      - "7880:7880"
      - "7881:7881"
    environment:
      LIVEKIT_KEYS: "devkey: secret"

volumes:
  pgdata:
```

- [ ] **Step 3: Commit**

```bash
git add backend/Dockerfile docker-compose.yml
git commit -m "feat: add Docker and docker-compose setup for backend, DB, and LiveKit"
```

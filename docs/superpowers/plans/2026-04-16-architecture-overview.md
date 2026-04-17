# LangTutor — Master Architecture Overview

## System Overview

LangTutor is a freemium AI language tutoring platform where users learn languages via voice/video calls and text chat with AI-driven personas. The system uses LiveKit for WebRTC transport, LivePortrait for real-time avatar video generation, Fish Speech S2 for TTS, Deepgram for STT, and Gemini 1.5 Flash as the AI brain.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Flutter Mobile App                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │   Auth    │ │  Home    │ │ Learning │ │ Profile  │       │
│  │  Screen   │ │  Screen  │ │ Screens  │ │ Screens  │       │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘       │
│       │             │            │             │             │
│  ┌────┴─────────────┴────────────┴─────────────┴──────┐     │
│  │              State Management (Riverpod)            │     │
│  └────────────────────┬───────────────────────────────┘     │
│                       │                                      │
│  ┌────────────────────┴───────────────────────────────┐     │
│  │         API Client (Dio) + LiveKit Client SDK       │     │
│  └────────────────────┬───────────────────────────────┘     │
└───────────────────────┼─────────────────────────────────────┘
                        │ HTTPS / WSS
                        ▼
┌───────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                           │
│                                                                │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐    │
│  │  Auth &     │  │  Admin API   │  │  User API         │    │
│  │  ACL Layer  │  │  (CRUD)      │  │  (Profile/Sub)    │    │
│  └──────┬──────┘  └──────┬───────┘  └────────┬──────────┘    │
│         │                │                    │               │
│  ┌──────┴────────────────┴────────────────────┴──────────┐   │
│  │              Service Layer (Business Logic)            │   │
│  └──────────────────────┬────────────────────────────────┘   │
│                         │                                     │
│  ┌──────────────────────┴────────────────────────────────┐   │
│  │           SQLAlchemy ORM + Alembic Migrations          │   │
│  └──────────────────────┬────────────────────────────────┘   │
│                         │                                     │
│  ┌──────────────────────┴───┐                                │
│  │     PostgreSQL Database   │                                │
│  └──────────────────────────┘                                │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              LiveKit Agent Worker                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐     │   │
│  │  │ Deepgram │  │  Gemini  │  │  Fish Speech S2  │     │   │
│  │  │  (STT)   │  │  (LLM)  │  │  (TTS)           │     │   │
│  │  └────┬─────┘  └────┬─────┘  └────────┬─────────┘     │   │
│  │       │              │                 │               │   │
│  │  ┌────┴──────────────┴─────────────────┴──────────┐    │   │
│  │  │   livekit-plugins-avatartalk (LivePortrait)     │    │   │
│  │  │   TensorRT Optimized Avatar Video Generation    │    │   │
│  │  └────────────────────────────────────────────────┘    │   │
│  └────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

---

## Database Schema (PostgreSQL)

### Core Tables

```
users
├── id (UUID, PK)
├── email (unique)
├── name (varchar)
├── date_of_birth (date, nullable)
├── avatar_id (FK → user_avatars.id)
├── native_language_id (FK → languages.id)
├── auth_provider (enum: google, apple)
├── auth_provider_id (varchar)
├── is_active (bool, default true)
├── is_banned (bool, default false)
├── ban_expires_at (timestamp, nullable)
├── deleted_at (timestamp, nullable)  -- soft delete
├── created_at (timestamp)
└── updated_at (timestamp)

admin_users
├── id (UUID, PK)
├── email (unique)
├── name (varchar)
├── password_hash (varchar)
├── role_id (FK → admin_roles.id)
├── is_active (bool)
├── deleted_at (timestamp, nullable)
├── created_at (timestamp)
└── updated_at (timestamp)

admin_roles
├── id (UUID, PK)
├── name (varchar, unique)
├── permissions (JSONB)  -- list of permission keys
├── created_at (timestamp)
└── updated_at (timestamp)

languages
├── id (UUID, PK)
├── name (varchar)           -- e.g. "Spanish"
├── locale (varchar, unique) -- e.g. "es-ES"
├── icon_url (varchar)       -- flag image path
├── is_default (bool)        -- default locale for this language name
├── is_fallback (bool)       -- only ONE can be true globally
├── is_active (bool)
├── deleted_at (timestamp, nullable)
├── created_at (timestamp)
└── updated_at (timestamp)

personas
├── id (UUID, PK)
├── name (varchar)
├── language_id (FK → languages.id)
├── image_url (varchar)
├── gender (enum: male, female, other)
├── type (enum: teacher, coordinator, peer)
├── teaching_style (enum: casual_friendly, friendly_structured, formal_structured, nullable)
├── is_active (bool)
├── deleted_at (timestamp, nullable)
├── created_at (timestamp)
└── updated_at (timestamp)
-- CONSTRAINT: only one coordinator per language_id

plans
├── id (UUID, PK)
├── name (varchar)                          -- Free, Pro, Ultra
├── slug (varchar, unique)                  -- free, pro, ultra
├── price_monthly (decimal, nullable)
├── price_yearly (decimal, nullable)
├── text_learning_limit_minutes (int)       -- 0 = unlimited
├── voice_call_limit_minutes (int)          -- 0 = unlimited
├── video_call_limit_minutes (int)          -- 0 = unlimited
├── agentic_voice_limit_monthly (int)       -- 0 = unlimited
├── coordinator_video_limit_monthly (int)   -- 0 = unlimited
├── is_active (bool)
├── created_at (timestamp)
└── updated_at (timestamp)

user_subscriptions
├── id (UUID, PK)
├── user_id (FK → users.id)
├── plan_id (FK → plans.id)
├── billing_cycle (enum: monthly, yearly)
├── started_at (timestamp)
├── expires_at (timestamp)
├── store_transaction_id (varchar, nullable)
├── store_type (enum: apple, google, nullable)
├── is_active (bool)
├── created_at (timestamp)
└── updated_at (timestamp)

user_languages
├── id (UUID, PK)
├── user_id (FK → users.id)
├── language_id (FK → languages.id)
├── teacher_persona_id (FK → personas.id)
├── teaching_style (enum)
├── current_cefr_level (enum: A0, A1, A2, B1, B2, C1)
├── cefr_progress_percent (float)
├── is_active (bool)
├── created_at (timestamp)
└── updated_at (timestamp)

cefr_level_history
├── id (UUID, PK)
├── user_language_id (FK → user_languages.id)
├── cefr_level (enum)
├── status (enum: passed, in_progress)
├── topics_covered (JSONB)
├── lessons_count (int)
├── hours_spent (float)
├── practice_sessions (int)
├── practice_hours (float)
├── streak_days (int)
├── progress_percent (float)
├── started_at (timestamp)
├── passed_at (timestamp, nullable)
└── updated_at (timestamp)

sessions
├── id (UUID, PK)
├── user_id (FK → users.id)
├── user_language_id (FK → user_languages.id)
├── persona_id (FK → personas.id)
├── session_type (enum: voice_call, video_call, text_chat)
├── session_mode (enum: learning, practice, support, onboarding)
├── livekit_room_name (varchar, nullable)
├── duration_seconds (int)
├── cefr_level_at_time (enum)
├── topics_covered (JSONB)
├── performance_metrics (JSONB)
├── skills_breakdown (JSONB)   -- reading/writing/listening/speaking
├── vocabulary_tracked (JSONB)
├── started_at (timestamp)
├── ended_at (timestamp, nullable)
└── created_at (timestamp)

session_transcripts
├── id (UUID, PK)
├── session_id (FK → sessions.id)
├── speaker (enum: user, persona)
├── content (text)
├── timestamp_offset_ms (int)
├── created_at (timestamp)
└── updated_at (timestamp)

chat_messages
├── id (UUID, PK)
├── session_id (FK → sessions.id)
├── sender (enum: user, persona)
├── content (text)
├── is_read (bool, default false)
├── created_at (timestamp)
└── updated_at (timestamp)

daily_usage
├── id (UUID, PK)
├── user_id (FK → users.id)
├── date (date)
├── voice_call_minutes (float, default 0)
├── video_call_minutes (float, default 0)
├── text_learning_minutes (float, default 0)
├── created_at (timestamp)
└── updated_at (timestamp)

monthly_usage
├── id (UUID, PK)
├── user_id (FK → users.id)
├── month (date)  -- first day of month
├── agentic_voice_calls (int, default 0)
├── coordinator_video_calls (int, default 0)
├── created_at (timestamp)
└── updated_at (timestamp)

audit_logs
├── id (UUID, PK)
├── actor_type (enum: user, admin, system)
├── actor_id (UUID)
├── action (varchar)
├── resource_type (varchar)
├── resource_id (UUID, nullable)
├── details (JSONB)
├── ip_address (varchar, nullable)
├── created_at (timestamp)
└── updated_at (timestamp)

user_avatars
├── id (UUID, PK)
├── image_url (varchar)
├── is_active (bool)
├── created_at (timestamp)
└── updated_at (timestamp)

user_bans
├── id (UUID, PK)
├── user_id (FK → users.id)
├── reason (text)
├── banned_at (timestamp)
├── expires_at (timestamp, nullable)
├── unbanned_at (timestamp, nullable)
├── created_at (timestamp)
└── updated_at (timestamp)
```

---

## Backend Directory Structure

```
backend/
├── alembic/                    # Database migrations
│   ├── versions/
│   └── env.py
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Settings & environment
│   ├── database.py             # DB engine & session
│   ├── dependencies.py         # Shared FastAPI dependencies
│   │
│   ├── models/                 # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── admin.py
│   │   ├── language.py
│   │   ├── persona.py
│   │   ├── plan.py
│   │   ├── subscription.py
│   │   ├── session.py
│   │   ├── usage.py
│   │   └── audit.py
│   │
│   ├── schemas/                # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── admin.py
│   │   ├── language.py
│   │   ├── persona.py
│   │   ├── plan.py
│   │   ├── subscription.py
│   │   ├── session.py
│   │   └── auth.py
│   │
│   ├── api/                    # Route handlers
│   │   ├── __init__.py
│   │   ├── deps.py             # Route-level dependencies
│   │   ├── auth.py             # Social login endpoints
│   │   ├── admin/
│   │   │   ├── __init__.py
│   │   │   ├── users.py
│   │   │   ├── languages.py
│   │   │   ├── personas.py
│   │   │   ├── plans.py
│   │   │   ├── reports.py
│   │   │   └── logs.py
│   │   └── mobile/
│   │       ├── __init__.py
│   │       ├── users.py
│   │       ├── languages.py
│   │       ├── sessions.py
│   │       ├── subscriptions.py
│   │       ├── chat.py
│   │       └── support.py
│   │
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── language_service.py
│   │   ├── persona_service.py
│   │   ├── plan_service.py
│   │   ├── subscription_service.py
│   │   ├── session_service.py
│   │   ├── usage_service.py
│   │   ├── onboarding_service.py
│   │   ├── cefr_service.py
│   │   ├── audit_service.py
│   │   ├── report_service.py
│   │   └── geoip_service.py
│   │
│   ├── ai/                     # AI/LiveKit integration
│   │   ├── __init__.py
│   │   ├── agent_worker.py     # LiveKit agent entrypoint
│   │   ├── tutor_agent.py      # Teaching/practice logic
│   │   ├── coordinator_agent.py # Onboarding/support logic
│   │   ├── prompt_templates.py # Gemini prompt templates
│   │   └── cefr_assessor.py    # CEFR level assessment
│   │
│   └── utils/
│       ├── __init__.py
│       ├── security.py         # JWT, password hashing
│       ├── file_upload.py      # Image upload handling
│       └── pagination.py       # Pagination helpers
│
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_admin/
│   ├── test_mobile/
│   └── test_services/
│
├── alembic.ini
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

---

## Flutter App Directory Structure

```
mobile/
├── lib/
│   ├── main.dart
│   ├── app.dart                     # MaterialApp + routing
│   │
│   ├── config/
│   │   ├── theme.dart               # Colors, text styles, pastel palette
│   │   ├── routes.dart              # Named routes
│   │   └── constants.dart           # API URLs, timeouts
│   │
│   ├── models/                      # Data classes
│   │   ├── user.dart
│   │   ├── language.dart
│   │   ├── persona.dart
│   │   ├── plan.dart
│   │   ├── subscription.dart
│   │   ├── session.dart
│   │   ├── chat_message.dart
│   │   └── cefr_level.dart
│   │
│   ├── providers/                   # Riverpod providers
│   │   ├── auth_provider.dart
│   │   ├── user_provider.dart
│   │   ├── language_provider.dart
│   │   ├── session_provider.dart
│   │   ├── subscription_provider.dart
│   │   ├── chat_provider.dart
│   │   └── usage_provider.dart
│   │
│   ├── services/                    # API client & platform services
│   │   ├── api_client.dart          # Dio HTTP client
│   │   ├── auth_service.dart        # Social login
│   │   ├── livekit_service.dart     # LiveKit room connection
│   │   ├── iap_service.dart         # In-app purchases
│   │   └── geoip_service.dart       # Phone locale + GeoIP
│   │
│   ├── screens/
│   │   ├── auth/
│   │   │   └── login_screen.dart
│   │   ├── onboarding/
│   │   │   ├── onboarding_call_screen.dart
│   │   │   ├── user_info_screen.dart
│   │   │   └── plan_selection_screen.dart
│   │   ├── home/
│   │   │   ├── home_screen.dart
│   │   │   └── language_popup.dart
│   │   ├── learning/
│   │   │   ├── voice_call_screen.dart
│   │   │   ├── video_call_screen.dart
│   │   │   └── chat_screen.dart
│   │   ├── practice/
│   │   │   └── practice_hub_screen.dart
│   │   ├── profile/
│   │   │   ├── profile_screen.dart
│   │   │   ├── profile_edit_screen.dart
│   │   │   ├── cefr_screen.dart
│   │   │   ├── history_screen.dart
│   │   │   ├── transcript_screen.dart
│   │   │   └── subscription_screen.dart
│   │   └── support/
│   │       └── support_screen.dart
│   │
│   └── widgets/                     # Reusable components
│       ├── bottom_nav_bar.dart
│       ├── top_info_bar.dart
│       ├── persona_avatar.dart
│       ├── call_controls.dart
│       ├── chat_bubble.dart
│       ├── plan_card.dart
│       ├── cefr_level_tile.dart
│       ├── bubble_background.dart   # Pastel BG with bubbles
│       └── language_flag.dart
│
├── assets/
│   ├── images/
│   └── fonts/
│
├── test/
├── pubspec.yaml
├── android/
└── ios/
```

---

## Key Technology Decisions

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Backend Framework | FastAPI | Requirement-specified; async, fast |
| Database | PostgreSQL | Complex relational data, JSONB for flexible fields |
| ORM | SQLAlchemy 2.0 | Async support, mature ecosystem |
| Migrations | Alembic | Standard for SQLAlchemy |
| Auth | Social Login (Google/Apple) | Requirement: mobile platform social login only |
| JWT | python-jose | Token-based auth for API |
| Mobile Framework | Flutter | Requirement-specified; cross-platform |
| State Management | Riverpod | Type-safe, testable, composable |
| HTTP Client | Dio | Interceptors, retry, logging |
| WebRTC | LiveKit Flutter SDK | Connects to LiveKit server |
| AI Brain | Gemini 1.5 Flash | Requirement-specified |
| TTS | Fish Speech S2 | Local, cost-effective |
| STT | Deepgram (self-hosted) | Local, cost-effective |
| Avatar Video | LivePortrait via livekit-plugins-avatartalk | Requirement-specified, TensorRT |
| In-App Purchase | revenue_cat or native | Apple/Google IAP |
| GeoIP | ip-api.com or MaxMind | Locale detection |

---

## Subsystem Plans

This project is decomposed into 5 independently buildable plans:

1. **Backend Core** — DB models, migrations, auth, admin CRUD APIs, user APIs
2. **Backend AI & Sessions** — LiveKit agent workers, Gemini integration, session management, CEFR engine
3. **Flutter App Foundation** — Project setup, theme, auth, navigation, home screen
4. **Flutter Learning & Practice** — Voice/video/chat screens, practice hub, LiveKit client
5. **Flutter Profile & Support** — Profile tabs, subscription, support, history/transcripts

Each plan produces working, testable software on its own.

# Plan 2: Backend AI & Session Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the LiveKit agent workers that power AI tutoring — integrating Deepgram STT, Fish Speech S2 TTS, Gemini 1.5 Flash as the brain, and LivePortrait via livekit-plugins-avatartalk for avatar video generation.

**Architecture:** LiveKit Agent Framework workers connect to LiveKit server. Each session spawns an agent that orchestrates STT → LLM → TTS → Avatar pipeline. Session state is managed via the FastAPI backend database. The agent communicates with the backend API for user context, CEFR tracking, and usage enforcement.

**Tech Stack:** livekit-agents, livekit-plugins-deepgram, livekit-plugins-avatartalk, google-generativeai (Gemini), Fish Speech S2 client, httpx (backend API calls)

---

### Task 1: AI Agent Project Setup

**Files:**
- Create: `backend/app/ai/__init__.py`
- Create: `backend/app/ai/agent_worker.py`
- Modify: `backend/pyproject.toml` (add AI dependencies)

- [ ] **Step 1: Add AI dependencies to pyproject.toml**

Add to `[project.dependencies]`:
```toml
    "livekit-agents>=0.11.0",
    "livekit-plugins-deepgram>=0.6.0",
    "livekit>=0.13.0",
    "google-generativeai>=0.7.0",
```

- [ ] **Step 2: Create agent worker entry point**

```python
# backend/app/ai/agent_worker.py
import logging
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.voice_assistant import VoiceAssistant
from app.ai.tutor_agent import create_tutor_agent
from app.ai.coordinator_agent import create_coordinator_agent

logger = logging.getLogger("langtutor-agent")

async def entrypoint(ctx: JobContext):
    logger.info(f"Agent job started: room={ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Room metadata determines agent type
    metadata = ctx.room.metadata or ""
    if "onboarding" in metadata or "support" in metadata:
        agent = await create_coordinator_agent(ctx)
    else:
        agent = await create_tutor_agent(ctx)

    agent.start(ctx.room)
    await agent.say("Hello! I'm ready to help you.", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/ai/ backend/pyproject.toml
git commit -m "feat: scaffold LiveKit agent worker entry point"
```

---

### Task 2: Gemini LLM Integration

**Files:**
- Create: `backend/app/ai/prompt_templates.py`
- Create: `backend/app/ai/gemini_plugin.py`

- [ ] **Step 1: Create prompt templates for tutoring**

```python
# backend/app/ai/prompt_templates.py

COORDINATOR_SYSTEM_PROMPT = """You are a friendly language learning coordinator for LangTutor.
Your role is to:
1. Greet the user in their detected native language
2. Confirm their native language
3. Ask which language they want to learn
4. Assess their CEFR level through natural conversation and mini quizzes
5. Help them choose a teacher

Current user context:
- Detected native language: {native_language}
- Detected locale: {locale}
- Available languages: {available_languages}

Rules:
- Be warm, encouraging, and professional
- If the user's language is not available, inform them and fall back to {fallback_language}
- For CEFR assessment, use a mix of conversation and textual questions
- Cover: vocabulary, grammar, reading comprehension, listening comprehension
- Assess levels: A0 (complete beginner) through C1 (advanced)
- Be concise — keep responses under 3 sentences unless testing
"""

TUTOR_SYSTEM_PROMPT = """You are an AI language tutor for LangTutor.
You are teaching {target_language} to a student whose native language is {native_language}.

Student profile:
- Name: {student_name}
- Current CEFR level: {cefr_level}
- CEFR progress: {progress_percent}%
- Teaching style preference: {teaching_style}
- Topics already covered: {topics_covered}
- Known weaknesses: {weaknesses}

Rules:
- {use_native_language_rule}
- Structure lessons dynamically based on student weaknesses and interests
- Make learning fun and engaging
- No topic overlap with higher CEFR levels
- Reinforce past knowledge from lower levels
- When all topics for current level are covered, initiate assessment
- If student fails assessment, focus on weaknesses while reviewing other topics
- Keep responses conversational and natural
- For text-based exercises, clearly format questions with options
"""

PRACTICE_SYSTEM_PROMPT = """You are an AI language practice partner for LangTutor.
You are helping a student practice {target_language}.

Student profile:
- Name: {student_name}
- Current CEFR level: {cefr_level}
- Topics learned so far: {topics_covered}

Rules:
- Only practice topics the student has already learned
- Do NOT teach new material
- Use conversation, role-play, and exercises to reinforce knowledge
- Be encouraging and correct mistakes gently
- Vary practice methods to keep it interesting
"""

SUPPORT_SYSTEM_PROMPT = """You are a support coordinator for LangTutor.
Help the user with any issues they are experiencing with the app or their learning journey.

User context:
- Name: {student_name}
- Current plan: {plan_name}
- Languages learning: {languages}

Rules:
- Be helpful and empathetic
- For technical issues, gather details and log them
- For learning-related questions, provide guidance
- Do not teach languages during support calls
- Keep the conversation focused on resolving the issue
"""

def get_native_language_rule(cefr_level: str) -> str:
    if cefr_level in ("A0", "A1", "A2", "B1"):
        return "Use the student's native language for explanations and instructions. Gradually introduce target language vocabulary."
    else:
        return "Conduct the entire lesson in the target language. Only use native language if the student is completely stuck."
```

- [ ] **Step 2: Create Gemini LLM plugin adapter**

```python
# backend/app/ai/gemini_plugin.py
import google.generativeai as genai
from livekit.agents import llm
from app.config import settings

genai.configure(api_key=settings.gemini_api_key if hasattr(settings, 'gemini_api_key') else "")

class GeminiLLM(llm.LLM):
    def __init__(self, model: str = "gemini-1.5-flash"):
        super().__init__()
        self._model = genai.GenerativeModel(model)
        self._chat = None

    async def chat(self, chat_ctx: llm.ChatContext) -> llm.ChatStream:
        messages = []
        for msg in chat_ctx.messages:
            role = "user" if msg.role == llm.ChatRole.USER else "model"
            messages.append({"role": role, "parts": [msg.content]})

        if not self._chat:
            self._chat = self._model.start_chat(history=messages[:-1])

        response = await self._chat.send_message_async(messages[-1]["parts"][0])
        return GeminiChatStream(response)

class GeminiChatStream(llm.ChatStream):
    def __init__(self, response):
        self._response = response
        self._done = False

    async def __anext__(self) -> llm.ChatChunk:
        if self._done:
            raise StopAsyncIteration
        self._done = True
        return llm.ChatChunk(
            choices=[llm.Choice(delta=llm.ChoiceDelta(content=self._response.text, role="assistant"))]
        )

    def __aiter__(self):
        return self
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/ai/
git commit -m "feat: add Gemini LLM integration and prompt templates"
```

---

### Task 3: Tutor Agent Implementation

**Files:**
- Create: `backend/app/ai/tutor_agent.py`
- Create: `backend/app/ai/cefr_assessor.py`

- [ ] **Step 1: Implement CEFR assessor**

```python
# backend/app/ai/cefr_assessor.py
CEFR_LEVELS = ["A0", "A1", "A2", "B1", "B2", "C1"]

CEFR_TOPICS = {
    "A0": ["greetings", "numbers_1_10", "basic_colors", "family_members", "days_of_week"],
    "A1": ["self_introduction", "daily_routines", "food_drink", "directions", "weather",
           "numbers_to_100", "time_telling", "basic_adjectives", "present_tense"],
    "A2": ["past_experiences", "future_plans", "shopping", "health", "travel",
           "comparisons", "past_tense", "hobbies_interests", "describing_people"],
    "B1": ["opinions_arguments", "work_career", "education", "media_news",
           "conditional_sentences", "passive_voice", "relative_clauses", "formal_informal_register"],
    "B2": ["abstract_topics", "cultural_discussions", "business_communication",
           "academic_writing", "subjunctive_mood", "complex_grammar", "idioms_expressions"],
    "C1": ["nuanced_arguments", "professional_presentations", "literary_analysis",
           "advanced_grammar", "register_switching", "research_writing", "debate_skills"],
}

def get_next_level(current: str) -> str | None:
    idx = CEFR_LEVELS.index(current)
    if idx < len(CEFR_LEVELS) - 1:
        return CEFR_LEVELS[idx + 1]
    return None

def get_topics_for_level(level: str) -> list[str]:
    return CEFR_TOPICS.get(level, [])

def get_reinforcement_topics(current_level: str) -> list[str]:
    """Get topics from all levels below current for reinforcement."""
    idx = CEFR_LEVELS.index(current_level)
    topics = []
    for i in range(idx):
        topics.extend(CEFR_TOPICS.get(CEFR_LEVELS[i], []))
    return topics

ASSESSMENT_PROMPT = """Based on the conversation so far, assess the student's proficiency.
Rate each skill from 0-100:
- Vocabulary: appropriate word choice and range
- Grammar: accuracy and complexity of structures
- Fluency: natural flow and coherence
- Comprehension: understanding of questions and context

Then determine the CEFR level: A0, A1, A2, B1, B2, or C1.

Respond in JSON format:
{{"vocabulary": <score>, "grammar": <score>, "fluency": <score>, "comprehension": <score>, "cefr_level": "<level>", "reasoning": "<brief explanation>"}}
"""
```

- [ ] **Step 2: Implement tutor agent**

```python
# backend/app/ai/tutor_agent.py
import json
import httpx
from livekit.agents import JobContext
from livekit.agents.voice_assistant import VoiceAssistant
from app.ai.gemini_plugin import GeminiLLM
from app.ai.prompt_templates import TUTOR_SYSTEM_PROMPT, PRACTICE_SYSTEM_PROMPT, get_native_language_rule
from app.ai.cefr_assessor import get_topics_for_level, get_reinforcement_topics
from app.config import settings

async def fetch_user_context(session_id: str) -> dict:
    """Fetch user and session context from the backend API."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"http://localhost:8000/api/internal/session-context/{session_id}")
        if resp.status_code == 200:
            return resp.json()
    return {}

async def create_tutor_agent(ctx: JobContext) -> VoiceAssistant:
    metadata = json.loads(ctx.room.metadata or "{}")
    session_id = metadata.get("session_id", "")
    mode = metadata.get("mode", "learning")

    context = await fetch_user_context(session_id)

    cefr_level = context.get("cefr_level", "A1")
    topics = get_topics_for_level(cefr_level)
    reinforcement = get_reinforcement_topics(cefr_level)

    if mode == "practice":
        system_prompt = PRACTICE_SYSTEM_PROMPT.format(
            target_language=context.get("target_language", "English"),
            student_name=context.get("student_name", "Student"),
            cefr_level=cefr_level,
            topics_covered=", ".join(context.get("topics_covered", [])),
        )
    else:
        system_prompt = TUTOR_SYSTEM_PROMPT.format(
            target_language=context.get("target_language", "English"),
            native_language=context.get("native_language", "English"),
            student_name=context.get("student_name", "Student"),
            cefr_level=cefr_level,
            progress_percent=context.get("progress_percent", 0),
            teaching_style=context.get("teaching_style", "friendly_structured"),
            topics_covered=", ".join(context.get("topics_covered", [])),
            weaknesses=", ".join(context.get("weaknesses", [])),
            use_native_language_rule=get_native_language_rule(cefr_level),
        )

    llm_instance = GeminiLLM()

    assistant = VoiceAssistant(
        vad=None,  # Will use default VAD
        stt=None,  # Configured via plugins
        llm=llm_instance,
        tts=None,  # Configured via plugins
        chat_ctx=llm.ChatContext().append(role="system", text=system_prompt),
    )

    return assistant
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/ai/
git commit -m "feat: implement tutor agent with CEFR-aware teaching logic"
```

---

### Task 4: Coordinator Agent (Onboarding & Support)

**Files:**
- Create: `backend/app/ai/coordinator_agent.py`
- Create: `backend/app/services/onboarding_service.py`
- Create: `backend/app/services/geoip_service.py`

- [ ] **Step 1: Implement GeoIP service**

```python
# backend/app/services/geoip_service.py
import httpx

async def detect_locale_from_ip(ip: str) -> dict:
    """Detect country/language from IP address."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://ip-api.com/json/{ip}?fields=country,countryCode,city,lat,lon")
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "country": data.get("country", ""),
                    "country_code": data.get("countryCode", "").upper(),
                    "city": data.get("city", ""),
                }
    except Exception:
        pass
    return {"country": "", "country_code": "", "city": ""}

COUNTRY_TO_LOCALE = {
    "GB": "en-GB", "US": "en-US", "AU": "en-AU",
    "ES": "es-ES", "MX": "es-MX", "AR": "es-AR",
    "FR": "fr-FR", "CA": "fr-CA",
    "DE": "de-DE", "AT": "de-AT",
    "IT": "it-IT",
    "PT": "pt-PT", "BR": "pt-BR",
    "JP": "ja-JP",
    "CN": "zh-CN", "TW": "zh-TW",
    "KR": "ko-KR",
    "RU": "ru-RU",
    "IN": "hi-IN",
    "SA": "ar-SA",
}

def build_locale(phone_language: str, country_code: str) -> str:
    """Build locale from phone language and GeoIP country code."""
    # Try exact match: phone_lang + country
    candidate = f"{phone_language}-{country_code}"
    if candidate in COUNTRY_TO_LOCALE.values():
        return candidate

    # If country matches any locale for this language, use it
    for cc, locale in COUNTRY_TO_LOCALE.items():
        if locale.startswith(phone_language) and cc == country_code:
            return locale

    # Fallback: use default locale for the language (will be resolved by DB)
    return f"{phone_language}-{country_code}"
```

- [ ] **Step 2: Implement onboarding service**

```python
# backend/app/services/onboarding_service.py
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.language import Language
from app.models.persona import Persona
from app.models.user import User, UserLanguage, CefrLevelHistory

async def detect_user_language(db: AsyncSession, phone_language: str, country_code: str) -> Language | None:
    from app.services.geoip_service import build_locale
    locale = build_locale(phone_language, country_code)

    # Try exact locale match
    result = await db.execute(select(Language).where(Language.locale == locale, Language.is_active.is_(True)))
    lang = result.scalar_one_or_none()
    if lang:
        return lang

    # Try default for this language
    result = await db.execute(
        select(Language).where(
            Language.name.ilike(f"%{phone_language}%"),
            Language.is_default.is_(True),
            Language.is_active.is_(True),
        )
    )
    lang = result.scalar_one_or_none()
    if lang:
        return lang

    # Fall back to fallback language
    return await get_fallback_language(db)

async def get_fallback_language(db: AsyncSession) -> Language | None:
    result = await db.execute(select(Language).where(Language.is_fallback.is_(True), Language.is_active.is_(True)))
    return result.scalar_one_or_none()

async def get_coordinator_for_language(db: AsyncSession, language_id: UUID) -> Persona | None:
    result = await db.execute(
        select(Persona).where(
            Persona.language_id == language_id,
            Persona.type == "coordinator",
            Persona.is_active.is_(True),
            Persona.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()

async def get_teachers_for_language(db: AsyncSession, language_id: UUID) -> list[Persona]:
    result = await db.execute(
        select(Persona).where(
            Persona.language_id == language_id,
            Persona.type == "teacher",
            Persona.is_active.is_(True),
            Persona.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())

async def complete_onboarding(db: AsyncSession, user_id: UUID, native_language_id: UUID,
                                target_language_id: UUID, teacher_id: UUID,
                                teaching_style: str, cefr_level: str) -> UserLanguage:
    # Update user's native language
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    user.native_language_id = native_language_id

    # Create user-language record
    ul = UserLanguage(
        user_id=user_id,
        language_id=target_language_id,
        teacher_persona_id=teacher_id,
        teaching_style=teaching_style,
        current_cefr_level=cefr_level,
    )
    db.add(ul)
    await db.flush()

    # Create initial CEFR history
    history = CefrLevelHistory(
        user_language_id=ul.id,
        cefr_level=cefr_level,
        status="in_progress",
    )
    db.add(history)
    await db.flush()

    return ul
```

- [ ] **Step 3: Implement coordinator agent**

```python
# backend/app/ai/coordinator_agent.py
import json
from livekit.agents import JobContext
from livekit.agents.voice_assistant import VoiceAssistant
from app.ai.gemini_plugin import GeminiLLM
from app.ai.prompt_templates import COORDINATOR_SYSTEM_PROMPT, SUPPORT_SYSTEM_PROMPT

async def create_coordinator_agent(ctx: JobContext) -> VoiceAssistant:
    metadata = json.loads(ctx.room.metadata or "{}")
    mode = metadata.get("mode", "onboarding")

    if mode == "support":
        system_prompt = SUPPORT_SYSTEM_PROMPT.format(
            student_name=metadata.get("student_name", "User"),
            plan_name=metadata.get("plan_name", "Free"),
            languages=metadata.get("languages", ""),
        )
    else:
        system_prompt = COORDINATOR_SYSTEM_PROMPT.format(
            native_language=metadata.get("native_language", "English"),
            locale=metadata.get("locale", "en-GB"),
            available_languages=metadata.get("available_languages", ""),
            fallback_language=metadata.get("fallback_language", "English"),
        )

    llm_instance = GeminiLLM()

    assistant = VoiceAssistant(
        llm=llm_instance,
        chat_ctx=None,  # Will be initialized with system prompt
    )

    return assistant
```

- [ ] **Step 4: Add onboarding API endpoint**

```python
# Add to backend/app/api/mobile/sessions.py
from app.services import onboarding_service
from app.services.geoip_service import detect_locale_from_ip
from pydantic import BaseModel

class OnboardingStartRequest(BaseModel):
    phone_language: str  # e.g., "en", "es"

class OnboardingCompleteRequest(BaseModel):
    target_language_id: str
    teacher_id: str
    teaching_style: str
    cefr_level: str
    name: str
    date_of_birth: str | None = None
    avatar_id: str | None = None

@router.post("/onboarding/start")
async def start_onboarding(data: OnboardingStartRequest, request: Request,
                           user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from fastapi import Request
    client_ip = request.client.host
    geo = await detect_locale_from_ip(client_ip)
    detected_lang = await onboarding_service.detect_user_language(db, data.phone_language, geo.get("country_code", ""))

    if not detected_lang:
        detected_lang = await onboarding_service.get_fallback_language(db)

    coordinator = await onboarding_service.get_coordinator_for_language(db, detected_lang.id) if detected_lang else None

    # Create LiveKit room for onboarding
    # Room name includes user ID for tracking
    room_name = f"onboarding-{user.id}"

    return {
        "room_name": room_name,
        "detected_language": {"id": str(detected_lang.id), "name": detected_lang.name, "locale": detected_lang.locale} if detected_lang else None,
        "coordinator": {"id": str(coordinator.id), "name": coordinator.name, "image_url": coordinator.image_url} if coordinator else None,
        "geo": geo,
    }

@router.post("/onboarding/complete")
async def complete_onboarding_endpoint(data: OnboardingCompleteRequest,
                                        user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from uuid import UUID as PyUUID
    # Update user profile
    user.name = data.name
    if data.date_of_birth:
        from datetime import date
        user.date_of_birth = date.fromisoformat(data.date_of_birth)
    if data.avatar_id:
        user.avatar_id = PyUUID(data.avatar_id)

    ul = await onboarding_service.complete_onboarding(
        db, user.id,
        native_language_id=user.native_language_id or PyUUID(data.target_language_id),
        target_language_id=PyUUID(data.target_language_id),
        teacher_id=PyUUID(data.teacher_id),
        teaching_style=data.teaching_style,
        cefr_level=data.cefr_level,
    )
    return {"user_language_id": str(ul.id), "cefr_level": ul.current_cefr_level}
```

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat: add coordinator agent, onboarding service, GeoIP detection"
```

---

### Task 5: LiveKit Room Management & Token Generation

**Files:**
- Create: `backend/app/services/livekit_service.py`
- Modify: `backend/app/api/mobile/sessions.py`

- [ ] **Step 1: Implement LiveKit service**

```python
# backend/app/services/livekit_service.py
from livekit import api
from app.config import settings

async def create_room(room_name: str, metadata: str = "") -> dict:
    lk_api = api.LiveKitAPI(
        settings.livekit_url if hasattr(settings, 'livekit_url') else "http://localhost:7880",
        settings.livekit_api_key if hasattr(settings, 'livekit_api_key') else "devkey",
        settings.livekit_api_secret if hasattr(settings, 'livekit_api_secret') else "secret",
    )
    room = await lk_api.room.create_room(api.CreateRoomRequest(
        name=room_name,
        metadata=metadata,
    ))
    return {"name": room.name, "sid": room.sid}

def generate_token(room_name: str, participant_name: str, participant_identity: str) -> str:
    token = api.AccessToken(
        settings.livekit_api_key if hasattr(settings, 'livekit_api_key') else "devkey",
        settings.livekit_api_secret if hasattr(settings, 'livekit_api_secret') else "secret",
    )
    token.with_identity(participant_identity)
    token.with_name(participant_name)
    token.with_grants(api.VideoGrants(
        room_join=True,
        room=room_name,
    ))
    return token.to_jwt()
```

- [ ] **Step 2: Add session start/end endpoints**

```python
# Add to backend/app/api/mobile/sessions.py
from app.services import livekit_service, usage_service
import json

class StartSessionRequest(BaseModel):
    session_type: str  # voice_call, video_call, text_chat
    session_mode: str  # learning, practice, support
    language_id: str | None = None

@router.post("/start")
async def start_session(data: StartSessionRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Check usage limits
    feature = data.session_type.replace("_call", "_call")
    if data.session_type in ("voice_call", "video_call"):
        limit_check = await usage_service.check_limit(db, user.id, data.session_type)
        if not limit_check["allowed"]:
            raise HTTPException(status_code=403, detail="Daily limit reached")

    # Get user language context
    from app.models.user import UserLanguage
    ul = None
    if data.language_id:
        from uuid import UUID as PyUUID
        result = await db.execute(
            select(UserLanguage).where(UserLanguage.user_id == user.id, UserLanguage.language_id == PyUUID(data.language_id))
        )
        ul = result.scalar_one_or_none()

    # Get persona
    persona_id = ul.teacher_persona_id if ul else None
    if data.session_mode == "support" or data.session_mode == "onboarding":
        from app.services.onboarding_service import get_coordinator_for_language
        if ul:
            coord = await get_coordinator_for_language(db, ul.language_id)
            persona_id = coord.id if coord else persona_id

    if not persona_id:
        raise HTTPException(status_code=400, detail="No persona available")

    # Create session record
    session = await session_service.create_session(
        db, user.id, persona_id, data.session_type, data.session_mode,
        user_language_id=ul.id if ul else None,
        cefr_level=ul.current_cefr_level if ul else None,
    )

    result_data = {"session_id": str(session.id)}

    # Create LiveKit room for voice/video calls
    if data.session_type in ("voice_call", "video_call"):
        room_name = f"{data.session_mode}-{session.id}"
        metadata = json.dumps({
            "session_id": str(session.id),
            "mode": data.session_mode,
            "student_name": user.name,
            "cefr_level": ul.current_cefr_level if ul else "A0",
        })
        room = await livekit_service.create_room(room_name, metadata)
        token = livekit_service.generate_token(room_name, user.name, str(user.id))
        result_data["livekit_token"] = token
        result_data["room_name"] = room_name

        session.livekit_room_name = room_name
        await db.flush()

    return result_data

class EndSessionRequest(BaseModel):
    duration_seconds: int

@router.post("/{session_id}/end")
async def end_session(session_id: UUID, data: EndSessionRequest,
                      user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    session = await session_service.end_session(db, session_id, data.duration_seconds)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Record usage
    minutes = data.duration_seconds / 60
    if session.session_type in ("voice_call", "video_call"):
        await usage_service.record_usage(db, user.id, session.session_type, minutes)

    return {"status": "ended", "duration": data.duration_seconds}
```

- [ ] **Step 3: Add usage check endpoint**

```python
# Add to backend/app/api/mobile/sessions.py
@router.get("/usage/check")
async def check_usage(feature: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await usage_service.check_limit(db, user.id, feature)
```

- [ ] **Step 4: Commit**

```bash
git add backend/
git commit -m "feat: add LiveKit room management, session start/end, usage checking"
```

---

### Task 6: Internal API for Agent Context

**Files:**
- Create: `backend/app/api/internal.py`

- [ ] **Step 1: Create internal API (agent-to-backend communication)**

```python
# backend/app/api/internal.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.database import get_db
from app.models.session import Session
from app.models.user import User, UserLanguage, CefrLevelHistory
from app.models.persona import Persona
from app.models.language import Language
from app.models.subscription import UserSubscription
from app.models.plan import Plan

router = APIRouter(prefix="/internal", tags=["internal"])

@router.get("/session-context/{session_id}")
async def get_session_context(session_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        return {}

    user_result = await db.execute(select(User).where(User.id == session.user_id))
    user = user_result.scalar_one()

    context = {
        "student_name": user.name,
        "session_type": session.session_type,
        "session_mode": session.session_mode,
    }

    # Get native language
    if user.native_language_id:
        nl = await db.execute(select(Language).where(Language.id == user.native_language_id))
        native_lang = nl.scalar_one_or_none()
        if native_lang:
            context["native_language"] = native_lang.name

    # Get target language and CEFR info
    if session.user_language_id:
        ul = await db.execute(select(UserLanguage).where(UserLanguage.id == session.user_language_id))
        user_lang = ul.scalar_one_or_none()
        if user_lang:
            context["cefr_level"] = user_lang.current_cefr_level
            context["progress_percent"] = user_lang.cefr_progress_percent
            context["teaching_style"] = user_lang.teaching_style

            tl = await db.execute(select(Language).where(Language.id == user_lang.language_id))
            target_lang = tl.scalar_one_or_none()
            if target_lang:
                context["target_language"] = target_lang.name

            # Get covered topics from CEFR history
            ch = await db.execute(
                select(CefrLevelHistory).where(
                    CefrLevelHistory.user_language_id == user_lang.id,
                    CefrLevelHistory.cefr_level == user_lang.current_cefr_level,
                )
            )
            cefr_history = ch.scalar_one_or_none()
            if cefr_history and cefr_history.topics_covered:
                context["topics_covered"] = cefr_history.topics_covered
            else:
                context["topics_covered"] = []

    # Get plan info
    sub = await db.execute(
        select(UserSubscription).where(UserSubscription.user_id == user.id, UserSubscription.is_active.is_(True))
    )
    subscription = sub.scalar_one_or_none()
    if subscription:
        plan_result = await db.execute(select(Plan).where(Plan.id == subscription.plan_id))
        plan = plan_result.scalar_one_or_none()
        if plan:
            context["plan_name"] = plan.name

    return context

@router.post("/session/{session_id}/transcript")
async def add_transcript(session_id: UUID, speaker: str, content: str, offset_ms: int = 0, db: AsyncSession = Depends(get_db)):
    from app.models.session import SessionTranscript
    transcript = SessionTranscript(session_id=session_id, speaker=speaker, content=content, timestamp_offset_ms=offset_ms)
    db.add(transcript)
    await db.flush()
    return {"id": str(transcript.id)}

@router.post("/session/{session_id}/update-cefr")
async def update_cefr(session_id: UUID, new_level: str, progress: float, topics: list[str] | None = None, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session or not session.user_language_id:
        return {"error": "session not found"}

    ul = await db.execute(select(UserLanguage).where(UserLanguage.id == session.user_language_id))
    user_lang = ul.scalar_one()
    user_lang.current_cefr_level = new_level
    user_lang.cefr_progress_percent = progress
    await db.flush()
    return {"status": "updated"}
```

- [ ] **Step 2: Register internal router in main.py**

Add to `backend/app/main.py`:
```python
from app.api.internal import router as internal_router
app.include_router(internal_router, prefix="/api")
```

- [ ] **Step 3: Commit**

```bash
git add backend/
git commit -m "feat: add internal API for agent-to-backend communication"
```

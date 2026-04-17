# Project Blueprint: Virtual AI Language Tutor

## 1. Core Architecture
- Backend: FastAPI (Python)
- Frontend: Flutter (Mobile-first)
- WebRTC Transport: LiveKit (Self-Hosted)
- Logic/Brain: Gemini 1.5 Flash 

## 2. The $9.99/mo High-Density Strategy (CRITICAL)
- We MUST use `LivePortrait` (TensorRT optimized) via the `livekit-plugins-avatartalk` plugin.
- We MUST use `Fish Speech S2` for local TTS.
- We must usee `Deepgram` for local STT.
- API-based video services like LemonSlice or HeyGen are strictly forbidden due to cost.

## 3. Application Logic
- English, all European languages, Japanese, Mandarin, Russian, Korean, Hindi, Tamil, Bengali, and Arabic should be there as languages [DONE]
- Any language can be Native Language and user may learn other languages [DONE]
- More languages may be added as the pplication will scale in future [DONE]
- For user authentication, Email/password, Social login, and Mobile OTP will be available for user to choose any of the option [DONE]
- The application will be a 'Freemium' service with usage limit for different subscription level [DONE]
- For users user free tier, unlimited voice and Text-based learning will be available [DONE]
- Users under paid plans will have two tiers. $4.99 per month and $9.99 per month [DONE]
- Users in $4.99/mo tier will have everything from free tier + 15 min video call [DONE]
- Users in $9.99/mo tier will have everything unlimited [DONE]
- Text based input/output will be shown only when it's necessary to use text instead of audio/video [DONE]
- All the audio/video (conversations/teacing) will always have transcript/subtitle [DONE]
- The initial CEFR level assessment for a user will be through a Placement test at starting a new anguage learning (automated quiz/conversation) [DONE]
- The initial assessment will be conversational through video call, regardless the subscription tier [DONE]
- A User may learn multiple languages parallelly, and each language should follow it's own independent learning path
- Admin uploads avatar images, configures per language [DONE]
- Each language has 1 coordinator (female) + N teachers (configurable) [DONE]
- Coordinator role:
-- Multilingual — speaks all supported languages [DONE]
-- Handles onboarding, language selection, and presumably assessment routing [DONE]
-- User doesn't choose coordinator — it's auto-assigned [DONE]
- Teacher role:
-- User picks their preferred teacher per language [DONE]
-- Teaches in the target language (with native language support below B2) [DONE]
- Coordinator access is tiered
-- Free: onboarding + language selection + initial CEFR assessment only [DONE]
-- $4.99/mo: Everything from free tier + 30 min/month cumulative coordinator time [DONE]
-- $9.99/mo: Everything from free tier + 4 hrs/month cumulative coordinator time [DONE]
-- No rollover of unused time [DONE]
-- Coordinator scope: strictly operational — settings, support, help. Never teaches [DONE]
- AI dynamically chooses topics based on student's weaknesses and interests as lession structure. It will be fully adaptive within CEFR level boundaries. No content leaking from the next level, and emphasis on making it enjoyable [DONE]


## 4. Onboarding Language Detection Flow
- Detect phone language + GeoIP
- If phone language is English → prioritize GeoIP to guess native language
- Coordinator greets in the auto-detected language, asks for confirmation
- No response → assume user doesn't know that language → fallback to English
- In both cases, ask: "Do you want to use [detected language] or select a different one?"
- User can change later in settings

## 5. Session Flow & State Changes
- **Video Call Mode:** Active when the user is conversing.
- **Writing Mode:** Video stream must be killed/paused immediately to save GPU VRAM. The UI shifts to a text-input field.
- **Idle Timeout:** If no audio is detected for 60 seconds, the video pipeline must pause.

## 6. CEFR Progression
- The AI must use the user's Native Language for explanations if they are below B2 level. 
- Transcripts must be analyzed post-session to update the `skills_mastery`
- Session will store timestamp, duration, CEFR level at time, language, transcript, topics covered, performance metrics, detailed skill breakdown (reading/writing/listening/speaking), vocabulary tracked
- The CEFR progression flow will be:
-- Teacher covers all topics for current CEFR level
-- Teacher initiates assessment conversation
-- Pass → promote to next level
-- Fail → friendly encouragement, then re-teach with emphasis on weaknesses + light review of other topics
-- Teacher re-initiates assessment after sufficient re-learning
-- Student can also request assessment at any time during re-learning
-- Cycle repeats until they pass

## 7. Admin Dashboard
- Admin & ACL management — super admin configures roles/permissions, role-based access for all admin functions
- Avatar management — upload images, assign to languages as coordinator/teacher
- Language management — add/remove languages, configure teachers per language
- User & subscription management — view/manage users, plans, billing
- Session analytics — usage stats, popular languages, etc.
- Configurable role system — super admin defines what each admin role can access

## 8. Payment Processor
- Both Stripe (for web) + in-app purchases  - Apple/Google (for mobile)

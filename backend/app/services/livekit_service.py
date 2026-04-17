from livekit.api import AccessToken, VideoGrants

from app.config import settings


async def create_room_and_token(
    room_name: str,
    participant_name: str,
    session_id: str,
) -> str:
    token = AccessToken(
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )
    token.with_identity(participant_name)
    token.with_name(participant_name)
    token.with_grants(
        VideoGrants(
            room_join=True,
            room=room_name,
        )
    )
    return token.to_jwt()

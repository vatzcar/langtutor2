from pydantic import BaseModel


class SocialLoginRequest(BaseModel):
    provider: str
    id_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


class AdminLoginRequest(BaseModel):
    email: str
    password: str

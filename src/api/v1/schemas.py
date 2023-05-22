from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserSchema(BaseModel):
    name: str = None
    email: EmailStr
    email_verified_at: datetime | None = Field(alias="emailVerified")
    image: str = None


class AccountScheme(BaseModel):
    user_id: str = Field(alias="userId")
    provider_name: str = Field(alias="type")
    provider_account_id: str = Field(alias="providerAccountId")
    refresh_token: Optional[str] = None
    access_token: Optional[str] = None
    access_token_expires: Optional[datetime] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    # TODO update on update
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    expires_at: Optional[int] = None
    token_type: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None
    session_state: Optional[str] = None

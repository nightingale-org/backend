from __future__ import annotations

from datetime import datetime
from typing import Optional

import humps
from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field, validator

from src.utils.pydantic_utils import AllOptional


class UserInputSchema(BaseModel):
    username: str | None
    email: EmailStr
    email_verified_at: datetime | None
    image: str = None

    class Config:
        alias_generator = humps.camelize


class UserUpdateSchema(UserInputSchema, metaclass=AllOptional):
    pass


class ExistsResponseSchema(BaseModel):
    exists: bool


class UserOutputSchema(BaseModel):
    id: str
    username: str | None
    email: EmailStr
    email_verified: datetime | None
    image: str = None
    created_at: datetime | None

    class Config:
        alias_generator = humps.camelize
        orm_mode = True

    @validator("id", pre=True)
    def convert_object_id(cls, value: ObjectId) -> str:
        return str(value)


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

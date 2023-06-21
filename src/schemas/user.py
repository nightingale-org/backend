from __future__ import annotations

from datetime import datetime

import humps

from bson import ObjectId
from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field
from pydantic import validator


class UserInputSchema(BaseModel):
    username: str | None
    email: EmailStr
    email_verified_at: datetime | None
    image: str | None = None

    class Config:
        alias_generator = humps.camelize


class CheckUsernameAvailabilitySchema(BaseModel):
    username: str


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
    refresh_token: str | None = None
    access_token: str | None = None
    access_token_expires: datetime | None = None
    created_at: datetime | None = Field(default_factory=datetime.utcnow)
    # TODO update on update
    updated_at: datetime | None = Field(default_factory=datetime.utcnow)
    expires_at: int | None = None
    token_type: str | None = None
    scope: str | None = None
    id_token: str | None = None
    session_state: str | None = None

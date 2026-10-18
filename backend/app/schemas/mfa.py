from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MfaStatus(BaseModel):
    enabled: bool
    recovery_codes_remaining: int
    # True when the organization requires it of this person and it isn't on yet.
    setup_required: bool


class MfaSetup(BaseModel):
    """Shown once while setting up: the key and the link the QR code encodes."""

    secret: str
    otpauth_uri: str


class MfaCode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=64)


class MfaProof(BaseModel):
    """Turning it off, or making new recovery codes, needs both."""

    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=64)


class RecoveryCodes(BaseModel):
    recovery_codes: list[str]


class MfaChallenge(BaseModel):
    """What a correct password gets, for an account with two-step sign-in: no
    session yet, only a short-lived ticket to present with a code."""

    mfa_required: Literal[True] = True
    ticket: str


class MfaLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket: str = Field(min_length=1, max_length=400)
    code: str = Field(min_length=1, max_length=64)


class SecuritySettingsRead(BaseModel):
    require_mfa_for_admins: bool
    # Active administrators who haven't set it up -- the people the rule would catch.
    admins_without_mfa: int


class SecuritySettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    require_mfa_for_admins: bool

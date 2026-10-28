"""Explicit depiction evidence; a normalized image URL grants no display rights."""

from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PermittedImage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["photo", "illustration"]
    url: str
    attribution: str = Field(min_length=1, max_length=500)
    provenance: str = Field(min_length=1, max_length=2000)
    permission_reference: str = Field(min_length=1, max_length=500)
    identity_reference: str = Field(min_length=1, max_length=500)
    source_listing_id: str = Field(min_length=1)
    depicts_exact_watch: Literal[True]

    @field_validator("url")
    @classmethod
    def public_image_url(cls, value: str) -> str:
        parts = urlsplit(value)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
            or any(c.isspace() for c in value)
        ):
            raise ValueError("Image requires an unsigned HTTPS URL without credentials or query")
        return value

    @field_validator("attribution", "provenance", "permission_reference", "identity_reference")
    @classmethod
    def meaningful_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Image evidence must be nonblank")
        return value.strip()

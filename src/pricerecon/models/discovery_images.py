"""Explicit depiction evidence; a normalized image URL grants no display rights."""

from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter, field_validator


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
        # urllib defers port validation and differs from browser URL parsing.
        # Validate both grammars before retaining the original display URL.
        TypeAdapter(HttpUrl).validate_python(value)
        parts = urlsplit(value)
        _ = parts.port
        if (
            parts.scheme != "https"
            or not parts.hostname
            or "\\" in value
            or any(ord(c) < 32 or ord(c) == 127 for c in value)
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

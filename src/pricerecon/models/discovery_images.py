"""Explicit depiction evidence; a normalized image URL grants no display rights."""

import re
from typing import Literal
from urllib.parse import parse_qsl, urlsplit

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


class RemoteReferenceImage(BaseModel):
    """User-approved remote display; neither a licence nor exact configuration evidence."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["remote_reference"]
    url: str
    attribution: str = Field(min_length=1, max_length=500)
    provenance: str = Field(min_length=1, max_length=2000)
    source_context_url: str
    configuration_note: str = Field(min_length=1, max_length=2000)
    source_listing_id: str = Field(min_length=1)
    depicts_exact_watch: Literal[False]

    @field_validator("url", "source_context_url")
    @classmethod
    def safe_remote_url(cls, value: str) -> str:
        if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError("Whitespace in remote URL")
        parts = urlsplit(value)
        # Only explicit public image transformations and page variant selections.
        patterns = {
            "v": r"[0-9]{1,20}",
            "width": r"[1-9][0-9]{0,4}",
            "format": r"(?:[1-9][0-9]{0,4}w|webp|jpg|jpeg|png|avif)",
            "variant": r"[0-9]{1,30}",
        }
        pairs = parse_qsl(parts.query, keep_blank_values=True)
        if parts.query and (
            not pairs
            or len({k for k, _ in pairs}) != len(pairs)
            or any(k not in patterns or not re.fullmatch(patterns[k], v) for k, v in pairs)
        ):
            raise ValueError("Only public image transformations or variant queries allowed")
        PermittedImage.public_image_url(value.split("?", 1)[0])
        if parts.fragment:
            raise ValueError("Fragments are not image evidence")
        return value

    @field_validator("attribution", "provenance", "configuration_note")
    @classmethod
    def meaningful_text(cls, value: str) -> str:
        return PermittedImage.meaningful_text(value)

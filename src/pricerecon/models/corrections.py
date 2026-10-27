"""Human identity intent is distinct from acquired merchant evidence."""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pricerecon.models.qualification import Configuration, FieldEvidence, IdentityField


class CorrectionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CorrectionWrite(CorrectionModel):
    expected_revision: int = Field(ge=0, strict=True)
    capture_id: str = Field(min_length=1, max_length=250)
    configuration_revision: int = Field(gt=0, strict=True)
    observed_configuration_id: str | None = Field(default=None, min_length=1, max_length=250)
    field: IdentityField
    value: str = Field(min_length=1, max_length=500)
    state: Literal["corrected", "disputed"] = "corrected"
    actor: str = Field(min_length=1, max_length=250)
    rationale: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_value(self) -> "CorrectionWrite":
        choices = {
            "product_kind": {"complete_watch", "accessory", "component"},
            "date_display": {"date", "no_date"},
        }
        if self.field in choices and self.value not in choices[self.field]:
            raise ValueError("Unsupported identity value")
        if self.field == "case_width_mm":
            try:
                number = Decimal(self.value)
            except InvalidOperation as exc:
                raise ValueError("Enter a positive finite case width") from exc
            if not number.is_finite() or number <= 0 or abs(number.adjusted()) > 100:
                raise ValueError("Enter a positive finite case width")
        return self


class CorrectionEntry(CorrectionWrite):
    id: str
    revision: int
    recorded_at: datetime
    original_value: str | None
    previous_correction_id: str | None = None


class CorrectionHistory(CorrectionModel):
    candidate_id: str
    configuration_id: str
    revision: int = 0
    state: Literal["uncorrected", "corrected", "disputed"] = "uncorrected"
    requalification: Literal["not_required", "required", "supported_by_fresh_evidence"] = (
        "not_required"
    )
    values: dict[str, str]
    original_configuration: Configuration
    original_evidence: list[FieldEvidence]
    lineage: list[CorrectionEntry] = Field(default_factory=list)
    needs: list[str] = Field(default_factory=list)

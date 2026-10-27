"""Exact-configuration intent and versioned target decisions; no acquisition settings."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from pricerecon.models.costs import Money, Token


class TrackingModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TrackingNotifications(TrackingModel):
    # Endpoints/credentials remain with the existing notification owner.
    channels: list[Literal["webhook", "telegram", "discord"]] = Field(default_factory=list)


class TrackingCreate(TrackingModel):
    candidate_id: Token
    capture_id: Token
    configuration_id: Token
    configuration_revision: int = Field(gt=0)
    target_gbp: Annotated[Money, Field(gt=0)]
    notifications: TrackingNotifications = Field(default_factory=TrackingNotifications)


class TrackingUpdate(TrackingModel):
    expected_revision: int = Field(gt=0)
    target_gbp: Annotated[Money, Field(gt=0)]
    notifications: TrackingNotifications = Field(default_factory=TrackingNotifications)


class DeliveryResolution(TrackingModel):
    expected_revision: int = Field(gt=0)
    channel: Literal["webhook", "telegram", "discord"]
    resolution: Literal["record_sent", "abandon"]
    # An explicit operator assertion; the server cannot prove remote delivery
    # or that an external process has stopped. This action never retries a send.
    confirm_no_send_in_flight: Literal[True]


class TrackingAssessment(TrackingModel):
    state: Literal["eligible", "above_target", "withheld"] = "withheld"
    reasons: list[str] = Field(default_factory=lambda: ["policy_required"])
    assessed_at: datetime | None = None
    valid_until: datetime | None = None
    policy_version: str | None = None
    policy_fingerprint: str | None = None
    preference_revision: int | None = None
    intent_revision: int | None = None
    capture_id: str | None = None
    offer_id: str | None = None
    offer_revision: int | None = None
    binding_revision: int | None = None
    configuration_revision: int | None = None
    scenario_id: str | None = None
    scenario_revision: int | None = None
    delivered_gbp: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)


class ExactTracking(TrackingCreate):
    id: int
    revision: int = 1
    created_at: datetime
    updated_at: datetime
    collection_state: Literal["staged"] = "staged"
    assessment: TrackingAssessment = Field(default_factory=TrackingAssessment)
    invalidation_revision: int = 0
    invalidation_reason: str | None = None


class TrackingList(TrackingModel):
    items: list[ExactTracking]


class TrackingPolicy(TrackingModel):
    """Explicit programmatic policy, never supplied by HTTP intent writes.

    Values are execution prerequisites. There is deliberately no production
    freshness, condition, quantity, destination or payment default.
    """

    version: Token
    max_evidence_age_seconds: int = Field(gt=0)
    allowed_conditions: list[Literal["new", "used", "refurbished"]] = Field(min_length=1)
    quantity: int = Field(gt=0)
    destination_nation: Token
    destination_region: Token
    payment_method: Token


class TrackingDelivery(TrackingModel):
    event_id: int
    tracking_id: int
    intent_revision: int
    offer_key: str
    delivered_gbp: Decimal = Field(ge=0, allow_inf_nan=False)
    reason: str
    status: str
    channels: dict[str, str]
    guarantee: str = "External send/ack crashes are ambiguous; no exactly-once guarantee."


class TrackingDeliveries(TrackingModel):
    items: list[TrackingDelivery]


class OfferTargetState(TrackingModel):
    """Decision state only, not ticket06's observation/history projection."""

    intent_revision: int
    policy_version: str
    policy_fingerprint: str
    previous_gbp: Decimal = Field(ge=0, allow_inf_nan=False)
    notified_low_gbp: Decimal = Field(ge=0, allow_inf_nan=False)
    crossing_epoch: int = 0
    evidence_at: datetime


class TargetEvent(TrackingDelivery):
    assessment: TrackingAssessment
    listing: dict[str, str | int | None]
    notification_channels: list[Literal["webhook", "telegram", "discord"]]
    invalidation_revision: int

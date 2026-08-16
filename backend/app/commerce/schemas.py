from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

EntitlementEventKind = Literal[
    "GRANT",
    "RESERVE",
    "CONSUME",
    "RELEASE",
    "REVERSE",
    "EXPIRE",
]


class NotificationPreferencesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    in_app_enabled: bool
    email_enabled: bool
    sms_enabled: bool


class NotificationPreferencesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    in_app_enabled: bool
    email_enabled: bool
    sms_enabled: bool


class AccountNotification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str
    summary: str
    available_at: datetime
    read_at: datetime | None
    target_href: str | None


class AccountNotificationsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notifications: list[AccountNotification]
    unread_count: int = Field(ge=0)


class AccountNotificationsReadAllResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unread_count: int = Field(ge=0)


class AccountOrderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: UUID
    product_label: str
    amount_minor: int = Field(ge=0)
    currency: str
    status: str
    fulfillment_status: str | None
    created_at: datetime
    paid_at: datetime | None


class AccountOrdersResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    orders: list[AccountOrderResponse]


class AccountEntitlementEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: EntitlementEventKind
    quantity: int = Field(ge=1)
    occurred_at: datetime


class AccountEntitlementResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    granted: int = Field(ge=0)
    reserved: int = Field(ge=0)
    consumed: int = Field(ge=0)
    released: int = Field(ge=0)
    reversed: int = Field(ge=0)
    expired: int = Field(ge=0)
    available: int = Field(ge=0)
    events: list[AccountEntitlementEventResponse]


class AccountEntitlementsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entitlements: list[AccountEntitlementResponse]


AdminEntitlementAction = Literal["grant", "compensate", "revoke"]


class AdminEntitlementAdjustmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_user_id: UUID
    entitlement_id: str = Field(min_length=1, max_length=160)
    action: AdminEntitlementAction
    quantity: int = Field(default=1, ge=1)
    reason: str = Field(min_length=1, max_length=500)
    source_ref: str = Field(min_length=1, max_length=160)
    target_ref: str | None = Field(default=None, max_length=160)


class AdminEntitlementEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    owner_user_id: UUID
    entitlement_id: str
    kind: EntitlementEventKind
    quantity: int
    source_type: str
    source_ref: str
    target_ref: str | None
    created_at: datetime


class AdminEntitlementAdjustmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: AdminEntitlementEventResponse
    created: bool


class AdminEntitlementEventsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[AdminEntitlementEventResponse]


class AdminCatalogReasonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)


class AdminCatalogFamilyCreateRequest(AdminCatalogReasonRequest):
    key: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=160)


class AdminCatalogVersionCreateRequest(AdminCatalogReasonRequest):
    family_id: UUID
    version: str = Field(min_length=1, max_length=40)
    price_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    contract_version: str = Field(min_length=1, max_length=80)
    follow_up_count: int = Field(default=0, ge=0)
    follow_up_window_seconds: int = Field(default=0, ge=0)


class AdminCatalogOfferCreateRequest(AdminCatalogReasonRequest):
    product_version_id: UUID
    channel: str = Field(min_length=1, max_length=32)
    channel_sku: str = Field(min_length=1, max_length=160)
    price_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    enabled: bool = False


class AdminCatalogOfferEnabledRequest(AdminCatalogReasonRequest):
    enabled: bool


class AdminCatalogOfferResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    product_version_id: UUID
    channel: str
    channel_sku: str
    price_minor: int = Field(ge=0)
    currency: str
    enabled: bool
    created_at: datetime


class AdminCatalogVersionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    family_id: UUID
    version: str
    price_minor: int = Field(ge=0)
    currency: str
    contract_version: str
    follow_up_count: int = Field(ge=0)
    follow_up_window_seconds: int = Field(ge=0)
    status: str
    created_at: datetime
    offers: list[AdminCatalogOfferResponse]


class AdminCatalogFamilyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    key: str
    label: str
    status: str
    created_at: datetime
    versions: list[AdminCatalogVersionResponse]


class AdminCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    families: list[AdminCatalogFamilyResponse]


class AdminOrderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    owner_user_id: UUID
    product_version_id: UUID
    purchase_target_ref: str
    amount_minor: int = Field(ge=0)
    currency: str
    status: str
    fulfillment_status: str | None
    created_at: datetime
    paid_at: datetime | None


class AdminOrdersResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    orders: list[AdminOrderResponse]


class AdminPaymentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    order_id: UUID
    channel: str
    channel_transaction_id: str
    amount_minor: int = Field(ge=0)
    currency: str
    status: str
    confirmed_at: datetime


class AdminPaymentsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payments: list[AdminPaymentResponse]


class AdminRefundResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    payment_id: UUID
    order_id: UUID
    channel: str
    channel_refund_id: str | None
    amount_minor: int = Field(ge=0)
    currency: str
    reason: str
    status: str
    created_at: datetime
    confirmed_at: datetime | None
    referral_confirmation_id: UUID | None
    referral_confirmation_policy_version: str | None
    referral_confirmation_at: datetime | None


class AdminRefundsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refunds: list[AdminRefundResponse]


AdminReconciliationPaymentStatus = Literal[
    "pending",
    "succeeded",
    "failed",
    "refunded",
]
AdminReconciliationRefundStatus = Literal["pending", "succeeded", "failed"]


class AdminReconciliationPaymentSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: str = Field(min_length=1, max_length=180)
    status: AdminReconciliationPaymentStatus
    amount_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)


class AdminReconciliationRefundSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refund_id: str = Field(min_length=1, max_length=180)
    payment_transaction_id: str | None = Field(default=None, max_length=180)
    status: AdminReconciliationRefundStatus
    amount_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)


class AdminReconciliationRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: str = Field(min_length=1, max_length=32)
    reason: str = Field(min_length=1, max_length=500)
    payments: list[AdminReconciliationPaymentSnapshot] = Field(default_factory=list)
    refunds: list[AdminReconciliationRefundSnapshot] = Field(default_factory=list)


class AdminReconciliationItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    kind: Literal["payment", "refund"]
    reference: str
    payment_id: UUID | None
    refund_id: UUID | None
    local_status: str | None
    provider_status: str | None
    local_amount_minor: int | None
    provider_amount_minor: int | None
    local_currency: str | None
    provider_currency: str | None
    discrepancy: str
    created_at: datetime


class AdminReconciliationRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    channel: str
    run_at: datetime
    status: str
    item_count: int = Field(ge=0)
    matched_count: int = Field(ge=0)
    difference_count: int = Field(ge=0)
    created_at: datetime
    items: list[AdminReconciliationItemResponse]


class AdminReconciliationRunsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runs: list[AdminReconciliationRunResponse]


AdminNotificationStatus = Literal["pending", "processing", "sent", "failed"]


class AdminNotificationRetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)


class AdminNotificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    owner_user_id: UUID
    kind: str
    dedupe_key: str
    channel: str | None
    status: AdminNotificationStatus
    available_at: datetime
    attempt_count: int = Field(ge=0)
    processing_until: datetime | None
    sent_at: datetime | None
    last_error: str | None


class AdminNotificationsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notifications: list[AdminNotificationResponse]


class AdminAuditEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    action: str
    actor: str
    metadata: dict[str, str | int | bool | None]
    created_at: datetime


class AdminAuditEventsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[AdminAuditEventResponse]


class AdminSessionRevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)


class AdminStaffSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    staff_user_id: UUID
    actor: str
    status: Literal["active", "expired", "revoked"]
    expires_at: datetime
    last_seen_at: datetime
    revoked_at: datetime | None
    created_at: datetime


class AdminStaffSessionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sessions: list[AdminStaffSessionResponse]

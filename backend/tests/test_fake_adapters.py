import importlib
from decimal import Decimal
from uuid import uuid4


async def test_fake_payment_never_reports_real_settlement() -> None:
    payment = importlib.import_module("app.adapters.payment")
    gateway = payment.FakePaymentGateway()

    checkout = await gateway.create_checkout(
        order_id=uuid4(),
        amount_minor=2990,
        currency="CNY",
    )
    notification = await gateway.verify_notification(b"untrusted callback")

    assert checkout.channel == "fake"
    assert checkout.status == "unavailable"
    assert checkout.redirect_url is None
    assert notification.verified is False
    assert notification.payment_succeeded is False


async def test_fake_model_returns_schema_shaped_non_accepted_copy() -> None:
    model = importlib.import_module("app.adapters.model")
    gateway = model.FakeModelGateway()
    request = model.NarrativeRequest(
        fact_brief_id=uuid4(),
        product_kind="PREVIEW",
        required_sections=("conclusion", "basis", "boundaries"),
        max_cost=Decimal("0"),
    )

    candidate = await gateway.generate(request)

    assert tuple(candidate.sections) == request.required_sections
    assert candidate.provider == "fake"
    assert candidate.accepted is False
    assert candidate.cost == Decimal("0")


async def test_fake_runtime_is_explicitly_non_production() -> None:
    runtime = importlib.import_module("app.adapters.runtime")
    adapter = runtime.FakeMingliRuntimeAdapter()

    description = await adapter.describe()

    assert description.protocol_version == "fake-v1"
    assert description.production_ready is False
    assert description.capabilities == ("bazi", "fortune", "liuyao")

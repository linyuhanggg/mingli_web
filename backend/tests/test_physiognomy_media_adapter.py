from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from app.media.physiognomy import (
    MAX_MEDIA_BYTES,
    ConsentRequiredError,
    InMemoryPrivateMediaStore,
    LocalPrivateMediaStore,
    MediaQualityError,
    MediaValidationError,
    PhysiognomyMediaAdapter,
    UnsupportedObservationModeError,
)


def test_local_private_store_round_trips_only_under_its_root(tmp_path: Path) -> None:
    store = LocalPrivateMediaStore(tmp_path)
    object_key = "private/physiognomy/asset-synthetic"
    store.put(object_key, JPEG)

    assert (tmp_path / object_key).read_bytes() == JPEG
    assert store.read(object_key) == JPEG
    store.delete(object_key)
    assert not (tmp_path / object_key).exists()

NOW = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
JPEG = b"\xff\xd8\xff\xe0" + b"fateradar-test-jpeg"
PNG = b"\x89PNG\r\n\x1a\n" + b"fateradar-test-png"
HEIC = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00heic"


def _adapter() -> tuple[PhysiognomyMediaAdapter, InMemoryPrivateMediaStore, list[object]]:
    store = InMemoryPrivateMediaStore()
    audit: list[object] = []
    return PhysiognomyMediaAdapter(store=store, audit_sink=audit.append), store, audit


def test_ingest_keeps_media_private_and_emits_safe_audit_event() -> None:
    adapter, store, audit = _adapter()
    owner_id = uuid4()

    asset = adapter.ingest(
        owner_kind="guest",
        owner_id=owner_id,
        content_type="image/jpeg",
        filename="example-subject-front.jpg",
        payload=JPEG,
        width=1200,
        height=1600,
        consent=True,
        mode="face",
        now=NOW,
    )

    assert asset.status == "ready"
    assert asset.expires_at == NOW + timedelta(hours=24)
    assert asset.object_key.startswith("private/physiognomy/")
    assert store.read(asset.object_key) == JPEG
    assert asset.object_key not in str(audit[0])
    assert "example-subject-front.jpg" not in str(audit[0])
    assert audit[0].action == "physiognomy_media.accepted"  # type: ignore[union-attr]


@pytest.mark.parametrize("content_type,payload", [("image/png", PNG), ("image/heic", HEIC)])
def test_supported_image_containers_are_accepted(
    content_type: str,
    payload: bytes,
) -> None:
    adapter, _, _ = _adapter()

    asset = adapter.ingest(
        owner_kind="user",
        owner_id=uuid4(),
        content_type=content_type,
        filename="upload",
        payload=payload,
        width=1200,
        height=1600,
        consent=True,
        mode="face",
        now=NOW,
    )

    assert asset.status == "ready"
    assert asset.expires_at == NOW + timedelta(days=7)


def test_missing_consent_never_writes_bytes() -> None:
    adapter, store, _ = _adapter()

    with pytest.raises(ConsentRequiredError):
        adapter.ingest(
            owner_kind="guest",
            owner_id=uuid4(),
            content_type="image/jpeg",
            filename="photo.jpg",
            payload=JPEG,
            width=1200,
            height=1600,
            consent=False,
            mode="face",
            now=NOW,
        )

    assert store.keys() == ()


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({"content_type": "image/gif", "payload": b"GIF89a"}, MediaValidationError),
        ({"content_type": "image/jpeg", "payload": b"not-a-jpeg"}, MediaValidationError),
        ({"content_type": "image/jpeg", "payload": JPEG, "width": 320}, MediaQualityError),
        ({"content_type": "image/jpeg", "payload": JPEG, "height": 320}, MediaQualityError),
        (
            {"content_type": "image/jpeg", "payload": JPEG + b"x" * MAX_MEDIA_BYTES},
            MediaValidationError,
        ),
    ],
)
def test_invalid_container_size_and_quality_are_rejected(
    kwargs: dict[str, object],
    expected: type[Exception],
) -> None:
    adapter, store, _ = _adapter()

    with pytest.raises(expected):
        adapter.ingest(
            owner_kind="guest",
            owner_id=uuid4(),
            content_type=str(kwargs["content_type"]),
            filename="photo.jpg",
            payload=bytes(kwargs["payload"]),
            width=int(kwargs.get("width", 1200)),
            height=int(kwargs.get("height", 1600)),
            consent=True,
            mode="face",
            now=NOW,
        )

    assert store.keys() == ()


def test_runtime_input_contains_only_structured_observations() -> None:
    adapter, store, _ = _adapter()
    asset = adapter.ingest(
        owner_kind="user",
        owner_id=uuid4(),
        content_type="image/png",
        filename="photo.png",
        payload=PNG,
        width=1200,
        height=1600,
        consent=True,
        mode="face",
        now=NOW,
    )

    runtime_input = adapter.build_runtime_input(
        asset_id=asset.asset_id,
        subject_ref="sid-11111111111111111111111111111111",
        observations=(
            {
                "region": "forehead",
                "feature_kind": "visible_morphology",
                "descriptor": "region_visible",
                "visibility": "full",
                "uncertainty": 0.1,
            },
        ),
        dimension_ids=("state",),
    )
    prepared = runtime_input.to_prepare(query="只核对结构化观察", action="physiognomy_preview")
    facts = prepared.to_dict()["facts"]
    subject_facts = facts["sid-11111111111111111111111111111111"]
    spec = subject_facts["physiognomy_spec"]

    assert spec["schema_version"] == "mingli-physiognomy-input-v1"
    assert spec["observation_scope"] == "face"
    assert spec["assets"] == []
    assert spec["source_layer_policy"] == "terminology_and_methodology_only"
    target = spec["requested_targets"][0]
    observation = spec["observations"][0]
    assert target["taxonomy"] == "anatomical_face_v1"
    assert target["region"] == "forehead"
    assert target["feature_kind"] == "visible_morphology"
    assert observation["target_id"] == target["target_id"]
    assert observation["source_type"] == "user_file"
    assert observation["value"] == {"descriptor": "region_visible"}
    assert observation["quality"] == {
        "lighting": "not_applicable",
        "camera_angle": "caller_description",
        "focus": "not_applicable",
        "resolution": "not_applicable",
        "filtering": "not_applicable",
        "color_fidelity": "not_applicable",
    }
    assert spec["confirmed_observation_ids"] == [observation["observation_id"]]
    assert asset.object_key not in str(facts)
    assert asset.asset_id not in str(facts)
    assert store.read(asset.object_key) == PNG


def test_non_face_modes_are_not_sent_to_a_face_only_runtime() -> None:
    adapter, _, _ = _adapter()
    asset = adapter.ingest(
        owner_kind="user",
        owner_id=uuid4(),
        content_type="image/jpeg",
        filename="photo.jpg",
        payload=JPEG,
        width=1200,
        height=1600,
        consent=True,
        mode="palm",
        now=NOW,
    )

    with pytest.raises(UnsupportedObservationModeError):
        adapter.build_runtime_input(
            asset_id=asset.asset_id,
            subject_ref="sid-11111111111111111111111111111111",
            observations=(),
            dimension_ids=("state",),
        )


def test_delete_and_expire_remove_raw_bytes_but_keep_no_runtime_media_reference() -> None:
    adapter, store, _ = _adapter()
    guest_asset = adapter.ingest(
        owner_kind="guest",
        owner_id=uuid4(),
        content_type="image/jpeg",
        filename="photo.jpg",
        payload=JPEG,
        width=1200,
        height=1600,
        consent=True,
        mode="face",
        now=NOW,
    )
    user_asset = adapter.ingest(
        owner_kind="user",
        owner_id=uuid4(),
        content_type="image/jpeg",
        filename="photo.jpg",
        payload=JPEG,
        width=1200,
        height=1600,
        consent=True,
        mode="face",
        now=NOW,
    )

    adapter.delete(guest_asset.asset_id, now=NOW + timedelta(minutes=1))
    expired = adapter.expire(now=NOW + timedelta(days=8))

    assert guest_asset.asset_id not in expired
    assert user_asset.asset_id in expired
    assert store.keys() == ()
    assert adapter.get(guest_asset.asset_id).status == "deleted"
    assert adapter.get(user_asset.asset_id).status == "expired"

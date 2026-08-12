#!/usr/bin/env python3
"""Grant dogfood paid reading capabilities to one email account.

Run ONLY on the test server, from a release tree, with /etc/fateradar/test.env
loaded. Never print secrets. Does not talk to the public internet.

Example:
  set -a && . /etc/fateradar/test.env && set +a
  cd /opt/fateradar/releases/<sha>
  .venv/bin/python scripts/dogfood_grant.py --email you@example.com \\
      --capabilities today,week,liuyao --by 'ops@host'
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import Settings  # noqa: E402
from app.entitlements.service import PAID_READING_CAPABILITIES, EntitlementService  # noqa: E402
from app.identity.models import AuditEvent, LoginIdentity, User  # noqa: E402
from app.identity.otp import hash_identity, normalize_destination  # noqa: E402
from app.identity.repository import IdentityRepository  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def _parse_capabilities(raw: str) -> list[str]:
    items = [part.strip() for part in raw.split(",") if part.strip()]
    if not items:
        raise SystemExit("at least one capability is required")
    unknown = sorted(set(items) - PAID_READING_CAPABILITIES)
    if unknown:
        raise SystemExit(f"unknown capabilities: {', '.join(unknown)}")
    return sorted(set(items))


async def _resolve_user(session: AsyncSession, settings: Settings, email: str) -> User:
    address = normalize_destination("email", email)
    subject_hash = hash_identity(settings.identity_hash_key.get_secret_value(), address)
    identity = await session.scalar(
        select(LoginIdentity).where(
            LoginIdentity.provider == "email",
            LoginIdentity.provider_subject_hash == subject_hash,
            LoginIdentity.status == "active",
        )
    )
    if identity is None:
        raise SystemExit(
            "no active email login identity for that address; "
            "sign in once on the dogfood site before granting"
        )
    user = await session.get(User, identity.user_id)
    if user is None or user.status != "active":
        raise SystemExit("identity points to an unavailable user")
    return user


async def _run(args: argparse.Namespace) -> int:
    settings = Settings()
    if settings.environment == "production":
        raise SystemExit("refusing to run dogfood_grant against production environment")
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with sessions() as session:
            user = await _resolve_user(session, settings, args.email)
            service = EntitlementService(session, settings)
            granted = await service.grant_capabilities(
                owner_user_id=user.id,
                capability_ids=_parse_capabilities(args.capabilities),
                granted_by=args.by,
                note=args.note,
            )
            IdentityRepository(session).add_audit_event(
                AuditEvent(
                    user_id=user.id,
                    actor_session_id=None,
                    action="dogfood.grant_capabilities",
                    event_metadata={
                        "capabilities": granted,
                        "granted_by": args.by,
                        "note": args.note,
                    },
                )
            )
            await session.commit()
            active = await service.list_active(owner_user_id=user.id)
        print(f"granted={','.join(granted)}")
        print(f"active={','.join(active)}")
        print(f"user_id={user.id}")
        return 0
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="account email already signed in once")
    parser.add_argument(
        "--capabilities",
        default="today,week,liuyao",
        help="comma-separated: today,week,liuyao",
    )
    parser.add_argument("--by", default="dogfood-script", help="operator label for audit")
    parser.add_argument("--note", default=None, help="optional short note")
    return asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())

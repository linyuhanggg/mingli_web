#!/usr/bin/env python3
"""Delete one dogfood user's identity-owned data by email.

Run ONLY on the test server with /etc/fateradar/test.env loaded.
Deletes the User row and relies on FK CASCADE for sessions, grants,
profiles and readings owned by that user. Guest-only rows are untouched.

Example:
  set -a && . /etc/fateradar/test.env && set +a
  cd /opt/fateradar/releases/<sha>
  .venv/bin/python scripts/dogfood_delete_user.py --email you@example.com --yes
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
from app.identity.models import LoginIdentity, User  # noqa: E402
from app.identity.otp import hash_identity, normalize_destination  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


async def _run(args: argparse.Namespace) -> int:
    if not args.yes:
        raise SystemExit("refusing to delete without --yes")
    settings = Settings()
    if settings.environment == "production":
        raise SystemExit("refusing to run dogfood_delete_user against production environment")

    address = normalize_destination("email", args.email)
    subject_hash = hash_identity(settings.identity_hash_key.get_secret_value(), address)

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with sessions() as session:
            identity = await session.scalar(
                select(LoginIdentity).where(
                    LoginIdentity.provider == "email",
                    LoginIdentity.provider_subject_hash == subject_hash,
                    LoginIdentity.status == "active",
                )
            )
            if identity is None:
                raise SystemExit("no active email login identity for that address")
            user_id = identity.user_id
            result = await session.execute(delete(User).where(User.id == user_id))
            if result.rowcount != 1:
                raise SystemExit(f"expected to delete 1 user, deleted {result.rowcount}")
            await session.commit()
        print(f"deleted_user_id={user_id}")
        print("cascade: grants, device sessions, owned profiles/readings (via FK)")
        return 0
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="account email to erase")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="required confirmation flag",
    )
    return asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())

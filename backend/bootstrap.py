"""First-boot setup for Glean on Railway.

api role: wait for PostgreSQL, run migrations under an advisory lock (overlapping
deploys can't run them twice), then on the very first boot create the admin
account and the first user account from generated variables and switch open
sign-up off, so nobody else can register on a fresh public URL.
worker role (--wait-only): wait until the database schema is at the latest
migration before the worker starts.
Passwords are never printed.
"""
import asyncio
import hashlib
import os
import subprocess
import sys
import time

import asyncpg

DB_DIR = "/app/packages/database"
LOCK_ID = 7230820301
URL = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)


def log(msg: str) -> None:
    print(f"[glean-bootstrap] {msg}", flush=True)


def alembic_heads() -> set[str]:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(os.path.join(DB_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(DB_DIR, "glean_database/migrations"))
    return set(ScriptDirectory.from_config(cfg).get_heads())


async def connect() -> asyncpg.Connection:
    deadline = time.monotonic() + 300
    while True:
        try:
            return await asyncpg.connect(URL, timeout=10)
        except Exception as exc:  # noqa: BLE001
            if time.monotonic() > deadline:
                raise
            log(f"waiting for PostgreSQL ({type(exc).__name__})")
            await asyncio.sleep(3)


async def current_revisions(conn: asyncpg.Connection) -> set[str]:
    try:
        rows = await conn.fetch("SELECT version_num FROM alembic_version")
    except asyncpg.UndefinedTableError:
        return set()
    return {r[0] for r in rows}


def sha256_hex(value: str) -> str:
    # The Glean web and admin apps send SHA-256(password); the API stores bcrypt of that.
    return hashlib.sha256(value.encode()).hexdigest()


async def first_boot_accounts() -> None:
    from sqlalchemy import func, select

    from glean_core.auth import hash_password
    from glean_core.services import AdminService, TypedConfigService
    from glean_database.models import AdminUser, User, UserAuthProvider
    from glean_database.models.admin import AdminRole
    from glean_database.session import get_session_context, init_database

    init_database(os.environ["DATABASE_URL"])
    async with get_session_context() as session:
        admins = await session.scalar(select(func.count()).select_from(AdminUser))
        if admins:
            log("existing installation: accounts and sign-up settings left unchanged")
            return

        admin_user = os.environ.get("ADMIN_USERNAME") or "admin"
        admin_pw = os.environ.get("ADMIN_PASSWORD") or ""
        user_email = (os.environ.get("GLEAN_USER_EMAIL") or "").strip()
        user_pw = os.environ.get("GLEAN_USER_PASSWORD") or ""
        if len(admin_pw) < 12:
            log("ADMIN_PASSWORD must be set (12+ characters) for the first boot")
            sys.exit(78)
        if user_email:
            from pydantic import validate_email

            try:
                # Same normalisation the login form's EmailStr applies.
                user_email = validate_email(user_email)[1]
            except Exception:  # noqa: BLE001
                log(f"GLEAN_USER_EMAIL '{user_email}' is not a valid email address; fix the variable and redeploy")
                sys.exit(78)
            if len(user_pw) < 8:
                log("GLEAN_USER_PASSWORD must be at least 8 characters")
                sys.exit(78)

        await AdminService(session).create_admin_user(
            username=admin_user, password=sha256_hex(admin_pw), role=AdminRole.SUPER_ADMIN
        )
        log(f"created admin account '{admin_user}' (password: ADMIN_PASSWORD variable)")

        if user_email:
            exists = await session.scalar(select(User).where(User.email == user_email))
            if not exists:
                user = User(
                    email=user_email,
                    name=user_email.split("@")[0],
                    password_hash=hash_password(sha256_hex(user_pw)),
                    primary_auth_provider="local",
                    provider_user_id=user_email,
                    is_active=True,
                    is_verified=True,
                )
                session.add(user)
                await session.flush()
                session.add(
                    UserAuthProvider(
                        user_id=user.id,
                        provider_id="local",
                        provider_user_id=user_email,
                        provider_metadata={},
                    )
                )
                log(f"created user account '{user_email}' (password: GLEAN_USER_PASSWORD variable)")
        await session.commit()

        if os.environ.get("GLEAN_OPEN_REGISTRATION", "false").lower() not in ("1", "true", "yes"):
            await TypedConfigService(session).set_registration_enabled(False)
            await session.commit()
            log("open sign-up switched off (turn it on in the admin panel if you want it)")


async def main(wait_only: bool) -> None:
    heads = alembic_heads()
    conn = await connect()
    try:
        if wait_only:
            deadline = time.monotonic() + 900
            while await current_revisions(conn) != heads:
                if time.monotonic() > deadline:
                    log("database schema still not migrated after 15 minutes")
                    sys.exit(1)
                log("waiting for the API to finish database migrations")
                await asyncio.sleep(5)
            log("database schema is current")
            return

        while not await conn.fetchval("SELECT pg_try_advisory_lock($1)", LOCK_ID):
            log("another deploy holds the migration lock; waiting")
            await asyncio.sleep(3)
        try:
            if await current_revisions(conn) != heads:
                log("running database migrations")
                subprocess.run(["alembic", "upgrade", "head"], cwd=DB_DIR, check=True)
            else:
                log("database schema is current")
            await first_boot_accounts()
        finally:
            await conn.execute("SELECT pg_advisory_unlock($1)", LOCK_ID)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main("--wait-only" in sys.argv))

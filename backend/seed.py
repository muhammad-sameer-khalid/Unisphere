"""
UniSphere CLI Seed Script.

Usage:
    python seed.py

Executes the idempotent seed data mechanism against the configured local development database.
Includes strict target verification to ensure it only targets explicitly approved local
development databases, completely prohibits Neon and remote databases, validates targets
before creating engines or opening sessions, and sanitizes all errors to prevent credential leakage.
"""

import os
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv

from app.database.seed import seed_database

# Approved schemes, hosts, and database names for local development seeding
ALLOWED_SCHEMES = ("postgresql", "postgresql+psycopg", "postgres")
ALLOWED_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
ALLOWED_DEV_DATABASES = {"unisphere_db", "unisphere_dev", "unisphere_development", "unisphere_local"}


def verify_target_safety(url: str) -> None:
    """
    Verify that the configured database is safe and intended for development seeding.

    Strict permitted target rules:
    1. Rejects invalid, empty, or non-PostgreSQL URLs.
    2. Rejects any production-like hosts, database names, or paths.
    3. Strictly rejects all Neon cloud endpoints (*.neon.tech), including development branches.
    4. Strictly rejects all other remote or cloud database hosts.
    5. Permits only explicitly approved local development hosts ('localhost', '127.0.0.1', '::1').
    6. Permits only an explicit allowlist of UniSphere local development database names:
       ('unisphere_db', 'unisphere_dev', 'unisphere_development', 'unisphere_local').
    7. Rejects test databases (names containing 'test') to prevent corrupting test environments.
    8. Sanitizes all printed target details (never logs credentials, passwords, or full connection strings).
    """
    if not url or not isinstance(url, str):
        print("ERROR: Database connection URL is empty or invalid.", file=sys.stderr)
        sys.exit(1)

    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    hostname = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    db_name = path.lstrip("/")

    if scheme not in ALLOWED_SCHEMES:
        print(f"ERROR: Unsupported database scheme '{scheme}'. UniSphere requires PostgreSQL.", file=sys.stderr)
        sys.exit(1)

    if not hostname:
        print("ERROR: Database connection URL does not specify a valid host.", file=sys.stderr)
        sys.exit(1)

    if not db_name:
        print("ERROR: Database connection URL does not specify a database name.", file=sys.stderr)
        sys.exit(1)

    # 1. Prohibit Neon endpoints completely (including development branches)
    if "neon.tech" in hostname or "neon." in hostname:
        print(
            "CRITICAL: Target database validation failed. Seeding against Neon cloud databases "
            "(including development branches) is strictly prohibited. Seeding is only permitted against local development databases.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 2. Block any production targeting
    host_parts = hostname.split(".")
    is_prod_host = (
        "production" in hostname
        or any("prod" in part for part in host_parts)
        or hostname.startswith("prod-")
    )
    is_prod_db = (
        "production" in db_name
        or db_name.startswith("prod")
        or db_name.endswith("_prod")
        or "_prod_" in db_name
    )

    if is_prod_host or is_prod_db:
        print(
            "CRITICAL: Target database validation failed. Seeding is strictly forbidden against production targets.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 3. Reject test databases
    if "test" in db_name:
        print(
            f"CRITICAL: Target database validation failed. Database '{db_name}' is a test database. "
            "The development seed CLI cannot target test databases.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 4. Enforce explicitly approved local hosts only
    if hostname not in ALLOWED_LOCAL_HOSTS:
        sanitized_host = parsed.hostname or "unknown-host"
        print(
            f"CRITICAL: Target database validation failed. '{sanitized_host}' is not an approved local development host. "
            f"Seeding is strictly restricted to local development instances ({', '.join(sorted(ALLOWED_LOCAL_HOSTS))}).",
            file=sys.stderr,
        )
        sys.exit(1)

    # 5. Enforce explicit allowlist of UniSphere local development database names
    if db_name not in ALLOWED_DEV_DATABASES:
        sanitized_db = db_name or "unknown-db"
        print(
            f"CRITICAL: Target database validation failed. Database '{sanitized_db}' is not in the allowlist "
            f"of approved UniSphere development databases ({', '.join(sorted(ALLOWED_DEV_DATABASES))}).",
            file=sys.stderr,
        )
        sys.exit(1)

    # Print sanitized target information (never credentials or full connection strings)
    sanitized_host = parsed.hostname or "unknown-host"
    sanitized_db = db_name or "unknown-db"
    print(f"Target Database : {sanitized_db}")
    print(f"Target Host     : {sanitized_host}")


def main() -> None:
    print("=" * 60)
    print("UniSphere ERP — Database Seeding CLI")
    print("=" * 60)

    # Load environment configuration
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print(
            "ERROR: DATABASE_URL is not set. Please configure backend/.env",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate target safety BEFORE creating engine or opening session
    verify_target_safety(database_url)
    print("-" * 60)
    print("Executing idempotent seed operations...")

    db = None
    try:
        from app.database.connection import SessionLocal
        db = SessionLocal()
        stats = seed_database(db)
        print("-" * 60)
        print(f"{'Entity':<25} {'Created':<10} {'Existing (Preserved)':<20}")
        print("-" * 60)
        total_created = 0
        total_existing = 0
        for entity, count_dict in stats.items():
            c = count_dict["created"]
            e = count_dict["existing"]
            total_created += c
            total_existing += e
            print(f"{entity:<25} {c:<10} {e:<20}")
        print("-" * 60)
        print(f"Total Created : {total_created}")
        print(f"Total Existing: {total_existing}")
        print("=" * 60)
        print("Seeding completed successfully.")
        print("=" * 60)
    except Exception as error:
        # Sanitize error message to prevent database credentials or sensitive details leaking
        err_msg = str(error)
        # Suppress raw connection strings if present in driver exceptions
        if "@" in err_msg and "://" in err_msg:
            err_msg = "Database operation failed. (Connection details suppressed for security)"
        print(f"ERROR: Seeding failed: {err_msg}", file=sys.stderr)
        sys.exit(1)
    finally:
        if db is not None:
            db.close()


if __name__ == "__main__":
    main()

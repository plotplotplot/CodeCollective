import asyncio
import os
import uuid
from decimal import Decimal, getcontext
from datetime import datetime, timezone

import asyncpg
from asyncpg import exceptions as asyncpg_exceptions

getcontext().prec = 18

COCKROACH_ASYNC_URL = os.environ.get("COCKROACH_ASYNC_URL", "")
DEFAULT_UBI_INTERVAL_SECONDS = int(os.environ.get("UBI_INTERVAL_SECONDS", "60"))
DEFAULT_DENA_ANNUAL = Decimal(os.environ.get("DENA_ANNUAL", "1"))
DEFAULT_DENA_PRECISION = int(os.environ.get("DENA_PRECISION", "6"))
DEFAULT_ENTITY_TYPES = [item.strip() for item in os.environ.get("UBI_ENTITY_TYPES", "individual").split(",") if item.strip()]
DEFAULT_ENTITY_TYPES_CSV = ",".join(DEFAULT_ENTITY_TYPES or ["individual"])
DB_RETRY_BASE_SECONDS = float(os.environ.get("UBI_DB_RETRY_BASE_SECONDS", "1"))
DB_RETRY_MAX_SECONDS = float(os.environ.get("UBI_DB_RETRY_MAX_SECONDS", "30"))
UBI_DB_POOL_MIN_SIZE = int(os.environ.get("UBI_DB_POOL_MIN_SIZE", "1"))
UBI_DB_POOL_MAX_SIZE = int(os.environ.get("UBI_DB_POOL_MAX_SIZE", "1"))


def dena_per_tick(annual: Decimal, precision: int) -> Decimal:
    minutes_per_year = Decimal(60 * 24 * 365)
    amount = annual / minutes_per_year
    return amount.quantize(Decimal("1." + "0" * precision))


async def ensure_schema(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        ALTER TABLE accounts
        ADD COLUMN IF NOT EXISTS dena_balance DECIMAL(20, 6) DEFAULT 0
        """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ubi_runtime_settings (
            id INT PRIMARY KEY CHECK (id = 1),
            interval_seconds INT NOT NULL,
            dena_annual DECIMAL(20, 6) NOT NULL,
            dena_precision INT NOT NULL,
            entity_types TEXT NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_by TEXT
        )
        """
    )
    await conn.execute(
        """
        INSERT INTO ubi_runtime_settings (id, interval_seconds, dena_annual, dena_precision, entity_types, updated_by)
        VALUES (1, $1, $2, $3, $4, 'ubi-service-bootstrap')
        ON CONFLICT (id) DO NOTHING
        """,
        DEFAULT_UBI_INTERVAL_SECONDS,
        float(DEFAULT_DENA_ANNUAL),
        DEFAULT_DENA_PRECISION,
        DEFAULT_ENTITY_TYPES_CSV,
    )


def _parse_entity_types(value: str) -> list[str]:
    parsed = [item.strip().lower() for item in (value or "").split(",") if item.strip()]
    return parsed or ["individual"]


async def get_runtime_settings(conn: asyncpg.Connection) -> dict:
    row = await conn.fetchrow(
        """
        SELECT interval_seconds, dena_annual, dena_precision, entity_types
        FROM ubi_runtime_settings
        WHERE id = 1
        """
    )
    if not row:
        return {
            "interval_seconds": DEFAULT_UBI_INTERVAL_SECONDS,
            "dena_annual": DEFAULT_DENA_ANNUAL,
            "dena_precision": DEFAULT_DENA_PRECISION,
            "entity_types": DEFAULT_ENTITY_TYPES or ["individual"],
        }
    interval_seconds = max(1, int(row["interval_seconds"]))
    dena_annual = Decimal(str(row["dena_annual"]))
    dena_precision = max(0, min(12, int(row["dena_precision"])))
    entity_types = _parse_entity_types(str(row["entity_types"]))
    return {
        "interval_seconds": interval_seconds,
        "dena_annual": dena_annual,
        "dena_precision": dena_precision,
        "entity_types": entity_types,
    }


async def tick(pool: asyncpg.Pool, settings: dict):
    amount = dena_per_tick(settings["dena_annual"], settings["dena_precision"])
    entity_types = [str(value).strip().lower() for value in settings["entity_types"] if str(value).strip()]
    if not entity_types:
        entity_types = ["individual"]
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Accumulate high-precision UBI into dena_balance.
            await conn.execute(
                """
                UPDATE accounts
                SET dena_balance = COALESCE(dena_balance, 0) + $1,
                    updated_at = NOW()
                WHERE LOWER(entity_type::text) = ANY($2::text[])
                """,
                float(amount),
                entity_types,
            )

            # Move whole cents from dena_balance into spendable account balance.
            payouts = await conn.fetch(
                """
                WITH eligible AS (
                    SELECT
                        id,
                        FLOOR(COALESCE(dena_balance, 0) * 100) / 100 AS payout
                    FROM accounts
                    WHERE LOWER(entity_type::text) = ANY($1::text[])
                      AND COALESCE(dena_balance, 0) >= 0.01
                ),
                updated AS (
                    UPDATE accounts a
                    SET balance = COALESCE(a.balance, 0) + e.payout,
                        dena_balance = COALESCE(a.dena_balance, 0) - e.payout,
                        updated_at = NOW()
                    FROM eligible e
                    WHERE a.id = e.id
                      AND e.payout > 0
                    RETURNING a.id, e.payout
                )
                SELECT id, payout FROM updated
                """,
                entity_types,
            )

            if payouts:
                await conn.executemany(
                    """
                    INSERT INTO transactions
                        (id, to_account_id, amount, currency, transaction_type, description, timestamp)
                    VALUES
                        ($1, $2, $3, 'DEM', 'UBI_PAYMENT', $4, NOW())
                    """,
                    [
                        (
                            uuid.uuid4(),
                            row["id"],
                            float(row["payout"]),
                            "Automatic UBI payout from dena balance",
                        )
                        for row in payouts
                    ],
                )
            return payouts


def _is_transient_db_error(exc: Exception) -> bool:
    return isinstance(
        exc,
        (
            OSError,
            ConnectionError,
            asyncpg_exceptions.InterfaceError,
            asyncpg_exceptions.InternalClientError,
            asyncpg_exceptions.PostgresConnectionError,
        ),
    )


def _is_txn_limit_error(exc: Exception) -> bool:
    if not isinstance(exc, asyncpg_exceptions.PostgresError):
        return False
    message = str(exc).lower()
    return "maximum number of concurrently open transactions has been reached" in message


async def run() -> None:
    if not COCKROACH_ASYNC_URL:
        raise RuntimeError("COCKROACH_ASYNC_URL is required")

    pool = await asyncpg.create_pool(
        COCKROACH_ASYNC_URL,
        min_size=max(1, UBI_DB_POOL_MIN_SIZE),
        max_size=max(1, UBI_DB_POOL_MAX_SIZE),
    )
    try:
        retry_delay = DB_RETRY_BASE_SECONDS
        while True:
            try:
                async with pool.acquire() as conn:
                    await ensure_schema(conn)
                    settings = await get_runtime_settings(conn)
                break
            except Exception as exc:
                if not _is_transient_db_error(exc):
                    raise
                print(
                    f"{datetime.now(timezone.utc).isoformat()} UBI startup transient DB error: {exc}. "
                    f"retry_in={retry_delay}s"
                )
                await asyncio.sleep(retry_delay)
                retry_delay = min(DB_RETRY_MAX_SECONDS, retry_delay * 2)
                await pool.expire_connections()
        print(
            f"{datetime.now(timezone.utc).isoformat()} UBI service started with interval "
            f"{settings['interval_seconds']}s"
        )
        retry_delay = DB_RETRY_BASE_SECONDS
        while True:
            try:
                tick_ts = datetime.now(timezone.utc).isoformat()
                async with pool.acquire() as conn:
                    settings = await get_runtime_settings(conn)
                print(
                    f"{tick_ts} UBI tick started interval={settings['interval_seconds']} "
                    f"dena_annual={settings['dena_annual']} dena_precision={settings['dena_precision']} "
                    f"entity_types={','.join(settings['entity_types'])}"
                )
                payouts = await tick(pool, settings)
                payout_count = len(payouts) if payouts else 0
                total_paid = sum(Decimal(str(row["payout"])) for row in payouts) if payouts else Decimal("0")
                print(
                    f"{datetime.now(timezone.utc).isoformat()} UBI tick completed "
                    f"payouts={payout_count} total_paid={total_paid}"
                )
                retry_delay = DB_RETRY_BASE_SECONDS
                await asyncio.sleep(settings["interval_seconds"])
            except Exception as exc:
                if _is_transient_db_error(exc) or _is_txn_limit_error(exc):
                    print(
                        f"{datetime.now(timezone.utc).isoformat()} UBI transient/backpressure DB error: {exc}. "
                        f"retry_in={retry_delay}s"
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(DB_RETRY_MAX_SECONDS, retry_delay * 2)
                    await pool.expire_connections()
                    continue
                print(f"{datetime.now(timezone.utc).isoformat()} UBI tick failed: {exc}")
                await asyncio.sleep(DEFAULT_UBI_INTERVAL_SECONDS)
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(run())

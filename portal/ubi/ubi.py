import asyncio
import os
from decimal import Decimal, getcontext
from datetime import datetime, timezone

import asyncpg

getcontext().prec = 18

COCKROACH_ASYNC_URL = os.environ.get("COCKROACH_ASYNC_URL", "")
UBI_INTERVAL_SECONDS = int(os.environ.get("UBI_INTERVAL_SECONDS", "60"))
DENA_ANNUAL = Decimal(os.environ.get("DENA_ANNUAL", "1"))
DENA_PRECISION = int(os.environ.get("DENA_PRECISION", "6"))
ENTITY_TYPES = [item.strip() for item in os.environ.get("UBI_ENTITY_TYPES", "individual").split(",") if item.strip()]


def dena_per_tick() -> Decimal:
    minutes_per_year = Decimal(60 * 24 * 365)
    amount = DENA_ANNUAL / minutes_per_year
    return amount.quantize(Decimal("1." + "0" * DENA_PRECISION))


async def ensure_schema(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        ALTER TABLE accounts
        ADD COLUMN IF NOT EXISTS dena_balance DECIMAL(20, 6) DEFAULT 0
        """
    )


async def tick(pool: asyncpg.Pool) -> None:
    amount = dena_per_tick()
    async with pool.acquire() as conn:
        await ensure_schema(conn)
        await conn.execute(
            """
            UPDATE accounts
            SET dena_balance = COALESCE(dena_balance, 0) + $1,
                updated_at = NOW()
            WHERE entity_type = ANY($2::text[])
            """,
            float(amount),
            ENTITY_TYPES,
        )


async def run() -> None:
    if not COCKROACH_ASYNC_URL:
        raise RuntimeError("COCKROACH_ASYNC_URL is required")

    pool = await asyncpg.create_pool(COCKROACH_ASYNC_URL, min_size=1, max_size=5)
    print(f"UBI service started at {datetime.now(timezone.utc).isoformat()} with interval {UBI_INTERVAL_SECONDS}s")
    try:
        while True:
            try:
                await tick(pool)
            except Exception as exc:
                print(f"UBI tick failed: {exc}")
            await asyncio.sleep(UBI_INTERVAL_SECONDS)
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(run())

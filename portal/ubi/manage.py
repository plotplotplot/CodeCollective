#!/usr/bin/env python3
"""Management commands for UBI service.

Usage:
    python manage.py trigger_payout
    python manage.py get_settings
    python manage.py update_settings --interval-seconds 120 --dena-annual 1000
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg
import httpx

COCKROACH_ASYNC_URL = os.environ.get("COCKROACH_ASYNC_URL", "")
PIDP_BASE_URL = os.environ.get("PIDP_BASE_URL", "http://pidp:8000")
UBI_API_KEY = os.environ.get("UBI_API_KEY", "")


def get_db_pool():
    """Create database pool."""
    if not COCKROACH_ASYNC_URL:
        raise RuntimeError("COCKROACH_ASYNC_URL not set")
    return asyncpg.create_pool(COCKROACH_ASYNC_URL, min_size=1, max_size=1)


async def get_settings():
    """Get current UBI settings."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT interval_seconds, dena_annual, dena_precision, entity_types, updated_at, updated_by "
            "FROM ubi_runtime_settings WHERE id = 1"
        )
    await pool.close()
    
    if not row:
        print("No settings found")
        return
    
    print("Current UBI Settings:")
    print(f"  Interval: {row['interval_seconds']} seconds")
    print(f"  Annual DENA: {row['dena_annual']} DEM")
    print(f"  Precision: {row['dena_precision']} decimal places")
    print(f"  Entity Types: {row['entity_types']}")
    print(f"  Last Updated: {row['updated_at']} by {row['updated_by']}")


async def trigger_payout():
    """Manually trigger a UBI payout."""
    from ubi import tick, get_runtime_settings, dena_per_tick
    from decimal import Decimal
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        settings = await get_runtime_settings(conn)
    
    print(f"Triggering UBI payout with settings:")
    print(f"  Annual DENA: {settings['dena_annual']}")
    print(f"  Per-tick amount: {dena_per_tick(settings['dena_annual'], settings['dena_precision'])}")
    print(f"  Entity types: {settings['entity_types']}")
    
    payouts = await tick(pool, settings)
    
    if payouts:
        total = sum(Decimal(str(row["payout"])) for row in payouts)
        print(f"\n✓ Payout complete: {len(payouts)} recipients, {total} DEM total")
    else:
        print("\n✓ Payout complete: No eligible recipients")
    
    await pool.close()


async def update_settings(
    interval_seconds: int | None = None,
    dena_annual: float | None = None,
    dena_precision: int | None = None,
    entity_types: str | None = None,
    api_key: str | None = None,
    pidp_token: str | None = None,
):
    """Update UBI settings via API."""
    url = f"{PIDP_BASE_URL.replace('/pidp', '').replace(':8000', ':8001')}/api/settings"
    
    data = {}
    if interval_seconds is not None:
        data["interval_seconds"] = interval_seconds
    if dena_annual is not None:
        data["dena_annual"] = dena_annual
    if dena_precision is not None:
        data["dena_precision"] = dena_precision
    if entity_types is not None:
        data["entity_types"] = entity_types
    
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    elif pidp_token:
        headers["Authorization"] = f"Bearer {pidp_token}"
    elif UBI_API_KEY:
        headers["Authorization"] = f"Bearer {UBI_API_KEY}"
    else:
        print("Error: No API key or token provided")
        return False
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, data=data, headers=headers)
            if resp.is_success:
                print("✓ Settings updated successfully")
                print(resp.json())
                return True
            else:
                print(f"✗ Failed to update settings: {resp.status_code}")
                print(resp.text)
                return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="UBI Service Management Commands")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # get_settings command
    subparsers.add_parser("get_settings", help="Get current UBI settings")
    
    # trigger_payout command
    subparsers.add_parser("trigger_payout", help="Manually trigger a UBI payout")
    
    # update_settings command
    update_parser = subparsers.add_parser("update_settings", help="Update UBI settings")
    update_parser.add_argument("--interval-seconds", type=int, help="Tick interval in seconds")
    update_parser.add_argument("--dena-annual", type=float, help="Annual DENA amount")
    update_parser.add_argument("--dena-precision", type=int, help="Decimal precision")
    update_parser.add_argument("--entity-types", help="Comma-separated entity types")
    update_parser.add_argument("--api-key", help="UBI API key")
    update_parser.add_argument("--pidp-token", help="PIdP JWT token")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "get_settings":
        asyncio.run(get_settings())
    
    elif args.command == "trigger_payout":
        asyncio.run(trigger_payout())
    
    elif args.command == "update_settings":
        success = asyncio.run(update_settings(
            interval_seconds=args.interval_seconds,
            dena_annual=args.dena_annual,
            dena_precision=args.dena_precision,
            entity_types=args.entity_types,
            api_key=args.api_key,
            pidp_token=args.pidp_token,
        ))
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

import asyncio
import os
import uuid
from decimal import Decimal, getcontext
from datetime import datetime, timezone
from contextlib import asynccontextmanager

import asyncpg
from asyncpg import exceptions as asyncpg_exceptions

# FastAPI imports
from fastapi import FastAPI, Form, HTTPException, Header, Depends
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# HTTP client for auth requests
import httpx

# Security
UBI_API_KEY = os.environ.get("UBI_API_KEY", "")
PIDP_BASE_URL = os.environ.get("PIDP_BASE_URL", "http://pidp:8000")
security = HTTPBearer(auto_error=False)

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

# Global state
db_pool: asyncpg.Pool | None = None
ubi_task: asyncio.Task | None = None


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


async def update_runtime_settings(
    conn: asyncpg.Connection,
    interval_seconds: int | None = None,
    dena_annual: Decimal | None = None,
    dena_precision: int | None = None,
    entity_types: str | None = None,
    updated_by: str = "web-ui",
) -> dict:
    current = await get_runtime_settings(conn)
    
    new_interval = max(1, interval_seconds) if interval_seconds is not None else current["interval_seconds"]
    new_annual = Decimal(str(dena_annual)) if dena_annual is not None else current["dena_annual"]
    new_precision = max(0, min(12, dena_precision)) if dena_precision is not None else current["dena_precision"]
    new_entity_types = entity_types if entity_types is not None else ",".join(current["entity_types"])
    
    await conn.execute(
        """
        INSERT INTO ubi_runtime_settings (id, interval_seconds, dena_annual, dena_precision, entity_types, updated_at, updated_by)
        VALUES (1, $1, $2, $3, $4, NOW(), $5)
        ON CONFLICT (id) DO UPDATE SET
            interval_seconds = EXCLUDED.interval_seconds,
            dena_annual = EXCLUDED.dena_annual,
            dena_precision = EXCLUDED.dena_precision,
            entity_types = EXCLUDED.entity_types,
            updated_at = EXCLUDED.updated_at,
            updated_by = EXCLUDED.updated_by
        """,
        new_interval,
        float(new_annual),
        new_precision,
        new_entity_types,
        updated_by,
    )
    
    return {
        "interval_seconds": new_interval,
        "dena_annual": new_annual,
        "dena_precision": new_precision,
        "entity_types": _parse_entity_types(new_entity_types),
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


async def ubi_tick_loop(pool: asyncpg.Pool):
    """Background task that runs UBI ticks."""
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
        except asyncio.CancelledError:
            print(f"{datetime.now(timezone.utc).isoformat()} UBI tick loop cancelled, shutting down gracefully...")
            raise  # Re-raise to properly exit the task
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


# HTML Template for the homepage
HOME_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UBI Service</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .info-row:last-child { border-bottom: none; }
        .label { font-weight: 600; color: #666; }
        .value { color: #2c3e50; font-family: monospace; }
        form { margin-top: 15px; }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #555;
        }
        input[type="number"], input[type="text"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        button {
            background: #3498db;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover { background: #2980b9; }
        .success {
            background: #d4edda;
            color: #155724;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 15px;
        }
        .info-box {
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            margin: 15px 0;
            border-radius: 0 4px 4px 0;
        }
        .status {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #4caf50;
            margin-right: 8px;
        }
    </style>
</head>
<body>
    <h1>🔷 UBI Service</h1>
    
    <div class="info-box">
        <span class="status"></span>
        <strong>Service Status:</strong> Running | 
        <strong>Current Time:</strong> {current_time}
    </div>

    <div class="card">
        <h2>About</h2>
        <p>
            The Universal Basic Income (UBI) Service automatically distributes periodic payments 
            to eligible accounts. It accumulates high-precision UBI into a dena balance and 
            transfers whole cents to spendable account balance.
        </p>
        <p>
            <strong>UBI per tick:</strong> {dena_per_tick} DEM<br>
            <strong>Formula:</strong> Annual amount ÷ (60 × 24 × 365 minutes)
        </p>
    </div>

    <div class="card">
        <h2>Current Settings</h2>
        <div class="info-row">
            <span class="label">Interval (seconds):</span>
            <span class="value">{interval_seconds}</span>
        </div>
        <div class="info-row">
            <span class="label">Annual DENA:</span>
            <span class="value">{dena_annual} DEM</span>
        </div>
        <div class="info-row">
            <span class="label">Precision:</span>
            <span class="value">{dena_precision} decimal places</span>
        </div>
        <div class="info-row">
            <span class="label">Entity Types:</span>
            <span class="value">{entity_types}</span>
        </div>
    </div>

    <div class="card">
        <h2>Adjust Parameters</h2>
        {success_message}
        <form method="post" action="/update">
            <div class="form-group">
                <label for="interval_seconds">Interval (seconds)</label>
                <input type="number" id="interval_seconds" name="interval_seconds" 
                       value="{interval_seconds}" min="1" required>
            </div>
            <div class="form-group">
                <label for="dena_annual">Annual DENA Amount</label>
                <input type="number" id="dena_annual" name="dena_annual" 
                       value="{dena_annual}" step="0.000001" min="0" required>
            </div>
            <div class="form-group">
                <label for="dena_precision">Precision (0-12 decimal places)</label>
                <input type="number" id="dena_precision" name="dena_precision" 
                       value="{dena_precision}" min="0" max="12" required>
            </div>
            <div class="form-group">
                <label for="entity_types">Entity Types (comma-separated)</label>
                <input type="text" id="entity_types" name="entity_types" 
                       value="{entity_types}" required>
            </div>
            <button type="submit">Update Settings</button>
        </form>
    </div>

    <div class="card">
        <h2>API Endpoints</h2>
        <div class="info-row">
            <span class="label">GET /</span>
            <span class="value">This homepage</span>
        </div>
        <div class="info-row">
            <span class="label">GET /health</span>
            <span class="value">Health check</span>
        </div>
        <div class="info-row">
            <span class="label">GET /settings</span>
            <span class="value">Current settings (JSON)</span>
        </div>
        <div class="info-row">
            <span class="label">POST /update</span>
            <span class="value">Update settings (form data, requires API key)</span>
        </div>
        <div class="info-row">
            <span class="label">POST /api/settings</span>
            <span class="value">Update settings (JSON API, requires API key)</span>
        </div>
    </div>

    <div class="card">
        <h2>Authentication</h2>
        <p>
            <strong>Status:</strong> {auth_status}
        </p>
        <p>
            To update settings, you must be an admin. Admin status is managed centrally by PIdP via SpiceDB.
        </p>
        <h3>Authentication Methods:</h3>
        <ol>
            <li><strong>API Key:</strong> <code>Authorization: Bearer &lt;UBI_API_KEY&gt;</code></li>
            <li><strong>JWT Token:</strong> <code>Authorization: Bearer &lt;PIDP_TOKEN&gt;</code> (user must have admin role in SpiceDB)</li>
        </ol>
        <h3>Managing Admins:</h3>
        <p>
            Use PIdP admin endpoints to grant/revoke admin status:
        </p>
        <ul>
            <li><code>POST /auth/admin/grant?user_id=&lt;uuid&gt;</code> - Grant admin (requires bootstrap key or existing admin)</li>
            <li><code>POST /auth/admin/revoke?user_id=&lt;uuid&gt;</code> - Revoke admin</li>
            <li><code>GET /auth/admin/check</code> - Check if current user is admin</li>
        </ul>
        <p>
            <em>Environment: UBI_API_KEY (optional), PIDP_BASE_URL</em>
        </p>
    </div>
</body>
</html>
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    global db_pool, ubi_task
    
    if not COCKROACH_ASYNC_URL:
        raise RuntimeError("COCKROACH_ASYNC_URL is required")
    
    # Create database pool
    db_pool = await asyncpg.create_pool(
        COCKROACH_ASYNC_URL,
        min_size=max(1, UBI_DB_POOL_MIN_SIZE),
        max_size=max(1, UBI_DB_POOL_MAX_SIZE),
    )
    
    # Initialize schema
    retry_delay = DB_RETRY_BASE_SECONDS
    while True:
        try:
            async with db_pool.acquire() as conn:
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
            await db_pool.expire_connections()
    
    print(
        f"{datetime.now(timezone.utc).isoformat()} UBI service started with interval "
        f"{settings['interval_seconds']}s"
    )
    
    # Start the UBI tick loop in background
    ubi_task = asyncio.create_task(ubi_tick_loop(db_pool), name="ubi_tick_loop")
    
    yield
    
    # Shutdown - graceful cleanup
    print(f"{datetime.now(timezone.utc).isoformat()} UBI service shutting down...")
    if ubi_task:
        ubi_task.cancel()
        try:
            await asyncio.wait_for(ubi_task, timeout=5.0)
        except asyncio.TimeoutError:
            print(f"{datetime.now(timezone.utc).isoformat()} UBI tick loop did not cancel in time, forcing...")
            ubi_task.cancel()
        except asyncio.CancelledError:
            pass
    if db_pool:
        await db_pool.close()
    print(f"{datetime.now(timezone.utc).isoformat()} UBI service shutdown complete")


app = FastAPI(title="UBI Service", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ubi"}


@app.get("/settings")
async def get_settings():
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    async with db_pool.acquire() as conn:
        settings = await get_runtime_settings(conn)
    return {
        "interval_seconds": settings["interval_seconds"],
        "dena_annual": str(settings["dena_annual"]),
        "dena_precision": settings["dena_precision"],
        "entity_types": settings["entity_types"],
    }


async def verify_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify that the user is an admin.
    
    Checks (in order):
    1. API key (if UBI_API_KEY is set)
    2. JWT token from PIdP (which checks SpiceDB for admin status)
    """
    # First check API key if configured
    if UBI_API_KEY:
        if credentials and credentials.credentials == UBI_API_KEY:
            return {"is_admin": True, "auth_method": "api_key"}
    
    # Otherwise, require Bearer token from PIdP
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Validate token with PIdP - PIdP checks SpiceDB for admin status
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Get user info from PIdP (includes is_admin from SpiceDB)
            resp = await client.get(
                f"{PIDP_BASE_URL}/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            if not resp.is_success:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            pidp_user = resp.json()
            user_id = str(pidp_user.get("id"))
            email = pidp_user.get("email")
            is_admin = pidp_user.get("is_admin", False)
            
            if not user_id or not email:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            if not is_admin:
                raise HTTPException(status_code=403, detail="Admin access required")
            
            return {
                "id": user_id,
                "email": email,
                "is_admin": True,
                "auth_method": "jwt",
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


@app.post("/update")
async def update_settings(
    interval_seconds: int = Form(...),
    dena_annual: float = Form(...),
    dena_precision: int = Form(...),
    entity_types: str = Form(...),
    admin_user: dict = Depends(verify_admin),
):
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with db_pool.acquire() as conn:
        await update_runtime_settings(
            conn,
            interval_seconds=interval_seconds,
            dena_annual=Decimal(str(dena_annual)),
            dena_precision=dena_precision,
            entity_types=entity_types,
            updated_by=admin_user.get("email", "admin"),
        )
    
    # Redirect back to home with success
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/?success=1", status_code=303)


@app.post("/api/settings")
async def update_settings_api(
    interval_seconds: int = Form(None),
    dena_annual: float = Form(None),
    dena_precision: int = Form(None),
    entity_types: str = Form(None),
    admin_user: dict = Depends(verify_admin),
):
    """API endpoint to update UBI settings (requires API key)."""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with db_pool.acquire() as conn:
        settings = await update_runtime_settings(
            conn,
            interval_seconds=interval_seconds,
            dena_annual=Decimal(str(dena_annual)) if dena_annual is not None else None,
            dena_precision=dena_precision,
            entity_types=entity_types,
            updated_by="api",
        )
    
    return {
        "status": "success",
        "settings": {
            "interval_seconds": settings["interval_seconds"],
            "dena_annual": str(settings["dena_annual"]),
            "dena_precision": settings["dena_precision"],
            "entity_types": settings["entity_types"],
        }
    }


@app.get("/", response_class=HTMLResponse)
async def home(success: int = 0):
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with db_pool.acquire() as conn:
        settings = await get_runtime_settings(conn)
    
    amount = dena_per_tick(settings["dena_annual"], settings["dena_precision"])
    
    success_message = '<div class="success">✓ Settings updated successfully!</div>' if success else ""
    if UBI_API_KEY:
        auth_status = "<span style='color: #f44336;'>🔒 Protected (API key)</span>"
    elif UBI_ADMIN_USER_IDS:
        auth_status = "<span style='color: #2196f3;'>🔒 Protected (Admin users)</span>"
    else:
        auth_status = "<span style='color: #f44336;'>🔒 Protected (PIdP admin required)</span>"
    
    html = HOME_PAGE_TEMPLATE.format(
        current_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        interval_seconds=settings["interval_seconds"],
        dena_annual=settings["dena_annual"],
        dena_precision=settings["dena_precision"],
        entity_types=",".join(settings["entity_types"]),
        dena_per_tick=amount,
        auth_status=auth_status,
        success_message=success_message,
    )
    return html


# Legacy run function for backward compatibility
async def run() -> None:
    """Run the UBI service (legacy mode - just the tick loop without web server)."""
    import uvicorn
    await uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    import uvicorn
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        print(f"{datetime.now(timezone.utc).isoformat()} UBI service stopped by user")
    except Exception as e:
        print(f"{datetime.now(timezone.utc).isoformat()} UBI service crashed: {e}")
        raise

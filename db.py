"""
Supabase database layer.

- Auto-creates tables on startup if missing
- Stores user info and updates on every /start
- Provides stats helpers
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from supabase import Client, create_client

import config

log = logging.getLogger(__name__)

# ---------- Client ----------
_client: Optional[Client] = None

def get_client() -> Client:
    global _client
    if _client is None:
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise SystemExit(
                "ERROR: SUPABASE_URL and SUPABASE_KEY must be set "
                "(in .env locally or Railway Variables in production)."
            )
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _client


# ---------- Bootstrap (create tables if missing) ----------
BOOTSTRAP_SQL = """
create table if not exists users (
    telegram_id    bigint primary key,
    username       text,
    first_name     text,
    last_name      text,
    language_code  text,
    is_premium     boolean default false,
    is_blocked     boolean default false,
    start_count    integer default 1,
    joined_at      timestamptz default now(),
    last_seen_at   timestamptz default now()
);

create table if not exists button_clicks (
    id           bigserial primary key,
    telegram_id  bigint references users(telegram_id) on delete cascade,
    button_text  text,
    button_url   text,
    clicked_at   timestamptz default now()
);

create index if not exists idx_users_username     on users(username);
create index if not exists idx_users_last_seen    on users(last_seen_at);
create index if not exists idx_clicks_telegram_id on button_clicks(telegram_id);
create index if not exists idx_clicks_button_text on button_clicks(button_text);
"""

def ensure_schema() -> None:
    """
    Try to use the tables. If they don't exist, give a helpful error.

    Note: Supabase's Python client can't run arbitrary DDL — that's a Postgres
    privilege issue, not a library limitation. So we VERIFY the tables exist
    and instruct the admin to run the SQL once if not. The SQL is shown below.
    """
    client = get_client()
    try:
        # Try a harmless read — if the table doesn't exist this raises
        client.table("users").select("telegram_id").limit(1).execute()
        log.info("Supabase: 'users' table OK")
    except Exception as e:
        msg = str(e).lower()
        if "does not exist" in msg or "relation" in msg or "schema cache" in msg:
            log.error(
                "Supabase tables are missing. Run this SQL once in Supabase "
                "SQL Editor:\n\n%s",
                BOOTSTRAP_SQL,
            )
            raise SystemExit(
                "Supabase tables not found. See logs above for the SQL to run."
            )
        # Different error — re-raise
        raise

    try:
        client.table("button_clicks").select("id").limit(1).execute()
        log.info("Supabase: 'button_clicks' table OK")
    except Exception as e:
        msg = str(e).lower()
        if "does not exist" in msg or "relation" in msg or "schema cache" in msg:
            log.warning(
                "'button_clicks' table missing — that's OK if you don't use click "
                "tracking. To enable, run this in Supabase SQL Editor:\n\n%s",
                BOOTSTRAP_SQL,
            )
        else:
            raise


# ---------- User operations ----------
def upsert_user(
    telegram_id: int,
    username: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    language_code: Optional[str],
    is_premium: bool,
) -> None:
    """
    Insert or update a user. If they already exist:
    - update username/name/language/premium (in case they changed)
    - increment start_count
    - refresh last_seen_at
    - clear is_blocked flag (they're back!)
    """
    client = get_client()
    now = datetime.now(timezone.utc).isoformat()

    existing = (
        client.table("users")
        .select("start_count")
        .eq("telegram_id", telegram_id)
        .execute()
    )

    if existing.data:
        new_count = (existing.data[0].get("start_count") or 0) + 1
        client.table("users").update({
            "username": username or "",
            "first_name": first_name or "",
            "last_name": last_name or "",
            "language_code": language_code or "",
            "is_premium": bool(is_premium),
            "is_blocked": False,
            "start_count": new_count,
            "last_seen_at": now,
        }).eq("telegram_id", telegram_id).execute()
    else:
        client.table("users").insert({
            "telegram_id": telegram_id,
            "username": username or "",
            "first_name": first_name or "",
            "last_name": last_name or "",
            "language_code": language_code or "",
            "is_premium": bool(is_premium),
            "is_blocked": False,
            "start_count": 1,
            "joined_at": now,
            "last_seen_at": now,
        }).execute()


def mark_user_blocked(telegram_id: int) -> None:
    """User blocked the bot — flag them so we skip in future broadcasts."""
    client = get_client()
    client.table("users").update({"is_blocked": True}).eq(
        "telegram_id", telegram_id
    ).execute()


def get_all_active_user_ids() -> list[int]:
    """All users who haven't blocked the bot — for broadcasts."""
    client = get_client()
    res = (
        client.table("users")
        .select("telegram_id")
        .eq("is_blocked", False)
        .execute()
    )
    return [row["telegram_id"] for row in res.data]


# ---------- Stats ----------
def get_stats() -> dict:
    """Aggregate stats for the /stats command."""
    client = get_client()

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    all_users = client.table("users").select(
        "telegram_id, is_blocked, is_premium, language_code, joined_at"
    ).execute().data

    total = len(all_users)
    blocked = sum(1 for u in all_users if u.get("is_blocked"))
    active = total - blocked
    premium = sum(1 for u in all_users if u.get("is_premium"))

    def joined_after(iso_cutoff):
        cutoff = iso_cutoff.isoformat()
        return sum(1 for u in all_users if (u.get("joined_at") or "") >= cutoff)

    new_today = joined_after(today_start)
    new_week = joined_after(week_start)
    new_month = joined_after(month_start)

    # Top languages
    langs: dict[str, int] = {}
    for u in all_users:
        code = u.get("language_code") or "?"
        langs[code] = langs.get(code, 0) + 1
    top_langs = sorted(langs.items(), key=lambda x: -x[1])[:5]

    return {
        "total": total,
        "active": active,
        "blocked": blocked,
        "premium": premium,
        "premium_pct": round((premium / total * 100), 1) if total else 0,
        "new_today": new_today,
        "new_week": new_week,
        "new_month": new_month,
        "top_langs": top_langs,
    }

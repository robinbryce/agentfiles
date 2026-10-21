"""Tunables, read from the environment at call time so tests can patch them."""
from __future__ import annotations
import os

STATUSES = ("active", "parked", "blocked", "landed", "closed")
NOTE_KINDS = ("followup", "tangent", "reminder")
DEFAULT_SCOPES = ("justgames", "forestrie", "home", "personal")
# agentfiles profiles; each is a config dir ~/.claude-<profile> and serves the Scope of the same name
PROFILES = ("justgames", "personal", "forestrie", "home")


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def ring() -> int: return max(1, _int("WIF_RING", 10))
def stream_cap() -> int: return _int("WIF_STREAM_CAP", 120)
def stale_days() -> int: return _int("WIF_STALE_DAYS", 14)
def rotate_pct() -> int: return _int("WIF_ROTATE_PCT", 60)
def pr_ttl() -> int: return _int("WIF_PR_TTL", 6 * 3600)
def session_keep_days() -> int: return _int("WIF_SESSION_KEEP_DAYS", 30)
def budget_lines() -> int: return _int("WIF_BUDGET_LINES", 40)

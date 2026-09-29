"""Sign in with Google or Discord (OAuth 2 authorization code flow, run by the server).

The browser asks the server for a sign-in URL (carrying its current profile, so a guest can become
an account), the provider sends the player back to /auth/<provider>/callback, the server swaps
the code for the player's provider account id, and hands the browser a one-time code that it
redeems for its own session key. Client secrets never leave the server.

Credentials come from the environment (on Fly: `fly secrets set`), or locally from the untracked
`results/oauth.json` ({"AK_GOOGLE_ID": ..., ...}). A provider without credentials is not offered.
"""

from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path
from typing import Optional

import aiohttp
from yarl import URL

LOCAL_CREDENTIALS = Path(__file__).resolve().parents[2] / "results" / "oauth.json"
PENDING_TTL = 600      # seconds a player has to finish signing in at the provider
HANDOFF_TTL = 60       # seconds the browser has to redeem its one-time code

PROVIDERS = {
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "userinfo": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email",
        "subject": lambda u: u["sub"],
        "label": lambda u: u.get("email") or "Google account",
    },
    "discord": {
        "authorize": "https://discord.com/oauth2/authorize",
        "token": "https://discord.com/api/oauth2/token",
        "userinfo": "https://discord.com/api/users/@me",
        "scope": "identify",
        "subject": lambda u: u["id"],
        "label": lambda u: u.get("global_name") or u.get("username") or "Discord account",
    },
}


class OAuthError(Exception):
    pass


def _credentials(provider: str) -> Optional[tuple[str, str]]:
    env = dict(os.environ)
    if LOCAL_CREDENTIALS.is_file():
        env = {**json.loads(LOCAL_CREDENTIALS.read_text()), **env}
    cid, secret = env.get(f"AK_{provider.upper()}_ID"), env.get(f"AK_{provider.upper()}_SECRET")
    return (cid, secret) if cid and secret else None


def available() -> list[str]:
    return [p for p in PROVIDERS if _credentials(p)]


class Flow:
    """The sign-ins in progress and the one-time codes waiting to be redeemed (in memory: a
    restart only means someone clicks Sign in again)."""

    def __init__(self):
        self.pending: dict[str, tuple[str, Optional[str], float]] = {}    # state -> (provider, guest, t)
        self.handoffs: dict[str, tuple[str, float]] = {}                   # one-time code -> (session key, t)

    def start(self, provider: str, guest: Optional[str], redirect_uri: str) -> str:
        creds = _credentials(provider)
        if provider not in PROVIDERS or not creds:
            raise OAuthError(f"{provider} sign-in isn't set up")
        now = time.time()
        self.pending = {k: v for k, v in self.pending.items() if now - v[2] < PENDING_TTL}
        state = secrets.token_urlsafe(24)
        self.pending[state] = (provider, guest, now)
        cfg = PROVIDERS[provider]
        q = {"client_id": creds[0], "redirect_uri": redirect_uri, "response_type": "code",
             "scope": cfg["scope"], "state": state, "prompt": "select_account" if provider == "google" else "none"}
        return str(URL(cfg["authorize"]).with_query(q))

    def claim(self, provider: str, state: str) -> Optional[str]:
        """The guest profile a callback's `state` was started from; raises if the state is unknown."""
        entry = self.pending.pop(state, None)
        if not entry or entry[0] != provider or time.time() - entry[2] > PENDING_TTL:
            raise OAuthError("that sign-in expired, try again")
        return entry[1]

    def hand_off(self, session_key: str) -> str:
        now = time.time()
        self.handoffs = {k: v for k, v in self.handoffs.items() if now - v[1] < HANDOFF_TTL}
        code = secrets.token_urlsafe(24)
        self.handoffs[code] = (session_key, now)
        return code

    def redeem(self, code: str) -> Optional[str]:
        entry = self.handoffs.pop(code, None)
        return entry[0] if entry and time.time() - entry[1] < HANDOFF_TTL else None


async def identify(provider: str, code: str, redirect_uri: str) -> tuple[str, str]:
    """Swap an authorization code for (provider account id, a label to show: email or username)."""
    cfg, (cid, secret) = PROVIDERS[provider], _credentials(provider)
    form = {"client_id": cid, "client_secret": secret, "code": code,
            "grant_type": "authorization_code", "redirect_uri": redirect_uri}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as http:
        async with http.post(cfg["token"], data=form, headers={"Accept": "application/json"}) as r:
            if r.status != 200:
                raise OAuthError(f"{provider} refused the sign-in ({r.status})")
            token = (await r.json())["access_token"]
        async with http.get(cfg["userinfo"], headers={"Authorization": f"Bearer {token}"}) as r:
            if r.status != 200:
                raise OAuthError(f"couldn't read the {provider} account ({r.status})")
            user = await r.json()
    return str(cfg["subject"](user)), str(cfg["label"](user))

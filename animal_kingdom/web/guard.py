"""What the server checks before it trusts a request: the body's shape, the client's address, how often it may ask, and
which characters a player's text may carry. Also the access log, which never writes a sign-in key or a seat token.

Rate limits are per client address (on Fly the proxy's `Fly-Client-IP`, which Fly sets on every request; elsewhere the
socket's peer) or per profile, counted in memory over a sliding window: a restart forgets them, which is fine for limits
meant to stop a loop, not a person. A local server (./play, the test harnesses) exempts its own machine's address.
"""

from __future__ import annotations

import os
import re
import time
import unicodedata
from collections import deque

from aiohttp import web
from aiohttp.web_log import AccessLogger

# name -> (requests, per seconds). Generous for a person (a household or a school behind one address included); a script
# looping on the route meets them within a minute.
LIMITS = {
    "profile": (30, 3600),      # new guest profiles, per address
    "signin": (30, 60),         # sign-in by code and the OAuth hand-off, per address
    "match": (40, 60),          # matches made or joined, per address
    "ranked": (20, 60),         # ranked searches, per profile
    "challenge": (20, 60),      # challenges sent, per profile
    "friend": (30, 60),         # friend links and requests, per profile
    "chat": (120, 60),          # chat messages, per address (chat.PER_MINUTE limits each profile)
    "feedback": (30, 3600),     # feedback messages, per address (feedback.PER_HOUR limits each profile)
    "mail": (60, 3600),         # feedback mails sent, server-wide: every message is a mail to Martin
}
LOCAL = {"127.0.0.1", "::1"}
SOCKET_MSG_MAX = 64 * 1024      # bytes in one socket message (the largest a client sends, a deck list, is under 2 KB)
SOCKET_BURST = (120, 10.0)      # socket messages a seat may send in that many seconds before the socket is closed


class Limiter:
    def __init__(self):
        self.hits: dict[tuple, deque] = {}

    def allow(self, name: str, key: str, now: float | None = None) -> bool:
        n, per = LIMITS[name]
        now = time.monotonic() if now is None else now
        q = self.hits.setdefault((name, key), deque())
        while q and now - q[0] >= per:
            q.popleft()
        if len(q) >= n:
            return False
        q.append(now)
        if len(self.hits) > 50_000:     # forget the idle keys now and then, so the table stays small
            self.hits = {k: v for k, v in self.hits.items() if v and now - v[-1] < LIMITS[k[0]][1]}
        return True


limiter = Limiter()


def on_fly() -> bool:
    return bool(os.environ.get("FLY_APP_NAME"))


def client_ip(req: web.Request) -> str:
    if on_fly() and req.headers.get("Fly-Client-IP"):
        return req.headers["Fly-Client-IP"]
    return req.remote or ""


def limit(name: str, key: str) -> None:
    """Raise 429 when `key` has used up the `name` limit. A local server's own machine is never limited."""
    if not key or (key in LOCAL and not on_fly()):
        return
    if not limiter.allow(name, key):
        raise web.HTTPTooManyRequests(text="too many requests: wait a minute and try again")


def limit_ip(req: web.Request, name: str) -> None:
    limit(name, client_ip(req))


async def body(req: web.Request, kind: type = dict):
    """The request's JSON body, which must be a `kind` (an empty body reads as an empty one); else 400."""
    if not req.can_read_body:
        return kind()
    try:
        data = await req.json()
    except ValueError:
        raise web.HTTPBadRequest(text="the body is not JSON")
    if not isinstance(data, kind):
        raise web.HTTPBadRequest(text=f"the body must be a JSON {'object' if kind is dict else 'list'}")
    return data


_NAME_DROP = {"Cc", "Cf", "Cs", "Co", "Cn"}   # control, format (bidi overrides, zero-width), surrogates, private, unassigned


def clean_text(text, *, name: bool = False) -> str:
    """A player's text as the server keeps it: a string, never a lone surrogate (it can't be stored) or a control
    character; a name also loses the invisible and direction-changing characters another name could be faked with."""
    if not isinstance(text, str):
        return ""
    drop = _NAME_DROP if name else {"Cs", "Cc"}
    keep_ws = "" if name else "\n\t"
    return "".join(ch for ch in text if ch in keep_ws or unicodedata.category(ch) not in drop)


_SECRET = re.compile(r"([?&](?:key|token)=)[^&\s\"]*")


class RedactingAccessLogger(AccessLogger):
    """aiohttp's access log, with the `key` (a profile's sign-in code) and `token` (a seat's) query values blanked:
    the sockets carry them in the URL, and a log line is no place for a credential."""

    def log(self, request, response, time):
        try:
            super().log(_Redacted(request), response, time)
        except Exception:
            self.logger.exception("access log failed")


class _Redacted:
    def __init__(self, req):
        self._req = req

    def __getattr__(self, attr):
        value = getattr(self._req, attr)
        if attr in ("path_qs", "rel_url", "url"):
            return _SECRET.sub(r"\1-", str(value))
        return value

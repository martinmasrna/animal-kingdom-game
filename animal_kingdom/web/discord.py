"""The Discord channels as the lobby: a few things the server knows, posted where the players already are.

Two webhooks, set as Fly secrets (locally in the untracked `results/oauth.json`, as for sign-in):
  DISCORD_WEBHOOK_FEEDBACK   every feedback message, so others can pile on;
  DISCORD_WEBHOOK_EVENTS     a person looking for a ranked match (so someone can queue too), a person beating the Expert
                             bot or another person, a newcomer finishing the tutorial.
Without a URL nothing is posted. Posting never blocks a request: it runs in a thread and failures are only logged.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request

from .oauth import LOCAL_CREDENTIALS

log = logging.getLogger("animal_kingdom.web")
QUEUE_QUIET = 10 * 60     # one "is looking for a match" per person in this many seconds
_last_queue_post: dict[str, float] = {}


def url(channel: str) -> str:
    env = dict(os.environ)
    if LOCAL_CREDENTIALS.is_file():
        env = {**json.loads(LOCAL_CREDENTIALS.read_text()), **env}
    return env.get(f"DISCORD_WEBHOOK_{channel.upper()}", "")


def post(channel: str, text: str) -> bool:
    """One message to a channel (blocking: run it in a thread). False without a webhook or on failure."""
    hook = url(channel)
    if not hook or not text:
        return False
    req = urllib.request.Request(hook, data=json.dumps({"content": text[:1900], "allowed_mentions": {"parse": []}}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "animal-kingdom"})
    try:
        with urllib.request.urlopen(req, timeout=10):
            return True
    except OSError:
        log.exception("could not post to Discord (%s)", channel)
        return False


def feedback_text(sender: str, text: str, context: dict) -> str:
    where = context.get("match") and f"turn {context.get('turn', '?')} of match {context['match']}" or context.get("screen", "")
    return f"**{sender}**" + (f" · {where}" if where else "") + f"\n{text}"


def queue_text(name: str, now: float | None = None) -> str:
    """'X is looking for a ranked match', at most once per person per QUEUE_QUIET; '' when it was said recently."""
    now = time.time() if now is None else now
    if now - _last_queue_post.get(name, 0) < QUEUE_QUIET:
        return ""
    _last_queue_post[name] = now
    return f"**{name}** is looking for a ranked match"


def result_text(winner: str, loser: str, winner_deck: str, loser_deck: str, loser_bot: str | None, lesson: int) -> str:
    """What is worth a line: a newcomer's finished tutorial, a win over the Expert bot, a win over a person. '' otherwise."""
    if lesson:
        return f"**{winner}** finished the tutorial" if lesson == 2 else ""
    if loser_bot == "expert":
        return f"**{winner}** beat the Expert bot's {loser_deck} with {winner_deck}"
    if loser_bot is None:
        return f"**{winner}** beat **{loser}** ({winner_deck} over {loser_deck})"
    return ""

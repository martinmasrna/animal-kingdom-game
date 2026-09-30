"""Player feedback: one free-text message with the moment it was sent from, kept and mailed to Martin.

The client adds what a player can't describe well: the screen, the match and turn, the window, and on the game
screen the seat's whole view (attached to the mail as view.json, so a bug arrives as the state it happened in).
Every message is kept in the profiles database (table `feedback`); the mail goes through Gmail's SMTP with an app
password when FEEDBACK_EMAIL and FEEDBACK_SMTP_PASSWORD are set (on Fly: `fly secrets set`; locally the untracked
`results/oauth.json`, as for sign-in). Without them a message is only kept.
"""

from __future__ import annotations

import json
import logging
import smtplib
import time
from email.message import EmailMessage

from .oauth import LOCAL_CREDENTIALS

TEXT_MAX = 4000
PER_HOUR = 10      # messages one sender can send an hour: every message is a mail
log = logging.getLogger("animal_kingdom.web")

SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback (
    sent REAL NOT NULL, profile TEXT NOT NULL, sender TEXT NOT NULL, text TEXT NOT NULL, context TEXT NOT NULL,
    view TEXT NOT NULL);
"""


class FeedbackError(ValueError):
    pass


def _credentials() -> tuple[str, str] | None:
    import os
    env = dict(os.environ)
    if LOCAL_CREDENTIALS.is_file():
        env = {**json.loads(LOCAL_CREDENTIALS.read_text()), **env}
    to, password = env.get("FEEDBACK_EMAIL"), env.get("FEEDBACK_SMTP_PASSWORD")
    return (to, password) if to and password else None


def keep(db, profile: str, sender: str, text: str, context: dict, view) -> None:
    """Store one message, after checking its length and the sender's rate."""
    text = str(text or "").strip()
    if not text:
        raise FeedbackError("write something first")
    if len(text) > TEXT_MAX:
        raise FeedbackError(f"keep it under {TEXT_MAX} characters")
    db.executescript(SCHEMA)
    recent = db.execute("SELECT COUNT(*) FROM feedback WHERE profile = ? AND sent > ?", (profile, time.time() - 3600)).fetchone()[0]
    if recent >= PER_HOUR:
        raise FeedbackError("that's a lot of messages: try again in an hour")
    with db:
        db.execute("INSERT INTO feedback VALUES (?, ?, ?, ?, ?, ?)",
                   (time.time(), profile, sender, text, json.dumps(context), json.dumps(view) if view else ""))


def subject(sender: str, context: dict) -> str:
    where = context.get("match") and f"turn {context.get('turn', '?')} of match {context['match']}" or context.get("screen", "")
    return f"Feedback: {sender}" + (f", {where}" if where else "")


def mail(sender: str, text: str, context: dict, view) -> bool:
    """Send one message to Martin (blocking: run it in a thread). False when there are no credentials or it failed."""
    creds = _credentials()
    if not creds:
        return False
    to, password = creds
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = to, to, subject(sender, context)
    msg.set_content(f"{text}\n\n--\n" + "\n".join(f"{k}: {v}" for k, v in context.items()))
    if view:
        msg.add_attachment(json.dumps(view, indent=1).encode(), maintype="application", subtype="json", filename="view.json")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as s:
            s.login(to, password)
            s.send_message(msg)
        return True
    except (OSError, smtplib.SMTPException):
        log.exception("could not mail feedback from %s", sender)
        return False

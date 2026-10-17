"""The Discord lobby lines (web/discord.py): what gets a line, what doesn't, and nothing posted without a webhook."""
import time

from animal_kingdom.web import discord


def test_nothing_is_posted_without_a_webhook(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_EVENTS", raising=False)
    monkeypatch.setattr(discord, "LOCAL_CREDENTIALS", type("P", (), {"is_file": staticmethod(lambda: False)})())
    assert discord.post("events", "hello") is False


def test_a_queue_line_is_said_once_per_person_per_quiet_window():
    discord._last_queue_post.clear()
    t = time.time()
    assert discord.queue_text("Ana#1", t) == "**Ana#1** is looking for a ranked match"
    assert discord.queue_text("Ana#1", t + 60) == ""
    assert discord.queue_text("Ana#1", t + discord.QUEUE_QUIET + 1) != ""
    assert discord.queue_text("Bo#2", t + 60) != ""


def test_results_worth_a_line():
    assert discord.result_text("Ana#1", "Bot (Expert)", "Cats", "Giants", "expert", 0) == "**Ana#1** beat the Expert bot's Giants with Cats"
    assert discord.result_text("Ana#1", "Bot (Normal)", "Cats", "Giants", "normal", 0) == ""
    assert discord.result_text("Ana#1", "Bo#2", "Cats", "their own deck", None, 0) == "**Ana#1** beat **Bo#2** (Cats over their own deck)"
    assert discord.result_text("Ana#1", "Wild dogs", "Cats", "Cats", "tutorial", 2) == "**Ana#1** finished the tutorial"
    assert discord.result_text("Ana#1", "Wild dogs", "Cats", "Cats", "tutorial", 1) == ""


def test_feedback_line_carries_the_moment():
    assert discord.feedback_text("Ana#1", "the Hornet did nothing", {"match": "ABC", "turn": 5}) == "**Ana#1** · turn 5 of match ABC\nthe Hornet did nothing"
    assert discord.feedback_text("Ana#1", "hi", {"screen": "#/collection"}) == "**Ana#1** · #/collection\nhi"

"""Every bot the web server ships builds, its learned evaluation included. A change to what the bots' features read (a new
tag in engine/cards.py, 2026-10-24) makes a trained network's schema hash stale; the server then answers every match
against that bot with a 500, so it fails here, at commit time, in the session that made it."""
import pytest

from animal_kingdom.web.match import BOT_LEVELS, bot_for


@pytest.mark.parametrize("level", sorted(BOT_LEVELS))
def test_a_shipped_bot_builds(level):
    assert bot_for(level, 0) is not None

"""The ranked bots' pool (web/pool.py): the premade decks today's cards allow, and a rating that follows a card change."""

import json
from dataclasses import replace

import ak_engine

from animal_kingdom import game
from animal_kingdom.web import ladder, pool
from animal_kingdom.web.match import BOT_LEVELS, PRACTICE_BOT

LIST = [f"wisp_{n}" for n in range(1, 7) for _ in range(2)] + [f"flight_{n}" for n in range(1, 7) for _ in range(2)] + ["warlord_legend"]
WISPS = {"slug": "wisps", "name": "Wisps", "leader": "warlord_legend", "cards": LIST}
OTHER = {"slug": "other", "name": "Other", "leader": "sage_legend",
         "cards": [f"hunter_{n}" for n in range(2, 8) for _ in range(2)] + [f"flight_{n}" for n in range(1, 7) for _ in range(2)] + ["sage_legend"]}


def test_the_levels_are_the_ladders_and_each_is_a_bot_the_engine_knows():
    assert tuple(BOT_LEVELS) == ladder.LEVELS and BOT_LEVELS[ladder.LEVELS[-1]] == PRACTICE_BOT
    for spec in BOT_LEVELS.values():
        ak_engine.Bot(spec, 1)


def test_a_deck_a_card_change_made_illegal_is_out_of_the_pool():
    assert pool.legal([WISPS, OTHER]) == [WISPS, OTHER]
    without = {cid: c for cid, c in game.CARDS.items() if cid != "wisp_3"}   # the card left the game
    assert pool.legal([WISPS, OTHER], cards=without) == [OTHER]
    uncollectible = {**game.CARDS, "hunter_4": replace(game.CARDS["hunter_4"], status="reserve")}
    assert pool.legal([WISPS, OTHER], cards=uncollectible) == [WISPS]


def test_the_pools_decks_can_be_played_under_their_own_slugs_and_names():
    from animal_kingdom.decks import DECK_LEADERS, load_deck
    from animal_kingdom.web.match import DECK_NAMES
    assert len({d["slug"] for d in pool.premade()}) == len(pool.premade()), "two premade decks share a slug"
    for d in pool.load():
        assert (load_deck(d["slug"]), DECK_LEADERS[d["slug"]], DECK_NAMES[d["slug"]]) == (d["cards"], d["leader"], d["name"])


def _seed():
    levels = {lv: {"bot": BOT_LEVELS[lv], "rating": 1000.0 + 100 * int(lv)} for lv in ladder.LEVELS}
    rows = {ladder.bot_id(lv, d["slug"]): {"rating": 1000.0 + 100 * int(lv) + (30 if d is WISPS else -30), "with": pool.measured_with(lv, d)}
            for d in (WISPS, OTHER) for lv in ladder.LEVELS}
    return {"version": "v1", "levels": levels, "ratings": rows}


def test_a_bot_starts_from_the_seed_while_it_plays_with_what_was_measured():
    rows = pool.ratings([WISPS, OTHER], _seed())
    assert rows["bot:5:wisps"][:2] == (1530.0, ladder.BOT_RD) and rows["bot:1:other"][:2] == (1070.0, ladder.BOT_RD)
    assert len(rows) == 10 and len({r[2] for r in rows.values()}) == 10


def test_a_card_change_puts_the_decks_that_hold_the_card_on_their_levels_rating():
    """The Wisp 3 costs one more: the Wisps deck's rating was measured with another card. Its bots stand on their level's
    rating, less sure, and under a new source so the ladder sets them; the other deck's numbers stay as they are."""
    seed = _seed()
    changed = {**game.CARDS, "wisp_3": replace(game.CARDS["wisp_3"], cost=game.CARDS["wisp_3"].cost + 1)}
    before, after = pool.ratings([WISPS, OTHER], seed), pool.ratings([WISPS, OTHER], seed, cards=changed)
    assert after["bot:5:wisps"][:2] == (1500.0, ladder.UNMEASURED_RD) and after["bot:5:wisps"][2] != before["bot:5:wisps"][2]
    assert all(after[lid] == before[lid] for lid in after if lid.endswith(":other"))
    # the same when the deck's own list changed, or the game is played on another map
    swapped = {**WISPS, "cards": LIST[:-3] + ["cantrip_2", "cantrip_2", "warlord_legend"]}
    assert pool.ratings([swapped], seed)["bot:3:wisps"][:2] == (1300.0, ladder.UNMEASURED_RD)
    other_map = "map_sq16" if game.MAP_ID != "map_sq16" else "map_hex19"
    assert all(r[1] == ladder.UNMEASURED_RD for r in pool.ratings([WISPS, OTHER], seed, map_id=other_map).values())


def test_a_card_a_deck_makes_counts_as_the_decks_own():
    spores = {**WISPS, "cards": LIST[:-3] + ["mama_spore", "mama_spore", "warlord_legend"]}
    changed = {**game.CARDS, "spore": replace(game.CARDS["spore"], base_strength=2)}
    assert pool.measured_with("5", spores) != pool.measured_with("5", spores, cards=changed)
    assert pool.measured_with("5", WISPS) == pool.measured_with("5", WISPS, cards=changed)


def test_with_no_seed_or_another_bot_at_the_level_a_bot_starts_where_its_level_was_last_measured():
    assert pool.ratings([WISPS], {})["bot:4:wisps"][:2] == (ladder.LEVEL_START["4"], ladder.UNMEASURED_RD)
    seed = _seed(); seed["levels"]["4"]["bot"] = "turn:budget=5"   # the level is another bot now: its old mean says nothing
    seed["ratings"]["bot:4:wisps"]["with"] = "measured-with-the-old-bot"
    assert pool.ratings([WISPS], seed)["bot:4:wisps"][0] == ladder.LEVEL_START["4"]


def test_the_shipped_seed_was_measured_with_the_levels_that_play():
    """The seed is measured again after a card change, and nothing waits on that (web/pool.py). A level's own bot is code:
    changing it means measuring again before it ships."""
    seed = json.loads(pool.SEED_FILE.read_text(encoding="utf-8"))
    assert {lv: row["bot"] for lv, row in seed["levels"].items()} == BOT_LEVELS, "run tools/ladder/seed.py: a level's bot changed"
    ratings = [seed["levels"][lv]["rating"] for lv in ladder.LEVELS]
    assert ratings == sorted(ratings), "each level is stronger than the one under it"

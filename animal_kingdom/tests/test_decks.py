

def test_a_starters_copy_count_does_not_cap_other_decks():
    """Python and Rattlesnake are 2 in the Egg starter (cards.json `copies`), but any deck may hold a common's 3 (Martin, 2026-10-01)."""
    from animal_kingdom.decks import PREMADE_DECKS, decklist_problems
    egg = PREMADE_DECKS["egg_control"]
    assert egg.count("goliath") == 2 and egg.count("rattlesnake") == 2
    deck = [c for c in egg if c not in ("goliath", "rattlesnake")]
    deck = deck[:24] + ["goliath"] * 3 + ["rattlesnake"] * 3
    assert len(deck) == 30 and not [p for p in decklist_problems(deck) if "Python" in p or "Rattlesnake" in p or "goliath" in p or "rattlesnake" in p]
    assert decklist_problems(deck[:26] + ["goliath"] * 4)   # a fourth is still too many

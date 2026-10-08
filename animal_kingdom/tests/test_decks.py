

def test_a_starters_copy_count_does_not_cap_other_decks():
    """A card's `copies` sizes its starter deck only: any deck may hold its rarity's full count (Martin, 2026-10-01).
    No launch starter sets `copies`; a card that did would still allow 3 of a common elsewhere."""
    from animal_kingdom.decks import PREMADE_DECKS, decklist_problems
    from animal_kingdom.engine.cards import load_cards
    cards = load_cards()
    two = {cid: rec for cid, rec in cards.items()}
    import dataclasses
    two["goliath"] = dataclasses.replace(cards["goliath"], copies=2)
    egg = PREMADE_DECKS["egg_control"]
    deck = [c for c in egg if c != "goliath"][:27] + ["goliath"] * 3
    assert len(deck) == 30 and not [p for p in decklist_problems(deck, cards=two) if "Python" in p]
    assert decklist_problems(deck[:26] + ["goliath"] * 4, cards=two)   # a fourth is still too many

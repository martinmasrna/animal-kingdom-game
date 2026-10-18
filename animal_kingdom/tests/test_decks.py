

def test_a_starters_copy_count_does_not_cap_other_decks():
    """A card's `copies` sizes its starter deck only: any deck may hold its rarity's full count (Martin, 2026-10-01).
    No launch starter sets `copies`; a card that did would still allow 3 of a common elsewhere."""
    from animal_kingdom.decks import PREMADE_DECKS, decklist_problems
    from animal_kingdom.engine.cards import load_cards
    cards = load_cards()
    two = {cid: rec for cid, rec in cards.items()}
    import dataclasses
    two["python"] = dataclasses.replace(cards["python"], copies=2)
    egg = PREMADE_DECKS["egg_control"]
    deck = [c for c in egg if c != "python"][:27] + ["python"] * 3
    assert len(deck) == 30 and not [p for p in decklist_problems(deck, cards=two) if "Python" in p]
    assert decklist_problems(deck[:26] + ["python"] * 4, cards=two)   # a fourth is still too many


def test_a_deck_recipe_holds_collectible_cards_only():
    """The optimizer's recipes stay inside what a player can build: no reserve designs, no tokens,
    and the built-in seed obeys the same rule (a stale seed once smuggled Polar Bear into a result)."""
    import pytest
    from animal_kingdom.engine.cards import COLLECTIBLE_SLUGS, load_cards
    from animal_kingdom.sim.deck_optimizer import SEED_RECIPE, make_recipe

    cards = load_cards()
    assert all(cards[cid].deck in COLLECTIBLE_SLUGS for cid in SEED_RECIPE.all_ids())
    with pytest.raises(ValueError, match="polar_bear"):
        make_recipe(SEED_RECIPE.legendary, ("jaguar", "hawk", "polar_bear", "rhinoceros"), SEED_RECIPE.common)
    with pytest.raises(ValueError, match="listed under"):
        make_recipe(SEED_RECIPE.legendary, SEED_RECIPE.rare, ("lion", "tiger", "mouse", "wolf", "eagle", "jaguar"))



def test_any_deck_may_hold_a_cards_full_count():
    """A deck may hold its rarity's full count of any collectible card, whatever its starter deck holds (Martin,
    2026-10-01); a card carries no count of its own, the decklists do."""
    from animal_kingdom.decks import PREMADE_DECKS, decklist_problems
    egg = PREMADE_DECKS["egg_control"]
    deck = [c for c in egg if c != "python"][:27] + ["python"] * 3
    assert len(deck) == 30 and not [p for p in decklist_problems(deck) if "Python" in p]
    assert decklist_problems(deck[:26] + ["python"] * 4)   # a fourth is still too many


def test_a_deck_recipe_holds_collectible_cards_only():
    """The optimizer's recipes stay inside what a player can build: no reserve designs, no tokens,
    and the built-in seed obeys the same rule (a stale seed once smuggled Polar Bear into a result)."""
    import pytest
    from animal_kingdom.engine.cards import load_cards
    from animal_kingdom.sim.deck_optimizer import SEED_RECIPE, make_recipe

    cards = load_cards()
    assert all(cards[cid].collectible for cid in SEED_RECIPE.all_ids())
    with pytest.raises(ValueError, match="polar_bear"):
        make_recipe(SEED_RECIPE.legendary, ("jaguar", "hawk", "polar_bear", "rhinoceros"), SEED_RECIPE.common)
    with pytest.raises(ValueError, match="listed under"):
        make_recipe(SEED_RECIPE.legendary, SEED_RECIPE.rare, ("lion", "tiger", "mouse", "wolf", "eagle", "jaguar"))

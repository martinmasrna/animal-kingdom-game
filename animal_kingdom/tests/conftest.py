"""The leaders prototype (branch leaders): the tests of cards whose text changed with it test the old text, so they are
skipped here; test_leaders.py tests the new ones. Never merged, so the old tests stay as they are on main."""

import pytest

# Queen Solenia (a Roar now, no Dusk), Lord Bumbleton (a Roar now, no rider, no Flight), Babaji (Echo and a Roar, no
# Dawn), Lady Juliette (a wish, no royal jelly), Xanthe's card (no Dawn evolution), the common Caterpillar (on the board
# too).
CHANGED_CARD_TESTS = (
    "test_meadow.py::test_caterpillar_in_hand_gaining_strength_draws_and_becomes_a_butterfly_but_not_on_the_board",
    "test_rulings.py::test_launch_cards__legendary_butterfly_evolves_at_dawn_in_hand_too",
    "test_rulings.py::test_launch_cards__legendary_butterfly_evolving_on_the_board_fires_no_roar_and_buried_doesnt_evolve",
    "test_rulings.py::test_launch_cards__legendary_baboon_two_random_cards",
    "test_jungle.py::test_sloth_legend_doubles_your_dusk_effects_only",
    "test_jungle.py::test_army_ant_legend_dusk_gains_two_food_for_each_animal_you_control",
    "test_jungle.py::test_army_ant_legend_does_not_count_a_buried_ally_and_not_at_the_opponents_dusk",
    "test_meadow.py::test_bee_legend_2_gives_plus_two_everywhere_with_a_small_starting_deck",
    "test_meadow.py::test_bumblebee_legend_adds_three_to_each_food_gain_of_yours_only",
    "test_meadow.py::test_bumblebee_legend_rides_on_region_income_and_not_when_buried",
    "test_meadow.py::test_bumblebee_legend_has_flight",
    "test_meadow.py::test_butterfly_legend_evolves_at_dawn_on_the_board",
    "test_actions_prototype.py::test_food_from_an_action_counts_as_food_gained_and_meets_the_riders",
    "test_effects.py::test_bumbleton_rider_lands_on_a_colony_roar",
    "test_effects.py::test_queen_solenia_pays_at_dusk_for_every_animal_you_control",
    "test_effects.py::test_falstaffs_extra_food_is_its_own_doing",
    "test_decision_g_caps.py::test_falstaff_capped_limits_rider_to_one_gain_event_per_turn",
    "test_savanna.py::test_baboon_legend_gives_two_random_hand_animals_plus_one_at_dawn",
    "test_savanna.py::test_baboon_legend_with_one_animal_in_hand_gives_it_plus_one",
    "test_launch_cards.py::test_the_legendary_butterfly_moves_one_stage_per_buff",
    "test_launch_cards.py::test_baboon_trains_two_different_cards_and_the_legend_two_random_ones_at_dawn",
    "test_launch_cards.py::test_the_legendary_sardines_doubled_fish_count_as_two_animals_for_the_worker_ant_and_queen_solenia",
    "test_launch_cards.py::test_royal_jelly_gives_your_animals_two_wherever_they_are_when_the_starting_deck_is_small",
    "test_launch_cards.py::test_royal_jelly_adds_to_a_pythons_growth_and_never_resets_it",
    "test_new_keywords.py::test_existing_dusk_cards_still_fire",
)


def pytest_collection_modifyitems(config, items):
    mark = pytest.mark.skip(reason="leaders prototype: this card's text changed (test_leaders.py tests the new one)")
    for item in items:
        if any(item.nodeid.endswith(t) for t in CHANGED_CARD_TESTS):
            item.add_marker(mark)

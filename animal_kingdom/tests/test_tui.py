from __future__ import annotations

import asyncio
from pathlib import Path

from textual.widgets import Static

from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import UnitInstance, new_game
from animal_kingdom.recording.cohort import generate_manifest
from animal_kingdom.tui.app import ActionCard, BoardWidget, CardShelf, RecorderApp, build_parser


def _human_first_seed() -> int:
    for seed in range(100):
        state = new_game(
            load_premade_deck("ramp"),
            load_premade_deck("egg_control"),
            seed,
            map_id="map_b",
        )
        if state.first_player == "A":
            return seed
    raise AssertionError("no human-first seed found")


def _manifest():
    return generate_manifest(
        cohort_id="ui-test",
        human_decks=("ramp",),
        opponent_decks=("egg_control",),
        opponent_kinds=("random",),
        repetitions=1,
        seats=("A",),
        base_seed=_human_first_seed(),
        schedule_seed=0,
        map_id="map_b",
        config=Config(),
    )


def test_tui_80x24_keyboard_draw_and_annotations(tmp_path):
    async def scenario():
        app = RecorderApp(manifest=_manifest(), output_root=Path(tmp_path))
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            assert app.session is not None and app.session.human_turn
            board = app.query_one(BoardWidget)
            assert board.board_render is not None
            assert board.board_render.width <= board.size.width
            assert board.board_render.height <= board.size.height
            own_hq = board.board_render.hitboxes[("hq", "A")]
            enemy_hq = board.board_render.hitboxes[("hq", "B")]
            assert own_hq.x < enemy_hq.x and own_hq.y > enemy_hq.y
            hand_cards = [
                widget for widget in app.query(ActionCard)
                if isinstance(widget.entry.payload, tuple)
            ]
            assert hand_cards
            assert all(widget.entry.effect and widget.entry.stats.startswith("STR ") for widget in hand_cards)
            assert "STR" in app.export_screenshot()

            await pilot.press("d")
            await pilot.pause()
            assert app.session.decision_count >= 1
            await pilot.press("m")
            await pilot.press("g")
            assert not app.session.game_valid
            assert not app.session.decision_validity[app.session.human_decisions[-1]]
            await pilot.press("q")

    asyncio.run(scenario())


def test_tui_click_card_then_board_target(tmp_path):
    async def scenario():
        app = RecorderApp(manifest=_manifest(), output_root=Path(tmp_path))
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            card = next(
                widget for widget in app.query(ActionCard)
                if isinstance(widget.entry.payload, tuple)
                and widget.entry.payload[0] == "card"
            )
            await pilot.click(f"#{card.id}")
            await pilot.pause()
            assert app.selected_card is not None
            assert app.target_map

            target = next(iter(app.target_map))
            hitbox = app.query_one(BoardWidget).board_render.hitboxes[target]
            before = app.session.decision_count
            await pilot.click("#board", offset=(hitbox.x + 1, hitbox.y + 1))
            await pilot.pause()
            assert app.session.decision_count > before

    asyncio.run(scenario())


def test_tui_wide_layout_centers_board_and_labels_players(tmp_path):
    async def scenario():
        app = RecorderApp(manifest=_manifest(), output_root=Path(tmp_path))
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()

            board = app.query_one(BoardWidget)
            assert board.board_render is not None
            hitboxes = board.board_render.hitboxes.values()
            left = min(hitbox.x for hitbox in hitboxes)
            right = max(hitbox.x + hitbox.width for hitbox in hitboxes)
            top = min(hitbox.y for hitbox in hitboxes)
            bottom = max(hitbox.y + hitbox.height for hitbox in hitboxes)
            assert left > 0 and top > 0
            assert abs(left - (board.size.width - right)) <= 1
            assert abs(top - (board.size.height - bottom)) <= 1

            status = str(app.query_one("#status", Static).content)
            assert "Your turn" in status
            assert "Turn 1" in status
            assert "OPPONENT · Seat B" in str(app.query_one("#opponent", Static).content)
            player = str(app.query_one("#player", Static).content)
            assert "YOU · Seat A" in player
            assert "Food 0" in player
            assert "Actions 2" in player

    asyncio.run(scenario())


def test_tui_pending_choice_can_be_declined_without_number_prompt(tmp_path):
    async def scenario():
        app = RecorderApp(manifest=_manifest(), output_root=Path(tmp_path))
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            state = app.session.state
            state.effect_stack.append({
                "op": "remove_choice",
                "chooser": "A",
                "by_player": "A",
                "options": ["1,1"],
                "optional": True,
            })
            state.pending = {
                "mode": "choice",
                "chooser": "A",
                "optional": True,
                "options": ["1,1"],
            }
            app.refresh_game()
            await pilot.pause()
            app.query_one(CardShelf)
            decline = next(
                widget for widget in app.query(ActionCard)
                if getattr(widget.entry.payload, "choice", None) == "__skip__"
            )
            await pilot.click(f"#{decline.id}")
            await pilot.pause()
            assert app.session.state.pending is None
            assert app.session.decision_count == 1

    asyncio.run(scenario())


def test_tui_runs_bot_first_without_blocking_input_loop(tmp_path):
    manifest = generate_manifest(
        cohort_id="bot-first",
        human_decks=("ramp",),
        opponent_decks=("egg_control",),
        opponent_kinds=("random",),
        repetitions=1,
        seats=("B",),
        base_seed=_human_first_seed(),
        schedule_seed=0,
        map_id="map_b",
        config=Config().sweep(actions_per_turn=2, draw_action_count=1),
    )

    async def scenario():
        app = RecorderApp(manifest=manifest, output_root=Path(tmp_path))
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(20):
                await pilot.pause()
                if app.session.human_turn:
                    break
            assert app.session.human_turn
            assert app.session.decision_count >= 2
            assert not app.bot_busy
            board = app.query_one(BoardWidget).board_render
            own_hq = board.hitboxes[("hq", "B")]
            enemy_hq = board.hitboxes[("hq", "A")]
            assert own_hq.x < enemy_hq.x and own_hq.y > enemy_hq.y

    asyncio.run(scenario())


def test_hovering_crossroad_shows_complete_stack_tooltip(tmp_path):
    async def scenario():
        app = RecorderApp(manifest=_manifest(), output_root=Path(tmp_path))
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            board = app.query_one(BoardWidget)
            app.session.state.board["1,1"] = [
                UnitInstance("elephant", "A", 900),
                UnitInstance("fig_tree", "B", 901),
            ]
            app.refresh_game()
            hitbox = board.board_render.hitboxes[("cr", "1,1")]
            await pilot.hover("#board", offset=(hitbox.x + 1, hitbox.y + 1))
            await pilot.pause()
            tooltip = str(board.tooltip)
            assert "bottom → top" in tooltip
            assert "A  Elephant" in tooltip
            assert "B  Fig Tree" in tooltip
            assert tooltip.index("Elephant") < tooltip.index("Fig Tree")

    asyncio.run(scenario())


def test_recorder_cli_defaults_to_shipped_config():
    assert build_parser().parse_args([]).config == "none"

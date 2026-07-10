from __future__ import annotations

import asyncio
from collections import Counter
from pathlib import Path

from rich.text import Text
from textual.widgets import Static

from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine.actions import DrawAction
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import Result, UnitInstance, new_game
from animal_kingdom.recording.cohort import generate_manifest
from animal_kingdom.tui.app import (
    ActionCard,
    BoardWidget,
    CardShelf,
    DeckTracker,
    HelpScreen,
    RecentActionIcon,
    RecentLog,
    RecorderApp,
    build_parser,
)


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
            assert own_hq.y > enemy_hq.y
            assert abs((own_hq.x + own_hq.width // 2) - (enemy_hq.x + enemy_hq.width // 2)) <= 1
            hand_cards = [
                widget for widget in app.query(ActionCard)
                if isinstance(widget.entry.payload, tuple)
            ]
            assert hand_cards
            shelf = app.query_one(CardShelf)
            assert not shelf.has_class("fits")
            assert all(widget.entry.effect and widget.entry.stats.startswith("STR ") for widget in hand_cards)
            draw = next(
                widget for widget in app.query(ActionCard)
                if isinstance(widget.entry.payload, DrawAction)
            )
            assert "D DRAW" in str(draw.content)
            assert "Draw 1 card" in str(draw.content)
            prompt = str(app.query_one("#notice", Static).content)
            assert "Choose a card from your hand or draw" in prompt
            assert "STR" in app.export_screenshot()

            await pilot.press("1")
            await pilot.pause()
            assert app.selected_card is not None
            selected = next(widget for widget in app.query(ActionCard) if widget.entry.selected)
            assert "▶ " in str(selected.content)
            assert "Choose a highlighted location" in str(
                app.query_one("#notice", Static).content
            )
            await pilot.press("escape")
            await pilot.pause()
            assert app.selected_card is None
            assert "Choose a card from your hand or draw" in str(
                app.query_one("#notice", Static).content
            )
            disabled = next(
                widget for widget in app.query(ActionCard)
                if not widget.entry.enabled
            )
            assert "× " in str(disabled.content)
            shortcut = disabled.entry.label.split(maxsplit=1)[0]
            await pilot.press(shortcut)
            await pilot.pause()
            assert app.selected_card is None

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
            selected_name = app.session.state.cards[app.selected_card].name
            prompt = str(app.query_one("#notice", Static).content)
            assert selected_name in prompt
            assert "Choose a highlighted location" in prompt
            inspector = Text.from_markup(
                str(app.query_one("#side", Static).content)
            ).plain
            assert "SELECTED CARD" in inspector
            assert selected_name in inspector
            assert "LOCATION" in inspector
            assert "LEGAL TARGET" in inspector

            target = next(iter(app.target_map))
            hitbox = app.query_one(BoardWidget).board_render.hitboxes[target]
            before = app.session.decision_count
            await pilot.click(
                "#board",
                offset=(
                    hitbox.x + hitbox.width // 2,
                    hitbox.y + hitbox.height // 2,
                ),
            )
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
            assert not app.query_one("#own-deck", DeckTracker).display
            assert not app.query_one("#opponent-deck", DeckTracker).display
            hitboxes = board.board_render.hitboxes.values()
            left = min(hitbox.x for hitbox in hitboxes)
            right = max(hitbox.x + hitbox.width for hitbox in hitboxes)
            top = min(hitbox.y for hitbox in hitboxes)
            bottom = max(hitbox.y + hitbox.height for hitbox in hitboxes)
            assert left > 0 and top >= 0
            assert abs(left - (board.size.width - right)) <= 1
            assert abs(top - (board.size.height - bottom)) <= 1

            status = str(app.query_one("#status", Static).content)
            assert "Your turn" in status
            assert "Turn 1" in status
            opponent = str(app.query_one("#opponent", Static).content)
            assert "OPPONENT" not in opponent
            assert "Seat B" not in opponent
            assert "Food 0" in opponent
            notice = str(app.query_one("#notice", Static).content)
            assert "YOUR HAND" not in notice
            assert "Seat A" not in notice
            assert "Food 0" in notice
            assert "Actions 2" in notice
            footer = str(app.query_one("#footer", Static).content)
            assert "q" in footer and "Quit" in footer
            assert "?" in footer and "Help" in footer
            assert "Previous target" not in footer
            shelf = app.query_one(CardShelf)
            assert shelf.has_class("fits")
            cards = list(app.query(ActionCard))
            left = cards[0].region.x - shelf.region.x
            right = shelf.region.right - cards[-1].region.right
            assert left > 0 and abs(left - right) <= 1
            assert str(app.query_one("#side", Static).content) == ""

            app.bot_busy = True
            app.refresh_game()
            assert "Opponent is thinking" in str(
                app.query_one("#notice", Static).content
            )

    asyncio.run(scenario())


def test_recent_log_uses_hoverable_icons_beside_board(tmp_path):
    async def scenario():
        app = RecorderApp(manifest=_manifest(), output_root=Path(tmp_path))
        async with app.run_test(size=(180, 40)) as pilot:
            await pilot.pause()
            assert app.session is not None
            entries = [
                "A: drew cards",
                "B: played Eagle on 3,3",
                "A: chose 2,2",
            ]
            app.session.recent[:] = entries
            app.refresh_game()
            await pilot.pause()

            board = app.query_one(BoardWidget)
            recent = app.query_one(RecentLog)
            opponent = app.query_one("#opponent-deck", DeckTracker)
            assert board.region.right == recent.region.x
            assert recent.region.right == opponent.region.x

            icons = list(app.query(RecentActionIcon))
            assert len(icons) == 3
            assert [str(icon.tooltip) for icon in icons] == list(reversed(entries))
            icon_text = [
                Text.from_markup(str(icon.content)).plain
                for icon in icons
            ]
            assert icon_text == ["A◇", "B◆", "A↓"]
            assert all(
                str(icon.tooltip) not in text
                for icon, text in zip(icons, icon_text)
            )

            await pilot.hover(f"#{icons[0].id}")
            await pilot.pause()
            assert str(icons[0].tooltip) == "A: chose 2,2"
            assert str(app.query_one("#side", Static).content) == ""

    asyncio.run(scenario())


def test_food_progress_bars_show_current_and_target(tmp_path):
    async def scenario():
        app = RecorderApp(manifest=_manifest(), output_root=Path(tmp_path))
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert app.session is not None
            app.session.state.food["A"] = 50
            app.session.state.food["B"] = 20
            app.refresh_game()

            player = Text.from_markup(
                str(app.query_one("#notice", Static).content)
            ).plain
            opponent = Text.from_markup(
                str(app.query_one("#opponent", Static).content)
            ).plain
            assert "Food 50/100 ▕█████░░░░░▏" in player
            assert "Food 20/100 ▕██░░░░░░░░▏" in opponent

            app.session.state.food["A"] = 120
            app.refresh_game()
            player = Text.from_markup(
                str(app.query_one("#notice", Static).content)
            ).plain
            assert "Food 120/100 ▕██████████▏" in player

    asyncio.run(scenario())


def test_deck_trackers_are_responsive_and_ignore_opponent_hidden_zones(tmp_path):
    async def scenario():
        app = RecorderApp(manifest=_manifest(), output_root=Path(tmp_path))
        async with app.run_test(size=(180, 40)) as pilot:
            await pilot.pause()
            assert app.session is not None
            state = app.session.state
            own = app.query_one("#own-deck", DeckTracker)
            opponent = app.query_one("#opponent-deck", DeckTracker)
            side = app.query_one("#side", Static)

            assert own.display and opponent.display and side.display
            assert own.region.width == side.region.width
            assert own.remaining_counts == Counter(state.decks["A"])
            assert sum(own.remaining_counts.values()) == len(state.decks["A"])
            assert sum(opponent.remaining_counts.values()) == len(
                state.starting_decks["B"]
            )
            assert "YOUR DECK" in str(own.content)
            assert "OPPONENT UNSEEN" in str(opponent.content)

            opponent_before = str(opponent.content)
            hand_card = state.hands["B"][0].card_id
            deck_index = next(
                index
                for index, card_id in enumerate(state.decks["B"])
                if card_id != hand_card
            )
            state.hands["B"][0].card_id, state.decks["B"][deck_index] = (
                state.decks["B"][deck_index],
                hand_card,
            )
            app.refresh_game()
            assert str(opponent.content) == opponent_before

            revealed_card = state.starting_decks["B"][0]
            state.board["1,1"] = [UnitInstance(revealed_card, "B", 900)]
            app.refresh_game()
            expected_left = Counter(state.starting_decks["B"])[revealed_card] - 1
            assert opponent.remaining_counts[revealed_card] == expected_left
            opponent_markup = str(opponent.content)
            assert f"(x{expected_left})" in opponent_markup
            assert "−" not in opponent_markup
            if expected_left == 0:
                assert "[dim](x0)" in opponent_markup
            assert "[bold yellow]" in opponent_markup
            assert "[bold blue]" in opponent_markup

            own_legendary = next(
                card_id
                for card_id in state.starting_decks["A"]
                if state.cards[card_id].rarity == "legendary"
            )
            state.decks["A"] = [
                card_id for card_id in state.decks["A"]
                if card_id != own_legendary
            ]
            app.refresh_game()
            assert (
                f"[dim](x0) {state.cards[own_legendary].name}[/dim]"
                in str(own.content)
            )

            await pilot.resize_terminal(150, 40)
            await pilot.pause()
            assert own.display and opponent.display
            assert not side.display

            await pilot.resize_terminal(120, 40)
            await pilot.pause()
            assert not own.display and not opponent.display
            assert side.display

            await pilot.resize_terminal(100, 40)
            await pilot.pause()
            assert not own.display and not opponent.display and not side.display

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
            prompt = str(app.query_one("#notice", Static).content)
            assert "Resolve effect" in prompt
            assert "highlighted location or an option below" in prompt
            decline = next(
                widget for widget in app.query(ActionCard)
                if getattr(widget.entry.payload, "choice", None) == "__skip__"
            )
            await pilot.click(f"#{decline.id}")
            await pilot.pause()
            assert app.session.state.pending is None
            assert app.session.decision_count == 1

    asyncio.run(scenario())


def test_completed_game_shows_clickable_recording_path(tmp_path, monkeypatch):
    async def scenario():
        app = RecorderApp(manifest=_manifest(), output_root=Path(tmp_path))
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert app.session is not None
            path = app.session.path.resolve()
            monkeypatch.setattr(
                type(app.session),
                "result",
                property(lambda _session: Result("A", "food")),
            )
            app.refresh_game()
            await pilot.pause()

            notice = app.query_one("#notice", Static)
            prompt = str(notice.content)
            inspector = str(app.query_one("#side", Static).content)
            assert "[@click=app.open_recording underline]Open JSONL log (O)[/]" in prompt
            assert inspector == ""

            opened: list[str] = []
            monkeypatch.setattr(
                app,
                "open_url",
                lambda url, **_kwargs: opened.append(url),
            )
            link_x = notice.content_region.x - notice.region.x
            for segment in notice.render_line(0):
                if segment.style and segment.style.meta.get("@click") == "app.open_recording":
                    break
                link_x += segment.cell_length
            else:
                raise AssertionError("completion prompt has no clickable log segment")
            await pilot.click("#notice", offset=(link_x, 0))
            await pilot.pause()
            assert opened == [path.as_uri()]

            await pilot.press("o")
            await pilot.pause()
            assert opened == [path.as_uri(), path.as_uri()]

    asyncio.run(scenario())


def test_help_overlay_keeps_recorder_controls_out_of_footer(tmp_path):
    async def scenario():
        app = RecorderApp(manifest=_manifest(), output_root=Path(tmp_path))
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert not app.active_bindings["m"].binding.show
            assert not app.active_bindings["g"].binding.show
            assert app.active_bindings["question_mark"].binding.show

            await pilot.press("question_mark")
            await pilot.pause()
            assert isinstance(app.screen, HelpScreen)
            help_text = str(app.screen.query_one("#help", Static).content)
            assert "HOW TO PLAY" in help_text
            assert "Exclude / restore the latest human decision" in help_text
            assert "Every action is saved to JSONL" in help_text

            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, HelpScreen)

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
            assert own_hq.y > enemy_hq.y
            assert abs((own_hq.x + own_hq.width // 2) - (enemy_hq.x + enemy_hq.width // 2)) <= 1

    asyncio.run(scenario())


def test_hovering_crossroad_shows_complete_stack_details(tmp_path):
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
            await pilot.hover(
                "#board",
                offset=(
                    hitbox.x + hitbox.width // 2,
                    hitbox.y + hitbox.height // 2,
                ),
            )
            await pilot.pause()
            tooltip = str(board.tooltip)
            assert "bottom → top" in tooltip
            assert "A  Elephant" in tooltip
            assert "B  Fig Tree" in tooltip
            assert tooltip.index("Elephant") < tooltip.index("Fig Tree")

            inspector = Text.from_markup(
                str(app.query_one("#side", Static).content)
            ).plain
            assert "Crossroad 1,1" in inspector
            assert "STACK · 2 cards · top first" in inspector
            assert "A Elephant · STR" in inspector
            assert "B Fig Tree · STR" in inspector
            assert inspector.index("Fig Tree") < inspector.index("Elephant")

            await pilot.hover("#actions")
            await pilot.pause()
            assert str(app.query_one("#side", Static).content) == ""

    asyncio.run(scenario())


def test_recorder_cli_defaults_to_shipped_config():
    assert build_parser().parse_args([]).config == "none"

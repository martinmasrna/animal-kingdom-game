# Audit: facts inferred instead of stated (Sol, 2026-10-01)

Asked for every place one side of the game guesses, diffs or times what the other side should state, after two such bugs (a hatching egg's choice named the opponent's card; 'Your turn' before a Polar Bear's card showed). The fixes are tracked against this list.

Ranked by likelihood and severity of a player-visible failure:

1. [web/static/app.js:763](animal_kingdom/web/static/app.js:763), [app.js:870](animal_kingdom/web/static/app.js:870) — Infers the opponent’s animated action from the last history entry plus a view diff. If one pushed view contains multiple resolved actions, only the last card is revealed while all changes animate together. Send an ordered event/resolution batch with card, target, effects, and completion boundaries.

2. [web/static/app.js:715](animal_kingdom/web/static/app.js:715) — `1900 ms`, plus `700 ms` if any removal/bounce, stands for “opponent’s move finished.” Multi-removal, food, draw, strength, or chained effects take different times; “Your turn” can appear mid-animation. Animation playback should emit/await a completion event for the server-provided sequence.

3. [web/static/app.js:723](animal_kingdom/web/static/app.js:723) — “Your turn” timing is inferred from `ui.revealEnd`; moves without a recognized reveal, or with longer secondary effects, cue immediately/early. Use an explicit client playback-complete boundary, not a timestamp.

4. [web/static/app.js:507](animal_kingdom/web/static/app.js:507) — Start-of-turn staging is guessed from current-player changes, history growth, and `yoursChanged`. An opponent’s Polar Bear/removal delivered with the turn transition can be mistaken for—or suppress—the new player’s start effects. Send distinct `turn_ended`, `start_turn_effects`, `decision_ready` phases.

5. [web/static/app.js:738](animal_kingdom/web/static/app.js:738) — `yoursChanged` only compares owned unit IDs or presence of a pending choice. Start-of-turn food, strength, timer, enemy removal, or a changed choice can be missed. Send explicit start-of-turn events and their affected objects.

6. [web/match.py:589](animal_kingdom/web/match.py:589) — Prompt source is guessed from `by_card`, then operation-name prefix, then the chooser’s last placement. A delayed/triggered choice can name an unrelated recent card or just “Choose.” Every choice request should carry an authoritative `source_card`/`source_iid` when created.

7. [engine/effects.py:89](animal_kingdom/engine/effects.py:89) — Missing prompt provenance is only asserted when tests toggle `REQUIRE_SOURCE`; production silently accepts it. A newly added choice op can regress exactly like Bird Egg. Make source mandatory in the `PendingRequest`/step schema, except mulligan.

8. [web/match.py:117](animal_kingdom/web/match.py:117) — The server reconstructs the move’s effects by diffing final state, losing order and causality. A placement that triggers several draws, removals, bounces, and food gains is reported as an unordered aggregate. The engine should emit ordered typed events while resolving.

9. [web/static/turn.js:35](animal_kingdom/web/static/turn.js:35) — Any new top IID is classified as “landed”; removing a top unit exposes an old buried unit and makes it animate as newly arriving. Supply explicit `land`, `uncover`, and `remove` events.

10. [web/static/turn.js:37](animal_kingdom/web/static/turn.js:37) — Any top replacement over a previously occupied crossroad is classified as “covered.” Removing/bouncing the top and revealing the unit below therefore looks like a cover. Use the explicit board event type.

11. [web/static/turn.js:40](animal_kingdom/web/static/turn.js:40) — Bounce identity is reconstructed as `card + owner`, not IID. With two identical owned copies, removal of one and bounce of the other can assign the bounce animation to the wrong piece. Emit the affected IID and destination.

12. [web/static/turn.js:41](animal_kingdom/web/static/turn.js:41) — Only units that were top in the previous view get leaving animations. Pestis removing an entire stack silently drops buried units. Emit every removed IID, its crossroad, and order.

13. [web/static/turn.js:45](animal_kingdom/web/static/turn.js:45) — Strength animation is inferred from net before/after strength. A unit buffed then debuffed to its original value shows nothing; several changes collapse into one direction. Emit ordered strength deltas.

14. [web/static/turn.js:50](animal_kingdom/web/static/turn.js:50) — Food origin is guessed from currently held region stones. Direct card food gained while regions are held appears to fly from those stones; income from a region lost later can fly from the wrong set. Emit each food gain’s source and amount.

15. [web/match.py:124](animal_kingdom/web/match.py:124) — Vanished board units are matched to Remove Pile entries by card ID and first matching owner. Duplicate cards owned by both players can attribute removal to the wrong owner. Record IID, owner, source, and destination at disposal time.

16. [web/match.py:127](animal_kingdom/web/match.py:127) — A fresh hand IID is guessed to be a bounce when a vanished same-card board unit exists. If the same move bounces one copy and draws another, the draw/bounce counts can be swapped. Emit explicit transfer events with old/new IID linkage.

17. [web/match.py:130](animal_kingdom/web/match.py:130) — New removals are inferred from a Remove Pile suffix. If the effect also removes something from that pile—Shuck or Ember-style movement—the suffix no longer represents what was removed during the move. Emit removal events when they occur.

18. [web/match.py:143](animal_kingdom/web/match.py:143) — End-turn income is inferred by subtracting `region_income` computed from the final post-start-of-next-turn board. If start-of-turn effects alter control, the subtraction is wrong and card food is misreported. Record the actual income payment event separately.

19. [web/static/app.js:1078](animal_kingdom/web/static/app.js:1078) — HQ capture display is reconstructed from result reason plus the last move, using printed card strength. Buffed/dynamic capturers can display the wrong strength, and a nonstandard capture chain could pick the wrong card. Include the capturing unit snapshot in the result event.

20. [web/static/app.js:1230](animal_kingdom/web/static/app.js:1230) — Replay visibility is decided by JSON-diffing a hand-picked subset of the view. Timer, strength metadata, prompt source, legal changes, or other omitted fields can make a meaningful step disappear. Persist explicit replay frames/events and a `visible`/`playback` boundary.

21. [web/static/app.js:1246](animal_kingdom/web/static/app.js:1246) — Replay move completion is inferred as “last view before history length grows.” Choices and effects belonging to a move can be separated incorrectly when extra placements create history entries or a move changes no history. Give every action/effect a stable `move_id` and explicit end marker.

22. [web/static/app.js:1252](animal_kingdom/web/static/app.js:1252) — Replay uses fixed `1400/2200/1100 ms` delays for opening/reveal/other steps. Complex effects are cut off; simple ones stall. Advance on animation-sequence completion, with speed scaling applied to declared durations.

23. [web/static/app.js:515](animal_kingdom/web/static/app.js:515) — `1500/1520 ms` means “turn plate finished,” then `1100 ms` means “start effect finished enough to show its choice.” Long food/removal chains reveal choices too early; short changes wait unnecessarily. Chain actual animation completion promises.

24. [web/static/app.js:1151](animal_kingdom/web/static/app.js:1151) — Game-over waits `2200 ms` or `revealEnd + 1200 ms`, guessing when the final action has finished. Large food payouts or multi-removals can be hidden by the result overlay. Show results after the final playback sequence reports completion.

25. [web/server.py:46](animal_kingdom/web/server.py:46), [server.py:148](animal_kingdom/web/server.py:148) — Bot pacing uses `1.6/1.1/0.6 s` as proxies for the client finishing open/move/choice playback. A bot can submit the next action while the previous one is still animating. Client acknowledgements or server event sequence IDs should gate bot continuation.

26. [web/server.py:155](animal_kingdom/web/server.py:155) — After tutorial hold release, `open + 0.4 s` guesses when the “Next” animation ends. Fruit volume or reduced-motion settings change the real duration. Have the tutorial client acknowledge playback completion.

27. [web/static/board.js:45](animal_kingdom/web/static/board.js:45), [board.js:140](animal_kingdom/web/static/board.js:140) — `0.7 s` flight and `0.035 s` gaps are separately encoded timing facts used to approximate food completion. CSS changes can desynchronize counters, pits, and overlays. Use one animation timeline or completion events derived from the rendered animations.

28. [web/static/board.js:150](animal_kingdom/web/static/board.js:150), [board.js:155](animal_kingdom/web/static/board.js:155) — `0.12/0.15/0.11 s` and `150/300 ms` synthesize “pit ripened/count finished.” Non-region food and large gains can make gem and pit timing disagree. Drive both from explicit food-gain animation items.

29. [web/static/app.js:965](animal_kingdom/web/static/app.js:965) — Tutorial-held food sets `animUntil = 1800 ms`, assuming every payout finishes then. Large payouts exceed it and a subsequent view can cut them off. Await the fruit timeline’s completion.

30. [engine/effects.py:67](animal_kingdom/engine/effects.py:67), [web/match.py:580](animal_kingdom/web/match.py:580) — Missing `optional` silently becomes mandatory in both engine legality and client view. A producer forgetting the field removes Skip without any schema failure. Require `optional` explicitly on every pending request.

31. [engine/effects.py:580](animal_kingdom/engine/effects.py:580), [effects.py:601](animal_kingdom/engine/effects.py:601) — Missing `while_buried` silently means a timer pauses while buried. Taipan explicitly opts out; any future delayed effect that forgets the field changes rules invisibly. Require a declared timer policy such as `pause_when_buried`/`continue_when_buried`.

32. [engine/effects.py:743](animal_kingdom/engine/effects.py:743) — Missing `source_iid` changes a queued reaction from “fizzle if its source left” to unconditional. A new reactive removal that omits it can fire from a dead unit. Model reaction source as required data, distinct from display `by_card`.

33. [engine/effects.py:748](animal_kingdom/engine/effects.py:748) — Missing `by_player` defaults to the target’s owner and missing `by_effect` defaults to `true`. An incompletely constructed removal can credit the victim, trigger the wrong “friendly/enemy removal” reactions, or bypass intended semantics. Make remover and removal cause mandatory.

34. [engine/effects.py:692](animal_kingdom/engine/effects.py:692) — Missing Scout `spec` means “top cards,” while present `spec` means random matching cards. Forgetting the field changes both card pool and randomness without failure. Use separate explicit operations or require a declared selection mode.

35. [engine/effects.py:759](animal_kingdom/engine/effects.py:759) — Missing/empty extra-play `filter` means every hand card is allowed. A card intended to grant a typed extra play becomes unrestricted if its filter is omitted. Require an explicit filter, including an explicit `any` variant.

36. [web/match.py:528](animal_kingdom/web/match.py:528), [web/static/app.js:575](animal_kingdom/web/static/app.js:575) — Absent clock or absent `on` silently means no displayed countdown. After loading an older/incomplete match, a live server timeout can occur with no visible clock. Send an explicit clock state enum and deadline.

37. [web/match.py:558](animal_kingdom/web/match.py:558), [web/static/app.js:861](animal_kingdom/web/static/app.js:861) — The client only knows the opponent is choosing through optional `opponentChoosing`; absence means ordinary thinking. A view/schema omission hides an active opponent prompt and may show misleading turn UI. Always send a decision phase and actor, even when no local legal actions are exposed.

## Status (2026-10-01, end of day)

Fixed by the event log (engine `state.events`, sent in every view; the server's position diff is gone): 8, 15, 16, 17, 18, and the board side of 9–12 and 14. Fixed by the animation timeline (`static/timeline.js`, one step per event, each for its declared length; `PB` in app.js plays them): 1–5, 23, 24, 27–29 in what they guarded (the guess timers are deleted), 9 (an uncovered unit no longer looks landed), 14 (only region income flies from the stones), 22 (replays move on when a step ends). Fixed by source cards by construction (effects.resolve, `REQUIRE_SOURCE` in tests): 6, 7. Fixed by required fields (constructors `remove_iid_step`, `remove_choice_step`; `schedule(..., while_buried=)`; scouts' `spec`; `PendingRequest.optional`; saved games upgraded in `state._upgrade_step`): 30–35.

Fixed since: 13 (stored strength changes are events, the moment Fox and Bush Dog react; the board flashes only those; auras show in the number without a flash). Fixed since: 19 (the capture event carries the taker's strength as played; the screen draws the den's animal from it). Fixed since: 20 (a replay step is a view that brought new events, a changed choice put to you, or a new phase; matches from before events keep the old comparison). Left as is: 21 (a move's end is read from the server's move list, a stated fact). Fixed since: 25–26 (a bot waits for each watching player's 'played' report, at most 6 s, then a short thinking beat; the tutorial lets its hold go only once what Next set off has played). Open: 36 (clock: no explicit state enum), 37 (`opponentChoosing` optional).

---
name: bot-change
description: Measure one change to how a bot plays (an evaluation term, a search knob, a new dial, a mulligan policy) with the paired benchmark on a frozen checkout, read the result, and ship it into the level's spec or drop it. Use when bot code changed and the question is whether the bot got better, when Martin asks "is the bot better", "does this help", "benchmark it", or "/bot-change". Do NOT use for card balance (cards are measured by Martin's games, never changed for a bot), for the ladder re-seed, or for a deploy that carries no bot change.
---

# Bot change

Purpose: a bot change ships on evidence that survives the next session, not on a run whose conditions nobody can restate. A benchmark is a claim about one pilot against another on one card pool; when the pool or the code moves under the run, or the code that ran was never committed, the number means nothing and nobody notices. Every run here is reproducible from its folder.

Bot work is judged by rating against people (goal: the best pairing at about 2100). Bot-against-bot numbers only rank candidates; they never say a bot is good. Never nerf a card to fix a bot. Difficulty comes from real strength only.

## 1. Commit the candidate before measuring it

The benchmark plays what is in a checkout, so the candidate's code must be a commit: push it, or commit it on a local branch and freeze that. A dial that is off by default ships with no change to play and needs no benchmark to go in; the benchmark decides whether a level's spec turns it on.

## 2. Run

`tools/bot_bench/bench.sh run <name> "+dial=value"` freezes origin/main into `results/bot_quality/<name>/tree` (`AT=<commit>` for another), records the commit and the card pool in `run.json`, and launches the paired benchmark in the background: candidate and baseline are the shipped Expert without its time budget, with and without the change, both playing the shipped Expert as the opponent. Twenty games a deck over the bot pool takes about four hours on the Mac; `AFTER=<name>` queues a run behind another, since two runs at once halve each other. Leave a background waiter on the log and keep the conversation going.

The run plays on the Rust engine with its own copy of the built module (`run.json` says `"rust": "1"`; AK_PY_BOTS=1 for the Python bots, fifty times slower). The checkout is the run's. Never fetch into it, rebase it, edit it or move it while the run goes; the workers re-read the cards whenever a batch starts. A self-play round, an oracle run or any other long job gets its own `tools/bot_bench/bench.sh freeze <name>` tree, never a benchmark's. Deploys and commits happen from another tree.

A change to the time budget, or anything whose effect is speed, is measured on moves per second, not here: the benchmark runs untimed so the machine's load cannot change a move.

## 3. Read

`tools/bot_bench/bench.sh report <name>` gives the per-deck deltas with their intervals and the pooled mean. `tools/ladder/ladder.py` then places the candidate on the one rating ladder with every bot and person who has played (docs/bots.md, the rating ladder); the result reaches Martin as the candidate's rating next to the live Expert's and his own, and as win rates, never as points a deck. Twenty games a deck is about plus or minus ten points per deck, so a single deck's sign is noise unless its interval clears zero.

Ship when all three hold: the pooled mean is up; no deck is down beyond its own interval; the gain sits where the change's mechanism predicts it (a change to how placements with sub-choices are ranked gains most on the decks whose placements carry sub-choices; the same mean landing on unrelated decks is a lucky run and wants more games). A change that gains where it should and loses clearly somewhere else has a side effect to find in that deck's logs under `<name>/logs/` before any shipping.

The benchmark is a guard against regressions, not proof the bot plays well (Martin, 2026-10-28): candidate and opponent share one evaluation, so its blind spots cancel out, and a stale network (trained before a large card change) is a fair referee between two bots and a poor one of play. A new network is judged first on Martin's own recent games on current cards (log-loss and sign against the live one), and every candidate also runs the misplay positions from his games (a play beyond argument never made, over many seeds) before it ships.

Stop a run early when half the decks are in and every delta sits inside noise around zero: the second half will not rescue it, and the machine has other runs waiting. Report the stop as a stop, never as a result.

Report the table to Martin as decks and points, with the mechanism read in one sentence. A change that passes the ship rule ships without waiting for him (Martin, 2026-10-23); his games against the bot afterwards are the yardstick, read from the logs and the ladder, never a session he is asked to play.

## 4. Ship

Shipping is the spec, not the code: add the dial to the level's string in `animal_kingdom/web/match.py` (the Expert, and Normal only when its own run says so), update the test that pins that spec, and add the result to the bot's entry in `docs/bots.md` as the current state, with the numbers and the date. Commit by path. Deploy from a tree whose HEAD contains origin/main (never the shared tree when it is behind), with `NEWS_OK=1` while the collection is unplayed, and check the live server plays the new spec, not only that it answers.

A bot change never triggers a full ladder re-seed; the ladder's Expert ratings lag the spec until a seed is due for its own reasons.

When the run is done and read, `tools/bot_bench/bench.sh clean <name>` removes the checkout; the logs and the run record stay, and are what a later question about the run is answered from.

## Self-improvement

At the start of every run, read `LEARNINGS.md` in this folder and apply it. After the change ships or drops, run the retrospective; the mechanism and guardrails live in `~/.claude/skills/_shared/self-improvement.md`, read it before writing to either file. A good staged learning here: a reading rule that turned out wrong on a later run, a deck that keeps flagging as a side effect for a reason the skill should name, or a step of the shipping path that a session missed.

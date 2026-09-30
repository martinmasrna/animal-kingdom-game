# Pre-launch

Decisions and work that must be settled before the game goes public, and not before. Each item says what is open and where it came from.

- **Who starts games 2 and 3 of a best-of-3.** The rules only say a coin flip picks the first player ([`rules/overview.md`](rules/overview.md) §4.2). Options: the loser of the previous game chooses, alternate, or flip each game.
- **Maps for the best-of-3.** Only Savanna Expanse exists, so all three games use it for now. More maps would make the three-map reveal (§14) mean something.
- **Turn clock values.** Poker-style: a free window per turn (unused time is lost) plus a bank for the whole game. Built with the starting guess, 30 s per decision and a 3-minute bank (`CLOCK_FREE`, `CLOCK_BANK` in `web/match.py`); set the real numbers from games between people.
- **Rating and ranked queue.** The home screen has a Leaderboard, which needs a rating system (Elo or similar) and a ranked option next to Friend and Bot.
- **Keyword explanations.** Right-clicking a card in the collection shows a one-line explanation per keyword (`KEYWORDS` in `web/static/collection.js`): a first draft summarised from [`rules/keywords.md`](rules/keywords.md). Players learn the rules from these lines, so Martin redlines them.
- **A painted cursor.** The game uses the system cursors. A custom one (as Hearthstone's gauntlet) only works as real painted art in the cards' hand; a code-drawn arrow was tried in the collection and removed.
- **Art consistency pass.** The card paintings are placeholders in two finishes: most commons and rares in a painterly gouache hand, most legendaries (and a few commons such as Viper and Python) in a dramatic rendered finish. The rendered finish carries much of the legendary look, and a painterly repaint of five cards (Lobo, Raksha, Python, Eon, Queen Marabunta, 2026-09-30) stripped it: every one read as a common. The pass must decide one coherent hand per rarity without losing what makes each card work (its hook, contrast and, for legendaries, the lift), and never repaint a working card for consistency alone. Audit page: `cards/style-audit.html` in the design sandbox.

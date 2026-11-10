# Ranked leagues

Martin, 2026-11-04: instead of ranked being a rating from the start, do what Hearthstone, Gwent, MTG Arena and League do: about ten leagues, each with a few stars; a win gains a star, a loss loses one; a bonus for win streaks; a few stars to move up; checkpoints below which you can't fall; the uncapped rating only in the highest league. Nothing elaborate. The point is progression instead of a flat number.

Settled (Martin, 2026-11-05): three rules, all on the screen. A win gains a star, two from your third win in a row. A loss loses a star, and at 0 stars drops you a league, never out of league 1. You play opponents from your own league; in the top league, from your rating, and the rating shows. In his words on what the top league means: the climb stops where your skill is, "yes, this is how it should be".

This page: what four other games do and what each mechanic is for, why this game's leagues work as they do, the rules, the simulation, what a player sees, the calls still open, the names, the migration, and a draft News entry.

Status: live since 2026-11-06 (merged from `ranked/leagues`), the screens in text only. The rules live in one file, `animal_kingdom/web/tiers.py`, which the server and the simulator both use.

## A word clash to know about

"The league" already means the bot population in this repo (`docs/league.md`, `web/league.py`, the runner). Players never see that word, so the screens can say "league" for the climb. The code says `tier` (`web/tiers.py`, the `tiers` table) so the two never mix.

## What the four games do

Sources were read through web search summaries; direct page fetches were blocked in this session (the network policy refused hearthstone.wiki.gg and blizzard.com), so treat exact numbers as "the cited page says about this". Where sources disagreed, it says so.

**Hearthstone** (the April 2020 system, unchanged since as far as the 2025 to 2026 patch notes show). Five leagues, Bronze to Diamond, each with ranks 10 to 1; 3 stars a rank, so about 150 stars from the bottom to Legend. A win gains a star, a loss loses one. From the third win in a row a win pays double, until Diamond 5. A floor every 5 ranks: once reached, you don't fall below it that month. Every month everyone restarts at Bronze 10 with a Star Bonus (a multiplier on stars per win, up to about 10x for a Legend finish) that shrinks as you climb past floors; while the bonus lasts, matchmaking uses the hidden rating (MMR). Inside Legend there are no stars: a number, moved by MMR. Blizzard's stated reasons: fair matches and a quick return to your level after the reset, a bonus for those who play little, floors so you can stop losing stars. Criticism: match quality "collapses" at Diamond 5 when the bonus runs out; the grind moved into Legend where progress is invisible. (pcgamer.com/new-hearthstone-ranking-system; playhearthstone.com/en-us/blog/23319441; blizzardwatch.com/2020/04/02/new-ranked-ladder-arrived-hearthstone-featuring-lots-stars; hearthstone.wiki.gg/wiki/Ranked; hearthstonetopdecks.com/hearthstones-ranked-mode-overhaul-two-months-in-how-good-is-it; hearthpwn.com/news/1814-ben-brode-unhappy-with-ranked-ladder-system)

**Gwent.** Ranks 30 to 0, each a mosaic of 5 pieces, a win fills one. Losses: ranks 30 to 26 never lose a piece, 25 to 15 lose one only after two losses in a row, 14 and up lose one a loss. Every rank is a floor: you can never drop a rank inside a season. Three wins in a row give a bonus piece from rank 30 to rank 8. Rank 0 is Pro Rank: no mosaic, a rating per faction, placed by the season's peak, so playing on never costs you. Monthly reset: 1 to 3 ranks down. CD Projekt ended development in 2024; seasons still run. (support.cdprojektred.com/en/gwent/pc/gwent-gameplay/issue/1105/ranked-mode-progression; …/issue/1957/season-end-ranked-resets; masters.playgwent.com/en/news/7091/pro-rank-mmr; masters.playgwent.com/en/official-rules)

**MTG Arena** (Constructed). Bronze, Silver, Gold, Platinum, Diamond, each with tiers 4 to 1, 6 pips a tier, then Mythic. Best-of-one: Bronze +2 a win and no loss, Silver and Gold +2 and −1, Platinum and Diamond +1 and −1. No win streak bonus (sources conflict; most say none). Floor: you can't drop out of your current rank (Gold never back to Silver); Mythic is kept until the season ends. Mythic shows a percentile, then an exact place in the top 1,200, from a Glicko rating. Monthly reset by last season's finish (Mythic to about Platinum 4). Criticism: the grind, a long climb that "has very little to do with how good you are", mostly from the symmetric +1/−1 at Platinum and Diamond. (draftsim.com/mtg-arena-ranking-system; magic.wizards.com/en/news/mtg-arena/ranked-season; mtgazone.com/the-mtg-heros-guide-to-mythic; steamcommunity.com/app/2141910/discussions/0/4352247707588015141)

**League of Legends.** Ten tiers, Iron to Challenger; Iron to Diamond in four divisions of 100 LP each. Promotion series were cut in 2021 (between divisions) and in 2023 (all), Riot saying the stress of replaying promotions for ranks you had already earned outweighed their worth. A new tier comes with a short shield against dropping out of it; the division shield was removed in 2024. Master and up: no divisions, LP uncapped. The hidden MMR sets the LP per game: MMR above your rank, bigger gains and smaller losses, until the rank catches up. One reset a year since 2025, after three a year in 2024 drew "grind" complaints. (support.riotgames.com/en-us/league-of-legends/gameplay/mmr-rank-and-lp; leagueoflegends.com/en-us/news/game-updates/what-s-next-for-ranked; dexerto.com/league-of-legends/riot-remove-league-promo-series-major-season-11-ranked-shake-up-1421120; dexerto.com/league-of-legends/league-players-upset-with-new-grind-caused-by-season-14-ranked-splits-2726725)

## What each mechanic is for

- **Stars per league.** How many wins a step costs. Few stars at the bottom make the first steps come in the first session; more stars higher up make each step mean something. All four do this, by stars (HS), pieces (Gwent), pips (MTGA) or LP (LoL).
- **No losses at the bottom.** Onboarding: a newcomer can only go up, so the first hours never feel like failing (HS Bronze in its old form, MTGA Bronze, Gwent 30 to 26).
- **Floors (checkpoints).** Cap what one bad evening can cost, so people keep playing instead of protecting their rank, and keep the progress they earned. The cost: someone can sit above their real level, meeting opponents a little too strong for them. LoL went the other way in 2024 and lets the rank follow the rating.
- **Win streak bonus.** A catch-up: someone who wins three in a row is probably placed too low, so they move faster. Every game switches it off near the top, so the top measures a sustained win rate, not a hot run.
- **The hidden rating under the stars.** All four keep one. It picks opponents, and in HS (the Star Bonus) and LoL (LP by MMR) it also decides how fast the visible rank moves, so the rank converges on real strength. Where the two drift apart, the complaints start (HS's Diamond 5, LoL's "+15/−25").
- **Resets (seasons).** Recurring goals, monthly rewards, a reshuffled ladder. Costly for a small player base: everyone has to climb again, and LoL cut back from three a year to one after players called it a grind.
- **The uncapped top tier.** Where the milestones end and the rating itself is shown: HS Legend's number, Gwent's Pro Rank, MTGA Mythic, LoL Master and up. It is where the best players compete for a place, and where esports qualification reads.

## Why opponents come from your league

On this ladder the opponent is nearly always a bot, and a bot is always there. If the rating picks the opponent, every settled player wins about half their games whatever their strength, and stars can only measure games played: a plain win +1, loss −1 goes nowhere, and every rule that lets a 50% player climb (no losses at the bottom, checkpoints, streak bonuses, extra stars tied to a hidden rating) is a way to turn volume into progress. Tying stars to a hidden rating (Hearthstone's Star Bonus, League of Legends' LP by MMR) fixes the volume problem at the cost of a number the player can't see deciding what the number they can see does.

Picking the opponent by league removes the problem at its root. Each league is a band of bot ratings, so a league's opponents get stronger as you climb, and the climb stops where you win as often as you lose: the league says how good you are. A loss at 0 stars has to be able to drop you a league, or a lucky run would leave a weak player in a league that beats them four games in five, for good; with drops, a drop from bad luck puts you among easier opponents and you climb back.

## The design

| League | Stars to move up | Bots it plays (rating) |
|---|---|---|
| 1 | 3 | under 1100 |
| 2 | 3 | 1100 to 1200 |
| 3 | 3 | 1200 to 1300 |
| 4 | 5 | 1300 to 1400 |
| 5 | 5 | 1400 to 1500 |
| 6 | 5 | 1500 to 1600 |
| 7 | 5 | 1600 to 1700 |
| 8 | 5 | 1700 to 1800 |
| 9 | 5 | 1800 to 1900 |
| 10, the top | none: the rating shows | by your rating, as before leagues |

The top league starts at the bot band Legendary (1900), so the top league and the top bot band mean the same thing. The 129 bot pairings run from 941 to 2246, with at least five in every league's band.

The rules, each a test in `animal_kingdom/tests/test_tiers.py`:

1. **Start.** Everyone starts in league 1 with 0 stars.
2. **A win** gains a star; your third win in a row and every one after it gains two, in every league below the top.
3. **Moving up.** Reaching the league's star count moves you up, a spare star carried over. Reaching the top league ends stars.
4. **A loss** loses a star and ends your streak. At 0 stars it drops you a league, onto that league's stars minus one; in league 1 it costs nothing more.
5. **Opponents.** Below the top league, a person from your league if one is waiting, else a bot from your league's band (the strongest pilot there first, never the deck of your last four bot games). In the top league, a person or bot near your rating, as before leagues.
6. **The top league** is kept once reached and shows your rating, the ladder's own number.
7. **The rating** keeps running for everyone, bots included. Below the top league it decides nothing a player sees; it gives the number you start the top league with, and it places each bot in its league. Bots show no league.
8. **What you see**: the league's name, your stars as a count ("3 of 5 stars"), your win streak from two wins; in the top league, the rating. The end of a ranked match says what the game did in one line ("+2 stars (win streak): League 5, 1 of 5 stars", "-1 star: League 5, 0 of 5 stars", "Up to League 7, 0 stars", "Down to League 4, 4 stars").

## The simulation

`tools/ranked/simulate.py`: a player of fixed true strength meets what the server would pick (below the top a bot drawn from the league's band of the seeded bot ratings, in the top league one near the player's rating), the result drawn from the Glicko expectation. 300 runs of 400 games each:

| Strength | Reached the top | Median games to it | League after 400 games | Won of the last 100 |
|---|---|---|---|---|
| 1100 | 0% | | 2 | 45% |
| 1300 | 0% | | 4 | 46% |
| 1500 | 0% | | 6 | 46% |
| 1700 | 72% | 151 | 10 | 49% |
| 1900 | 100% | 35 | 10 | 50% |
| 2100 | 100% | 23 | 10 | 51% |

Every player settles in the league that matches their strength and wins a little under half there. Playing more doesn't push anyone past it; getting better does. The strong are at the top within a few sessions.

## What a player sees, screen by screen

Text only, as built on the branch; where a picture belongs is marked.

- **Home, the Ladder piece** (top-right corner): "Ladder", under it the league and place: "League 5 · 2 of 5 stars · #7"; in the top league "League 10 · 2011 · #2". *Picture: the league's badge beside the word.*
- **Home, the Ranked choice**: under "Ranked", the league: "League 5 · 2 of 5 stars".
- **The ladder screen, Leaderboard tab**: one line above the list, your standing: "League 5 · 2 of 5 stars · 3 wins in a row" (the streak shows from two wins). In the top league: "League 10 · 2011". *Picture: the badge at the start of the line; perhaps the stars as pips.*
- **The leaderboard rows**: a person below the top league has their league where the number was and their stars beside their name; a person in the top league their rating, and "League 10" beside their name; bots as before, "Fish (Expert Bot)" and its rating. People and bots stay one list, a person below the top sorted by their league's band plus their stars' share of it (league 8 with 2 of 5 stars sorts as 1740).
- **The versus moment**: a person below the top league shows nothing under their card; in the top league their rating in the gem; a bot its rating. *A design spot: the gem could hold the league's badge.*
- **The end of a ranked match**: one line about the stars under Victory or Defeat. Below the top league no rating counter; in the top league the rating counts from before to after as today. *A design spot: moving up deserves its own moment.*

## Open calls

1. **Names.** Open, for a session of its own (Martin, 2026-11-05: "leave placeholder 1-10 for now"). The screens say "League 1" to "League 10" until then.
2. **Pictures.** None in this build. Settled (Martin, 2026-11-10): the player owns the picture, the league owns the border, the way League of Legends rings a player's own icon with a rank border; Hearthstone's way, a picture per rank, is out. In his words, on profile pictures: "I wanted to create something like that anyway, it naturally transitions into achievement feature as well". The game has no profile pictures yet, so they come first. Open: what the border is made of, how a league reads in it, the top league's piece, the promotion moment. The rounds of 2026-11-06 (`design/league-progress/`, an animal per league in a rim) are superseded. What other games draw: https://claude.ai/artifact/WBVqUZAfNmR6k1ZDKFSna9
3. **Season resets.** Recommendation: none while few people play. With opponents by league, a reset is only a fresh climb: everyone down a few leagues, back where they belong in a session or two.

## Names

Open (Martin, 2026-11-05: "leave placeholder 1-10 for now and I'll come back to this"). What the first look found:

- Names from the game's own cards (the food chain set: Mouse, Rabbit, Squirrel, Fox, Badger, Lynx, Wolf, Leopard, Bear, Lion) felt wrong to Martin ("there's a reason LoL leagues aren't named after champions and HS leagues aren't named after cards"). Why such names fail: a rank needs an order the player already knows; a card name as a league ranks the card itself (the bottom league's card reads as the weakest); cards are reworked and renamed, a rank must outlive that; "I'm Mouse" reads as an insult.
- Gwent names none: ranks 30 down to 1, then Pro Rank. Hearthstone and League of Legends use metals and gems, an order everyone knows; ten of them runs out of instantly known ones after about six.
- The other set drafted, a life (Egg, Hatchling, Cub, Yearling, Forager, Hunter, Stalker, Alpha, Elder, Apex), has the card-world problem less but Apex clashes with the Apex Predator keyword. Stones (Sand to Diamond) were drafted too.
- Recommendation from that look: numbered leagues, and one name for the top league, where a name earns its place (Legend, Pro Rank).

## Migration

Existing profiles get a league once, from their current rating, when the server first starts with leagues (`tiers.from_rating`, run by `Tiers.migrate`): the league whose band holds their rating, at most league 9 (the top is reached by a win), with 0 stars. A profile still placing (under 10 rated games) starts in league 1. Examples: 1820 is league 9, 1500 is league 6, 1250 is league 3. Opponents come from that league, so a profile placed a little wrong finds its level in a few games. Bots get no league row: theirs is read from their rating.

## News entry (draft, not shipped)

**Ranked has leagues.** Ranked is now a climb: ten leagues, from League 1 to the top. A win gains a star, and from your third win in a row two; a loss loses one, and with no stars left it drops you a league. Every league has its own opponents, stronger as you climb, so your league says how good you are. In the top league stars end and your rating shows, the number that picks your opponents there. Your league starts from your rating. Bots don't have leagues; they keep their names, Beginner to Legendary.

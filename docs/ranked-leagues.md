# Ranked leagues

Martin, 2026-11-04: instead of ranked being a rating from the start, do what Hearthstone, Gwent, MTG Arena and League do: about ten leagues, each with a few stars; a win gains a star, a loss loses one; a bonus for win streaks; a few stars to move up; checkpoints below which you can't fall; the uncapped rating only in the highest league. Nothing elaborate. The point is progression instead of a flat number.

This page: what those four games do and what each mechanic is for, the recommended design for this game, the simulation that set its numbers, the calls that are Martin's, the names, the migration, and a draft News entry.

Status: designed, simulated and built on the branch `ranked/leagues`; nothing shipped. The rules live in one file, `animal_kingdom/web/tiers.py`, which the server and the simulator both use.

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

## Why the plain Hearthstone rules don't fit here

The first draft was Hearthstone's rules alone (stars, streaks, floors, nothing tied to the rating). The simulation showed the flaw: here, the rating picks every ranked opponent from bots that are always there (`Ladder.nearest_bot`, within 75 points), so once a person's rating settles, they win about half their games, whatever their strength. Stars with floors and a streak bonus climb at 50%: floors stop the falls and streaks add extra wins. A weak player (true strength 1200) reached the top league in a median of 265 games, a 1500 player in 281. The league would measure games played, not skill.

HS and LoL avoid this by tying star gains to the hidden rating (the Star Bonus; LP by MMR). The recommended design does the same, in two rules that each fit in a sentence: a win pays double while your rating is ahead of your league, and a loss costs double while your rating is well behind it. With those, the 1200 player settles in league 4 (its checkpoint) and the 1500 player in league 7.

## The recommended design

The rating keeps running for everyone, bots included, and still picks every ranked opponent; nothing about matchmaking or how bots are rated changes. Leagues and stars are the person's view, updated on every rated game where a person sat (a person against a bot, or two people), next to the rating, never instead of it. The number shows only in the top league.

Each league has a **par**: the rating it stands for, 1000 for league 1 up to 1900 for league 10, 100 apart. The top league's par is the bot band Legendary (1900), so the top league and the top bot band mean the same thing.

| League | Stars to move up | Par rating | Checkpoint | A loss costs |
|---|---|---|---|---|
| 1 | 3 | 1000 | yes (the start) | nothing |
| 2 | 3 | 1100 | | nothing |
| 3 | 3 | 1200 | | nothing |
| 4 | 5 | 1300 | yes | 1 star (2 if over-ranked); never below league 4 once reached |
| 5 | 5 | 1400 | | 1 star (2 if over-ranked) |
| 6 | 5 | 1500 | | 1 star (2 if over-ranked) |
| 7 | 5 | 1600 | yes | 1 star (2 if over-ranked); never below league 7 once reached |
| 8 | 5 | 1700 | | 1 star (2 if over-ranked) |
| 9 | 5 | 1800 | | 1 star (2 if over-ranked) |
| 10 (top) | none: the rating shows | 1900 | yes | nothing on the league; the rating moves as always |

The rules, each one a test in `animal_kingdom/tests/test_tiers.py`:

1. **Start.** Everyone starts in league 1 with 0 stars.
2. **A win** gains 1 star. It gains 2 if either bonus applies (never more than 2):
   - **win streak**: it is your third win in a row or more, you are in leagues 1 to 7, and your rating is at least your league's par;
   - **rating bonus**: your rating is at least the next league's par (you are ahead of your league).
3. **Moving up.** Reaching the league's star count moves you up with 0 stars; a spare star carries over. Reaching league 10 ends stars.
4. **A loss** costs 1 star, nothing in leagues 1 to 3, and 2 when you are **over-ranked**: your rating is more than 100 under your league's par.
5. **Moving down.** A loss with no stars left (or fewer than it costs) moves you down a league, onto that league's top minus what was left to pay (5 stars needed, a 1-star loss: 4 stars).
6. **Checkpoints.** Leagues 1, 4, 7 and 10. Once you reach one, you never go below it: a loss there at 0 stars costs nothing.
7. **The top league** has no stars. It shows your rating, the ladder's own number, and you never leave it (there are no seasons; see Martin's calls).
8. **The rating** the bonuses read is your ladder rating going into the game.
9. **What you see**: the league's name, your stars as a count ("3 of 5 stars"), your checkpoint, your win streak; in the top league, the rating. The end of a ranked match says what the game did in one line ("+2 stars (win streak): League 5, 1 of 5 stars", "No star lost (League 4 is a checkpoint)", "Up to League 7, 0 stars").

What each part is doing here: the three-star leagues with no losses are the first session (three promotions in the first ten or so games); the checkpoints at 4 and 7 keep what an evening earned; the streak bonus moves a winner fast but stops at league 7 and only pays a player who isn't already over-ranked; the rating bonus is Hearthstone's Star Bonus made continuous (a player whose rating is ahead of their league catches up at two stars a win, so a returning or migrated player is home in a few wins, and no reset is needed for it to work); the over-ranked double loss is LoL's LP-by-MMR, the brake that stops grinding past your strength.

## The simulation

`tools/ranked/simulate.py` replays the recorded results through `web/tiers.py`; `--players results/players.json` (from `deploy/deploy.sh players`, not available in this session) gives exact people and ranked-only games.

How the people were read without that file: the game logs carry the seats, decks, winner, match id and date, but not who played or whether the game was ranked. So every human-against-bot game from 1 October (the ladder's first day) counts, and the person is read off the deck: Kalista's mono Cats (at least 90% Cats, before 17 October), Laras's lists on Black Bear, Owl and Raven (until 6 October, her sixth day), Martin for the rest. That matches the playtest read of 2 October (Laras 208 games, Kalista mono Cats) but is an inference: some games are surely misfiled, practice games are counted as ranked, and the two guests are folded into Martin. Games between two people are left out (both sides unknown). The rating the rules read is replayed with the ladder's own Glicko-2 against each bot's 24 October seed rating, not the rating it had on the day, so the ratings below are close, not exact.

**The people** (games are every logged human-vs-bot game, ranked or not):

| Person | Games | Won | Days | Reached league 4 / 7 / 9 / top after | League at the end |
|---|---|---|---|---|---|
| Martin | 1,228 | 62% | 31 | 5 / 14 / 25 / 33 games | top (1 Oct, his first day) |
| Laras | 663 | 84% | 5 | 6 / 25 / 30 / 42 games | top (1 Oct, her first day) |
| Kalista | 284 | 58% | 13 | 7 / 44 / 111 / 245 games | league 7 after day 1, 8 from 7 Oct, top on 10 Oct |

None of the three played "a few games a day": Laras played 177 games on her first day, Martin 123, Kalista 87. Measured in games, Martin and Laras reach the top in 33 and 42, and Kalista, who started weak and improved (she lost three of four on day one and beat the Expert more often than not by day twelve), climbs over ten days and 245 games, sitting at league 7 for a week while her rating caught up. That is the shape wanted: the strong players' climb is quick, the learning player's climb follows her learning.

**By day**, under the recommended rules: the league at the end of each day each person played ("top, 1850" is the top league with the rating replayed that day; the count in brackets is their games so far; a blank is a day they didn't play). Martin and Laras reach the top on their first day because they played over a hundred games that day; Kalista's row is the climb of a learning player.

| Day | Martin | Laras | Kalista |
|---|---|---|---|
| 10-01 | top, 1850 (123) | top, 1858 (177) | 7, 4 of 5 stars (87) |
| 10-02 | top, 1907 (170) | top, 2073 (269) | 7, 4 of 5 stars (116) |
| 10-04 | top, 1918 (202) | top, 2000 (604) | 7, 2 of 5 stars (126) |
| 10-05 | top, 1996 (217) | top, 2185 (652) | 7, 4 of 5 stars (148) |
| 10-06 | top, 2011 (219) | top, 2213 (663) | 7, 3 of 5 stars (149) |
| 10-07 | top, 2024 (221) |  | 8, 0 of 5 stars (163) |
| 10-08 | top, 2016 (229) |  | 8, 2 of 5 stars (215) |
| 10-09 | top, 1926 (246) |  | 8, 2 of 5 stars (233) |
| 10-10 | top, 2019 (379) |  | top, 1986 (258) |
| 10-11 | top, 1978 (385) |  |  |
| 10-12 | top, 2071 (399) |  | top, 2023 (273) |
| 10-13 | top, 2123 (418) |  | top, 2042 (276) |
| 10-14 | top, 2003 (440) |  |  |
| 10-15 | top, 1975 (528) |  | top, 2060 (279) |
| 10-16 | top, 2053 (559) |  | top, 2026 (284) |
| 10-17 | top, 2133 (617) |  |  |
| 10-18 | top, 2089 (619) |  |  |
| 10-19 | top, 2112 (632) |  |  |
| 10-20 | top, 2108 (635) |  |  |
| 10-21 | top, 1901 (669) |  |  |
| 10-22 | top, 2015 (690) |  |  |
| 10-23 | top, 2174 (717) |  |  |
| 10-24 | top, 2148 (782) |  |  |
| 10-25 | top, 2090 (828) |  |  |
| 10-26 | top, 2100 (846) |  |  |
| 10-27 | top, 1918 (896) |  |  |
| 10-28 | top, 1908 (907) |  |  |
| 10-29 | top, 1803 (1018) |  |  |
| 10-30 | top, 1948 (1132) |  |  |
| 10-31 | top, 1908 (1210) |  |  |
| 11-04 | top, 1820 (1228) |  |  |

**Synthetic players**, 300 runs each, 400 games. A fixed win rate, as asked (the rating moved by those results against opponents at the player's own rating):

| Win rate | Games to reach league 4 | 6 | 8 | 9 | top |
|---|---|---|---|---|---|
| 40% | 13 | never (stops at 5) | | | |
| 50% | 10 | 27 | 64 | 76 | not in 400 |
| 60% | 8 | 19 | 33 | 44 | 64 |

A fixed win rate isn't stable on this ladder (matchmaking pulls everyone to 50%), so the more honest model is a fixed strength, with opponents within the matchmaking window of the player's current rating:

| True strength | League after 10 / 25 / 50 / 100 / 200 / 400 games | Games to the top |
|---|---|---|
| 1200 | 3 / 4 / 4 / 4 / 4 / 4 | never |
| 1400 | 3–4 / 4 / 5 / 5 / 7 / 7 | never |
| 1600 | 4 / 5 / 7 / 7 / 7 / 8 | never |
| 1800 | 4 / 6 / 8 / 9 / 10 / 10 | 112 |
| 2000 | 4 / 7 / 10 / 10 / 10 / 10 | 47 |
| 2200 | 5 / 8 / 10 / 10 / 10 / 10 | 36 |

For a person playing five ranked games a day: the first three promotions in the first session; a 2000 player (about Laras's level against the Expert) at the top in under two weeks, a 2200 player in about a week; an 1800 player (about where Martin's rating sits) in about three weeks, and their league then sits near their rating; players under 1800 settle at a league near their strength, held up a little by the checkpoints. Nobody reaches the top by playing a lot.

**What moved during the tuning**, all on the same seeds:

- The plain Hearthstone draft (3, 3, 3 then 4, 4, 4 then 5, 5, 5 stars; no rating ties): a 1200 player at the top in 265 games, a 1500 player in 281. Too easy for the weak, because of the 50% pull above.
- Adding the over-ranked double loss alone: the 1200 player stops at league 4–5 and the 1500 player at 7; the strong players unchanged. It does most of the work.
- Adding the streak-only-at-par rule alone: the 1200 player at league 6 after 300 games, the 1500 player at 8. Weaker on its own, but it stops a streak from pushing an over-ranked player further.
- Leagues 4 to 6 at 5 stars instead of 4: about 5 more games to the top for strong players and a slower middle, chosen so the table reads "3 stars at the bottom, 5 above".
- Over-ranked at 50 instead of 100 points: no difference worth the stricter rule.

## What a player sees, screen by screen

Text only, as built on the branch; where a picture belongs is marked. For Martin to design from.

- **Home, the Ladder piece** (top-right corner): "Ladder", under it the league and place: "League 5 · 2 of 5 stars · #7"; in the top league "League 10 · 2011 · #2". A newcomer who hasn't played ranked sees "Ladder" alone. *Picture: the league's badge beside the word.*
- **Home, the Ranked choice**: under "Ranked", the league instead of "your rating 1500?": "League 5 · 2 of 5 stars".
- **The ladder screen, Leaderboard tab**: one line above the list, your standing: "League 5 · 2 of 5 stars · never below League 4 · 3 wins in a row" (the streak shows from two wins; the checkpoint always). In the top league: "League 10 · 2011". *Picture: the badge at the start of the line; perhaps the stars as pips instead of the count.*
- **The leaderboard rows**: a person below the top league has their league where the number was ("League 5") and their stars beside their name ("2 of 5 stars"); a person in the top league has their rating where the number was and "League 10" beside their name; bots as before, "Fish (Expert Bot)" and its rating. The list is one, people and bots, people placed by league and stars. *Picture: a small badge in the row.*
- **The versus moment** (two cards facing each other as a match opens): a person below the top league shows nothing under their card; in the top league their rating in the gem as before; a bot its rating in the gem. *A design spot: the gem could hold the league's badge.*
- **The end of a ranked match**: under Victory or Defeat and how it ended, one line about the stars: "+1 star: League 5, 1 of 5 stars", "+2 stars (win streak): …", "+2 stars (rating bonus): …", "-1 star: …", "-2 stars: …", "No star lost (no stars lost in leagues 1 to 3): League 2, 1 of 3 stars", "No star lost (League 4 is a checkpoint): …", "Up to League 7, 0 stars", "Down to League 4, 4 stars". Below the top league no rating counter; in the top league the rating counts from before to after as it does today, and the line shows only on the game that brought you there ("Up to League 10"). *A design spot: moving up deserves its own moment (the badge arriving), and the stars could fill one by one.*
- **The match history**: unchanged; a ranked game says "Ranked" as before.

## Martin's calls

1. **Names.** Recommendation: the food chain set (below). Each league then has a picture that already exists, the animal's own card painting, and the climb is the game's world. Until then the screens say "League 1" to "League 10".
2. **Pictures.** None in this build. Recommendation: each league's animal portrait from its card art, in the rim the history rows already use for decks (`kit2/rim_n.webp`), on the ladder screen and at the end of a match; the top league its own piece. A design job for the sandbox, not an agent.
3. **Whether bots show a league.** Recommendation: no. Bots aren't climbing: their rating is their identity and the band word already names it ("Fish (Expert Bot)"). A bot with a league computed from its rating would be a league that never moves by stars, next to people whose leagues do, and the leaderboard would show two meanings of the same word. So bot rows keep their band and rating; people's rows show their league.
4. **Season resets.** Recommendation: none until there are enough players to fill a monthly ladder (dozens playing each week). A reset for five players is a chore, and the rating bonus already does what Hearthstone's reset bonus does. When seasons come: monthly, everyone down four leagues but never below checkpoint 4, the top league kept by the best few; the rating never resets.
5. **The numbers on the versus moment and the leaderboard.** The design says the number shows only in the top league. This build follows it for people (a person's row and seat show their league; the top league shows the rating) and keeps the bots' numbers (they have no league). Recommendation: keep it that way.
6. **The leaderboard's order.** People and bots are still one list. A person below the top is placed by their league, par plus their stars' share of the next 100 points (league 8 with 2 of 5 stars sorts as 1740), a person in the top league by their rating, a bot by its rating. Recommendation: keep one list; the alternative, people only, loses the bots as landmarks.

## Names

Three sets of ten, bottom first.

- **The food chain** (this game's own animals, from prey to Apex): Mouse, Rabbit, Squirrel, Fox, Badger, Lynx, Wolf, Leopard, Bear, Lion. The feel: you start as something everything eats and end as the animal nothing eats, and every step is a card you know.
- **Stones** (the menus' own granite and slabs): Sand, Clay, Slate, Flint, Granite, Basalt, Marble, Jade, Obsidian, Diamond. The feel: quiet and of a piece with the screens, but it says nothing about animals, and only the last two sound like an achievement.
- **A life** (an animal's life from the egg, and the Eggs are in the game): Egg, Hatchling, Cub, Yearling, Forager, Hunter, Stalker, Alpha, Elder, Apex. The feel: growing up rather than beating others; Apex as the top echoes Apex Predator, which is a strength (the top league as the keyword) and a risk (players may read it as the keyword).

Bronze to Diamond reads instantly and says nothing; it is the fallback if none of these lands.

## Migration

Existing profiles get a league from their current rating once, when the server first starts with leagues (`tiers.from_rating`, run by `server.migrate_tiers`): two leagues under the league their rating stands for (the highest league whose par is at or under the rating), so at most league 8 (the top is always earned), at that league's checkpoint, with 0 stars. A profile still placing (under 10 rated games) starts at league 1. Examples: 1820 stands for league 9, starts in league 7 (checkpoint 7); 1500 stands for league 6, starts in league 4; 1250 stands for league 3, starts in league 1.

Why two under: putting everyone straight where their rating says would make the first ranked game after the release say nothing. Two leagues under, with the rating bonus, a player whose rating is ahead gains two stars a win and is back where they belong in about eight wins (an 1820 player from league 7 to the top: 15 stars at 2 a win), so the release is felt as a climb, not taken away. Bots get nothing: they have no league.

## News entry (draft, not shipped)

**Ranked has leagues.** Ranked is now a climb: ten leagues, from League 1 to the top. A win gains a star, a loss loses one, and a few stars move you up a league; in the first three leagues a loss costs nothing. Three wins in a row pay double, and so does winning while your rating is ahead of your league, so a strong player climbs fast; leagues 4 and 7 are checkpoints you never fall below once you reach them. In the top league stars end and your rating shows, the same number that has always picked your opponents. Your league starts from your rating, two leagues under where it puts you, so your next few wins carry you back up. Bots don't have leagues; they keep their names, Beginner to Legendary.

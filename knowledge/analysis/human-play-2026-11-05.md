# How people play: the recorded human games, 2026-09-26 to 2026-11-04

What the 2,421 web game logs under `results/human_games/web/` say about how people use the cards, built by `tools/human_play.py` (its docstring has the definitions: turn, row, played, the replay check). Every table below is that tool's output on the logs as committed on 2026-11-05; rerun it to refresh them. Analysis only: nothing in the game changed.

The logs carry no player id, and STATUS names three or four people behind most of these games, so each rate is the habits of a few players, not of a population. Person win rates are high (67% against the Expert) for the same reason.

## Corpus

|  | games |
|---|---|
| web game logs | 2421 |
| dates | 20260926 to 20261104 |
| seats human/expert | 1916 |
| seats human/normal | 420 |
| seats human/easy | 45 |
| seats human/human | 40 |
| replay on today's cards | 12% (299/2421) |
| no replay: EngineError | 1631 |
| no replay: KeyError | 322 |
| no replay: ValueError | 169 |
| placements credited by list (no replay) | 42073 |
| placements left uncredited (no replay; card in both lists, or in neither: a token) | 4032 |
| ad-hoc recorder lines skipped (no actions) | 16 |

Most of the record no longer replays: only 12% of games (299) replay on today's cards and end as their logs say. The rest fail on cards that changed or left the pool. For those, plays are credited by which deck list holds the card, which works for most placements: 4,032 of about 46,000 placements stay uncredited: cards both decks held in the same game, and tokens. The questions that need turns rest on replays. The den within five turns uses the 299 full replays; turns 1 and 2 also use games whose replay gets through both players' first two turns before it breaks.

## Cards in people's decks

2295 person-games with a known list (a game between two people counts twice). In a deck: share of those person-games whose list held the card; copies: mean copies when held. Played in the game: of the person-games that held it and where a play can be credited (the game replays, or the opponent's list lacks the card), how many played it at least once. Played when in hand: of the replayed person-games where it reached the hand, how many played it. Win rate when played and deck win rate are the person's, over the same creditable person-games.

| card | status today | in a deck | copies | played in the game | played when in hand | win rate when played | deck win rate | played − deck (pts) |
|---|---|---|---|---|---|---|---|---|
| Black Bear (`black_bear`) | collectible | 42% (956/2295) | 2.8 | 73% (610/838) | 90% (19/21) | 76% (464/610) | 79% (662/838) | -3 |
| Hornet (`hornet`) | collectible | 41% (940/2295) | 2.0 | 39% (296/752) | 62% (18/29) | 72% (212/296) | 83% (627/752) | -12 |
| Prince Leo (`lion_legend`) | collectible | 40% (917/2295) | 1.0 | 60% (434/727) | 92% (24/26) | 77% (333/434) | 76% (554/727) | +1 |
| Princess Lea (`lion_legend_2`) | collectible | 40% (917/2295) | 1.0 | 61% (446/727) | 92% (24/26) | 77% (345/446) | 76% (554/727) | +1 |
| Owl (`owl`) | collectible | 39% (888/2295) | 3.0 | 72% (615/857) | 70% (7/10) | 78% (479/615) | 81% (690/857) | -3 |
| Raven (`raven`) | collectible | 38% (864/2295) | 2.7 | 51% (413/815) | 45% (5/11) | 67% (277/413) | 79% (642/815) | -12 |
| Serval (`serval`) | collectible | 34% (778/2295) | 2.1 | 45% (291/646) | 69% (20/29) | 65% (189/291) | 65% (422/646) | -0 |
| Bird Egg (`bird_egg`) | collectible | 33% (766/2295) | 3.0 | 61% (446/730) | 75% (6/8) | 73% (327/446) | 79% (576/730) | -6 |
| Aurum (`goose_legend`) | reserve | 32% (724/2295) | 1.0 | 59% (404/684) | 50% (2/4) | 74% (299/404) | 79% (542/684) | -5 |
| Alley Cat (`alley_cat`) | collectible | 27% (622/2295) | 2.7 | 66% (374/569) | 74% (20/27) | 64% (238/374) | 66% (374/569) | -2 |
| Lion (`lion`) | collectible | 27% (611/2295) | 3.0 | 66% (364/549) | 58% (18/31) | 67% (243/364) | 66% (362/549) | +1 |
| Lynx (`lynx`) | collectible | 26% (588/2295) | 2.8 | 70% (381/543) | 48% (12/25) | 67% (254/381) | 67% (362/543) | +0 |
| Queen Adira (`lion_legend_4`) | collectible | 26% (587/2295) | 1.0 | 46% (250/542) | 75% (9/12) | 72% (179/250) | 67% (361/542) | +5 |
| King Theron (`lion_legend_3`) | collectible | 25% (575/2295) | 1.0 | 47% (251/531) | 77% (10/13) | 72% (180/251) | 67% (357/531) | +4 |
| Chameleon (`chameleon`) | collectible | 25% (563/2295) | 2.0 | 20% (98/482) | 71% (12/17) | 71% (70/98) | 85% (410/482) | -14 |
| [MOLE] (`mole_legend`) | collectible | 24% (556/2295) | 1.0 | 43% (203/472) | 83% (10/12) | 92% (187/203) | 88% (414/472) | +4 |
| Mouse (`mouse`) | collectible | 24% (554/2295) | 3.0 | 65% (307/474) | 62% (16/26) | 85% (262/307) | 86% (410/474) | -1 |
| Caracal (`caracal`) | collectible | 23% (535/2295) | 3.0 | 60% (297/493) | 43% (10/23) | 69% (205/297) | 66% (324/493) | +3 |
| Ember (`pheasant_legend`) | collectible | 23% (518/2295) | 1.0 | 58% (275/477) | 80% (16/20) | 65% (178/275) | 62% (295/477) | +3 |
| Falcon (`falcon`) | collectible | 22% (514/2295) | 2.7 | 33% (147/440) | 53% (9/17) | 80% (117/147) | 90% (395/440) | -10 |
| Chinchilla (`chinchilla`) | reserve | 22% (501/2295) | 2.0 | 60% (252/420) | – (0/0) | 89% (224/252) | 89% (375/420) | -0 |
| Jerboa (`jerboa`) | reserve | 22% (499/2295) | 2.0 | 66% (276/419) | 100% (1/1) | 97% (267/276) | 90% (377/419) | +7 |
| Tiger (`tiger`) | collectible | 21% (486/2295) | 2.9 | 51% (212/416) | 54% (14/26) | 61% (129/212) | 60% (249/416) | +1 |
| Black Panther (`black_panther`) | collectible | 21% (475/2295) | 2.0 | 59% (265/448) | 67% (4/6) | 65% (173/265) | 65% (292/448) | +0 |
| Snow Leopard (`snow_leopard`) | reserve | 21% (475/2295) | 1.9 | 69% (301/436) | 86% (6/7) | 67% (202/301) | 64% (280/436) | +3 |
| Jaguar (`jaguar`) | collectible | 18% (423/2295) | 2.0 | 46% (179/386) | 67% (8/12) | 59% (106/179) | 59% (229/386) | -0 |
| [OCTOPUS] (`octopus_legend_2`) | collectible | 17% (397/2295) | 1.0 | 56% (180/323) | 100% (2/2) | 69% (125/180) | 63% (203/323) | +7 |
| Cougar (`cougar`) | reserve | 13% (306/2295) | 3.0 | 65% (186/284) | 67% (2/3) | 54% (101/186) | 55% (155/284) | -0 |
| Magpie (`magpie`) | collectible | 13% (306/2295) | 2.0 | 74% (208/280) | 50% (2/4) | 59% (123/208) | 56% (157/280) | +3 |
| Black Swan (`swan_legend`) | reserve | 13% (302/2295) | 1.0 | 8% (22/280) | 0% (0/1) | 68% (15/22) | 57% (159/280) | +11 |
| Black Mamba (`black_mamba`) | collectible | 12% (286/2295) | 1.7 | 63% (167/264) | 0% (0/1) | 72% (120/167) | 62% (165/264) | +9 |
| Hawk (`hawk`) | collectible | 12% (285/2295) | 1.6 | 49% (129/263) | 33% (1/3) | 60% (77/129) | 59% (156/263) | +0 |
| Python (`python`) | collectible | 10% (238/2295) | 2.7 | 67% (155/232) | 38% (3/8) | 74% (115/155) | 61% (141/232) | +13 |
| Rat (`rat`) | collectible | 10% (226/2295) | 3.0 | 70% (127/182) | 59% (10/17) | 64% (81/127) | 68% (124/182) | -4 |
| Lemming (`lemming`) | reserve | 9% (204/2295) | 3.0 | 73% (124/170) | – (0/0) | 93% (115/124) | 92% (157/170) | +0 |
| Bat (`bat`) | collectible | 8% (195/2295) | 3.0 | 61% (94/154) | 60% (3/5) | 65% (61/94) | 64% (99/154) | +1 |
| Snake Egg (`snake_egg`) | collectible | 8% (184/2295) | 3.0 | 77% (137/179) | 62% (5/8) | 64% (87/137) | 61% (109/179) | +3 |
| Chipmunk (`chipmunk`) | collectible | 7% (165/2295) | 3.0 | 70% (115/164) | 81% (42/52) | 54% (62/115) | 51% (83/164) | +3 |
| Hummingbird (`hummingbird`) | collectible | 7% (154/2295) | 2.0 | 62% (93/151) | 75% (15/20) | 61% (57/93) | 60% (90/151) | +2 |
| [LEOPARD] (`leopard_legend`) | collectible | 7% (150/2295) | 1.0 | 44% (58/131) | 100% (8/8) | 72% (42/58) | 64% (84/131) | +8 |
| Hamster (`hamster`) | collectible | 6% (134/2295) | 2.9 | 55% (73/133) | 68% (32/47) | 59% (43/73) | 53% (70/133) | +6 |
| Flying Squirrel (`flying_squirrel`) | collectible | 6% (131/2295) | 2.0 | 50% (66/131) | 68% (23/34) | 70% (46/66) | 52% (68/131) | +18 |
| Honey Badger (`honey_badger`) | collectible | 6% (131/2295) | 2.0 | 40% (36/90) | 78% (7/9) | 69% (25/36) | 53% (48/90) | +16 |
| Squirrel (`squirrel`) | collectible | 6% (131/2295) | 3.0 | 45% (59/131) | 40% (18/45) | 73% (43/59) | 52% (68/131) | +21 |
| Eon (`anaconda_legend`) | collectible | 6% (130/2295) | 1.0 | 53% (63/118) | 100% (5/5) | 59% (37/63) | 56% (66/118) | +3 |
| Giraffe (`giraffe`) | collectible | 6% (130/2295) | 3.0 | 62% (76/123) | 59% (16/27) | 57% (43/76) | 50% (62/123) | +6 |
| Porcupine (`porcupine`) | collectible | 6% (128/2295) | 2.0 | 58% (74/127) | 89% (31/35) | 47% (35/74) | 49% (62/127) | -2 |
| Bobcat (`bobcat`) | collectible | 5% (126/2295) | 3.0 | 74% (80/108) | 70% (14/20) | 79% (63/80) | 75% (81/108) | +4 |
| Chimpanzee (`chimpanzee`) | collectible | 5% (126/2295) | 2.7 | 62% (71/115) | 47% (7/15) | 79% (56/71) | 62% (71/115) | +17 |
| Groundhog (`groundhog`) | collectible | 5% (125/2295) | 2.3 | 49% (61/124) | 78% (31/40) | 57% (35/61) | 51% (63/124) | +7 |
| Tally (`chipmunk_legend`) | collectible | 5% (123/2295) | 1.0 | 16% (20/123) | 36% (9/25) | 90% (18/20) | 51% (63/123) | +39 |
| Elephant (`elephant`) | collectible | 5% (123/2295) | 2.9 | 54% (62/114) | 55% (11/20) | 58% (36/62) | 54% (61/114) | +5 |
| Gopher (`gopher`) | collectible | 5% (123/2295) | 2.9 | 55% (68/123) | 58% (26/45) | 54% (37/68) | 51% (63/123) | +3 |
| Mole (`mole`) | collectible | 5% (123/2295) | 2.0 | 58% (62/106) | 86% (24/28) | 71% (44/62) | 65% (69/106) | +6 |
| Orangutan (`orangutan`) | collectible | 5% (122/2295) | 2.0 | 64% (77/121) | 62% (10/16) | 81% (62/77) | 67% (81/121) | +14 |
| Tarsier (`tarsier`) | collectible | 5% (122/2295) | 2.0 | 61% (74/121) | 69% (9/13) | 73% (54/74) | 67% (81/121) | +6 |
| [RAT] (`rat_legend`) | collectible | 5% (121/2295) | 1.0 | 24% (29/121) | 40% (8/20) | 69% (20/29) | 52% (63/121) | +17 |
| Rattlesnake (`rattlesnake`) | reserve | 5% (121/2295) | 2.5 | 64% (76/118) | – (0/0) | 71% (54/76) | 61% (72/118) | +10 |
| Dormouse (`dormouse`) | collectible | 5% (120/2295) | 2.0 | 57% (68/120) | 80% (28/35) | 53% (36/68) | 51% (61/120) | +2 |
| Egg Eater (`egg_eater`) | collectible | 5% (120/2295) | 2.5 | 52% (61/117) | 33% (2/6) | 67% (41/61) | 59% (69/117) | +8 |
| Caterpillar (`caterpillar`) | collectible | 5% (119/2295) | 3.0 | 31% (37/118) | 6% (1/18) | 78% (29/37) | 67% (79/118) | +11 |
| The First of Many (`locust_legend`) | collectible | 5% (118/2295) | 1.0 | 35% (41/116) | 67% (8/12) | 71% (29/41) | 61% (71/116) | +10 |
| Baboon (`baboon`) | collectible | 5% (115/2295) | 3.0 | 69% (79/114) | 69% (11/16) | 71% (56/79) | 68% (78/114) | +2 |
| [GORILLA] (`orangutan_legend`) | collectible | 5% (115/2295) | 1.0 | 53% (60/114) | 67% (8/12) | 75% (45/60) | 68% (78/114) | +7 |
| Macaque (`macaque`) | collectible | 5% (113/2295) | 2.2 | 49% (55/112) | 43% (6/14) | 80% (44/55) | 65% (73/112) | +15 |
| Leopard (`leopard`) | collectible | 5% (112/2295) | 2.0 | 69% (73/106) | 100% (16/16) | 70% (51/73) | 76% (81/106) | -7 |
| Pestis (`rat_legend_2`) | collectible | 5% (109/2295) | 1.0 | 36% (36/101) | 100% (3/3) | 61% (22/36) | 59% (60/101) | +2 |
| Gorilla (`gorilla`) | collectible | 5% (108/2295) | 3.0 | 57% (62/108) | 44% (8/18) | 76% (47/62) | 68% (73/108) | +8 |
| Boar (`boar`) | collectible | 5% (104/2295) | 2.7 | 63% (65/103) | 74% (20/27) | 65% (42/65) | 59% (61/103) | +5 |
| Orca (`orca`) | collectible | 5% (104/2295) | 2.0 | 58% (57/98) | 80% (4/5) | 68% (39/57) | 55% (54/98) | +13 |
| Gazelle (`gazelle`) | collectible | 4% (103/2295) | 3.0 | 34% (35/103) | 30% (9/30) | 74% (26/35) | 56% (58/103) | +18 |
| Big Gus (`capybara_legend`) | collectible | 4% (102/2295) | 1.0 | 23% (23/102) | 45% (9/20) | 65% (15/23) | 51% (52/102) | +14 |
| [WHITE WOLF] (`wolf_legend_3`) | collectible | 4% (101/2295) | 1.0 | 43% (42/98) | 100% (7/7) | 67% (28/42) | 53% (52/98) | +14 |
| Cape Buffalo (`cape_buffalo`) | collectible | 4% (100/2295) | 2.4 | 51% (49/97) | 81% (22/27) | 55% (27/49) | 55% (53/97) | +0 |
| Hippopotamus (`hippopotamus`) | collectible | 4% (99/2295) | 2.0 | 52% (49/95) | 77% (10/13) | 41% (20/49) | 43% (41/95) | -2 |
| Lord Bumbleton (`bumblebee_legend`) | collectible | 4% (98/2295) | 1.0 | 42% (40/96) | 38% (3/8) | 65% (26/40) | 69% (66/96) | -4 |
| Cheetah (`cheetah`) | collectible | 4% (97/2295) | 2.9 | 40% (36/90) | 33% (6/18) | 69% (25/36) | 69% (62/90) | +1 |
| Grizzly Bear (`grizzly_bear`) | collectible | 4% (96/2295) | 3.0 | 57% (52/92) | 0% (0/2) | 69% (36/52) | 60% (55/92) | +9 |
| Beaver (`beaver`) | collectible | 4% (95/2295) | 2.0 | 45% (40/89) | 67% (18/27) | 72% (29/40) | 66% (59/89) | +6 |
| Deer (`deer`) | collectible | 4% (95/2295) | 3.0 | 67% (64/95) | 79% (26/33) | 61% (39/64) | 57% (54/95) | +4 |
| Okapi (`okapi`) | collectible | 4% (93/2295) | 2.0 | 61% (57/93) | 81% (21/26) | 61% (35/57) | 57% (53/93) | +4 |
| Wildebeest (`wildebeest`) | collectible | 4% (93/2295) | 3.0 | 68% (63/93) | 70% (21/30) | 60% (38/63) | 57% (53/93) | +3 |
| Zebra (`zebra`) | collectible | 4% (93/2295) | 2.6 | 46% (43/93) | 47% (16/34) | 70% (30/43) | 57% (53/93) | +13 |
| Raccoon (`raccoon`) | collectible | 4% (91/2295) | 2.0 | 46% (42/91) | 53% (10/19) | 67% (28/42) | 55% (50/91) | +12 |
| Queen Solenia (`army_ant_legend`) | collectible | 4% (90/2295) | 1.0 | 31% (26/84) | 88% (7/8) | 81% (21/26) | 70% (59/84) | +11 |
| Queen Melissia (`bee_legend`) | collectible | 4% (88/2295) | 1.0 | 40% (34/86) | 100% (8/8) | 71% (24/34) | 71% (61/86) | -0 |
| Soldier Wasp (`guard_wasp`) | collectible | 4% (88/2295) | 3.0 | 49% (42/86) | 47% (7/15) | 74% (31/42) | 71% (61/86) | +3 |
| Vesper (`hornet_legend`) | collectible | 4% (88/2295) | 1.0 | 6% (5/86) | 0% (0/3) | 100% (5/5) | 71% (61/86) | +29 |
| Nurse Bee (`nurse_bee`) | collectible | 4% (88/2295) | 2.7 | 50% (43/86) | 65% (11/17) | 74% (32/43) | 71% (61/86) | +3 |
| Queen Bee (`queen_bee`) | collectible | 4% (88/2295) | 2.7 | 74% (64/86) | 73% (11/15) | 70% (45/64) | 71% (61/86) | -1 |
| Soldier Ant (`soldier_ant`) | collectible | 4% (88/2295) | 3.0 | 45% (39/86) | 59% (10/17) | 77% (30/39) | 71% (61/86) | +6 |
| Termite King (`termite_king`) | collectible | 4% (88/2295) | 2.0 | 55% (47/86) | 81% (13/16) | 77% (36/47) | 71% (61/86) | +6 |
| Termite Queen (`termite_queen`) | collectible | 4% (88/2295) | 2.0 | 57% (49/86) | 92% (11/12) | 76% (37/49) | 71% (61/86) | +5 |
| Worker Bee (`worker_bee`) | collectible | 4% (88/2295) | 3.0 | 55% (47/86) | 56% (10/18) | 77% (36/47) | 71% (61/86) | +6 |
| Worker Wasp (`worker_wasp`) | collectible | 4% (88/2295) | 3.0 | 83% (71/86) | 95% (18/19) | 70% (50/71) | 71% (61/86) | -1 |
| African Wild Dog (`african_wild_dog`) | collectible | 4% (87/2295) | 2.9 | 68% (58/85) | 75% (6/8) | 52% (30/58) | 49% (42/85) | +2 |
| Bush Dog (`bush_dog`) | collectible | 4% (87/2295) | 2.9 | 61% (52/85) | 100% (7/7) | 60% (31/52) | 49% (42/85) | +10 |
| Dhole (`dhole`) | collectible | 4% (87/2295) | 2.0 | 58% (49/85) | 60% (3/5) | 53% (26/49) | 49% (42/85) | +4 |
| Fox (`fox`) | collectible | 4% (87/2295) | 2.3 | 58% (49/85) | 83% (5/6) | 53% (26/49) | 49% (42/85) | +4 |
| Wolf (`wolf`) | collectible | 4% (87/2295) | 3.0 | 64% (54/85) | 50% (4/8) | 50% (27/54) | 49% (42/85) | +1 |
| [BLACK WOLF] (`wolf_legend_2`) | collectible | 4% (87/2295) | 1.0 | 45% (38/85) | 100% (4/4) | 58% (22/38) | 49% (42/85) | +8 |
| Mara (`mara`) | collectible | 4% (86/2295) | 3.0 | 65% (56/86) | 81% (35/43) | 55% (31/56) | 47% (40/86) | +9 |
| [RODENT] (`rodent_legend`) | collectible | 4% (86/2295) | 1.0 | 5% (4/86) | 13% (3/23) | 75% (3/4) | 47% (40/86) | +28 |
| City Spider (`city_spider`) | collectible | 4% (85/2295) | 3.0 | 87% (74/85) | 100% (21/21) | 55% (41/74) | 52% (44/85) | +4 |
| Cockroach (`cockroach`) | collectible | 4% (85/2295) | 3.0 | 80% (68/85) | 80% (16/20) | 57% (39/68) | 52% (44/85) | +6 |
| Earthworm (`earthworm`) | collectible | 4% (85/2295) | 2.1 | 69% (59/85) | 94% (16/17) | 56% (33/59) | 52% (44/85) | +4 |
| Piranha (`piranha`) | collectible | 4% (85/2295) | 2.7 | 61% (52/85) | 42% (8/19) | 63% (33/52) | 58% (49/85) | +6 |
| Vulture (`vulture`) | collectible | 4% (85/2295) | 3.0 | 12% (10/85) | 21% (4/19) | 20% (2/10) | 52% (44/85) | -32 |
| [BABOON] (`baboon_legend`) | collectible | 4% (84/2295) | 1.0 | 48% (40/84) | 86% (6/7) | 68% (27/40) | 62% (52/84) | +6 |
| Capybara (`capybara`) | collectible | 4% (84/2295) | 2.6 | 61% (51/84) | 100% (4/4) | 55% (28/51) | 57% (48/84) | -2 |
| Armadillo (`armadillo`) | collectible | 4% (82/2295) | 2.0 | 53% (43/81) | 0% (0/2) | 44% (19/43) | 44% (36/81) | -0 |
| Rhinoceros (`rhinoceros`) | collectible | 4% (82/2295) | 2.0 | 58% (45/78) | 56% (9/16) | 51% (23/45) | 45% (35/78) | +6 |
| Sperm Whale (`sperm_whale`) | collectible | 4% (82/2295) | 2.0 | 54% (44/82) | 53% (10/19) | 57% (25/44) | 56% (46/82) | +1 |
| Oxpecker (`oxpecker`) | collectible | 3% (80/2295) | 3.0 | 68% (52/77) | 56% (9/16) | 54% (28/52) | 44% (34/77) | +10 |
| Roach King (`cockroach_legend`) | collectible | 3% (79/2295) | 1.0 | 51% (40/79) | 93% (14/15) | 60% (24/40) | 56% (44/79) | +4 |
| Whale Shark (`whale_shark`) | collectible | 3% (79/2295) | 2.0 | 55% (43/78) | 50% (10/20) | 58% (25/43) | 49% (38/78) | +9 |
| Praying Mantis (`praying_mantis`) | collectible | 3% (78/2295) | 2.3 | 73% (57/78) | 95% (19/20) | 56% (32/57) | 54% (42/78) | +2 |
| Worker Ant (`worker_ant`) | collectible | 3% (78/2295) | 3.0 | 49% (38/78) | 29% (5/17) | 84% (32/38) | 71% (55/78) | +14 |
| [EAGLE] (`eagle_legend`) | collectible | 3% (77/2295) | 1.0 | 13% (10/77) | 22% (2/9) | 60% (6/10) | 64% (49/77) | -4 |
| Muskrat (`muskrat`) | reserve | 3% (77/2295) | 2.9 | 47% (36/76) | 33% (1/3) | 69% (25/36) | 57% (43/76) | +13 |
| Cottonmouth (`cottonmouth`) | reserve | 3% (75/2295) | 2.0 | 65% (45/69) | 100% (1/1) | 64% (29/45) | 58% (40/69) | +6 |
| [SPERM WHALE] (`sperm_whale_legend`) | collectible | 3% (75/2295) | 1.0 | 38% (28/74) | 45% (5/11) | 57% (16/28) | 47% (35/74) | +10 |
| Street Dog (`street_dog`) | collectible | 3% (75/2295) | 3.0 | 53% (39/74) | 75% (6/8) | 59% (23/39) | 54% (40/74) | +5 |
| Stork (`stork`) | collectible | 3% (74/2295) | 3.0 | 49% (36/74) | 14% (1/7) | 58% (21/36) | 61% (45/74) | -2 |
| Badger (`badger`) | collectible | 3% (73/2295) | 3.0 | 75% (51/68) | – (0/0) | 51% (26/51) | 51% (35/68) | -0 |
| Sardine (`sardine`) | collectible | 3% (73/2295) | 3.0 | 81% (54/67) | 96% (26/27) | 69% (37/54) | 66% (44/67) | +3 |
| [WILDEBEEST] (`wildebeest_legend`) | collectible | 3% (73/2295) | 1.0 | 30% (22/73) | 65% (11/17) | 64% (14/22) | 53% (39/73) | +10 |
| [BUTTERFLY] (`butterfly_legend`) | collectible | 3% (71/2295) | 1.0 | 32% (23/71) | 100% (7/7) | 83% (19/23) | 62% (44/71) | +21 |
| Azamandulai (`tortoise_legend`) | collectible | 3% (71/2295) | 1.0 | 50% (33/66) | 50% (1/2) | 27% (9/33) | 38% (25/66) | -11 |
| [ZEBRA] (`zebra_legend`) | collectible | 3% (71/2295) | 1.0 | 30% (21/71) | 69% (9/13) | 76% (16/21) | 54% (38/71) | +23 |
| Dung Beetle (`dung_beetle`) | collectible | 3% (70/2295) | 3.0 | 84% (58/69) | 84% (16/19) | 50% (29/58) | 46% (32/69) | +4 |
| Coyote (`coyote`) | collectible | 3% (69/2295) | 2.7 | 46% (32/69) | 33% (2/6) | 53% (17/32) | 52% (36/69) | +1 |
| Jackal (`jackal`) | collectible | 3% (69/2295) | 2.2 | 42% (29/69) | 88% (7/8) | 59% (17/29) | 52% (36/69) | +6 |
| Queen Ant (`queen_ant`) | collectible | 3% (66/2295) | 2.0 | 59% (34/58) | 93% (14/15) | 71% (24/34) | 60% (35/58) | +10 |
| Scarlett (`fox_legend`) | collectible | 3% (64/2295) | 1.0 | 38% (20/53) | 100% (1/1) | 75% (15/20) | 72% (38/53) | +3 |
| Ocelot (`ocelot`) | collectible | 3% (64/2295) | 2.0 | 70% (45/64) | 100% (12/12) | 80% (36/45) | 75% (48/64) | +5 |
| Blue Whale (`blue_whale`) | collectible | 3% (63/2295) | 3.0 | 35% (22/63) | 56% (9/16) | 59% (13/22) | 52% (33/63) | +7 |
| Marmot (`marmot`) | collectible | 3% (61/2295) | 3.0 | 23% (14/61) | 23% (8/35) | 79% (11/14) | 49% (30/61) | +29 |
| Warthog (`warthog`) | collectible | 3% (61/2295) | 3.0 | 31% (19/61) | 42% (11/26) | 68% (13/19) | 49% (30/61) | +19 |
| Hedgehog (`hedgehog`) | collectible | 3% (60/2295) | 2.8 | 57% (34/60) | 0% (0/2) | 56% (19/34) | 48% (29/60) | +8 |
| [GIRAFFE] (`giraffe_legend`) | collectible | 2% (57/2295) | 1.0 | 47% (27/57) | 86% (6/7) | 48% (13/27) | 47% (27/57) | +1 |
| Hyena (`hyena`) | collectible | 2% (56/2295) | 2.9 | 57% (31/54) | 75% (15/20) | 68% (21/31) | 54% (29/54) | +14 |
| [TIGER] (`tiger_legend`) | collectible | 2% (56/2295) | 1.0 | 27% (15/55) | 100% (4/4) | 73% (11/15) | 71% (39/55) | +2 |
| [OXPECKER] (`oxpecker_legend`) | collectible | 2% (55/2295) | 1.0 | 37% (20/54) | 40% (2/5) | 65% (13/20) | 52% (28/54) | +13 |
| Grimm (`raven_legend`) | collectible | 2% (55/2295) | 1.0 | 31% (17/55) | 40% (2/5) | 65% (11/17) | 67% (37/55) | -3 |
| Sunfish (`sunfish`) | collectible | 2% (54/2295) | 3.0 | 78% (42/54) | 96% (22/23) | 69% (29/42) | 70% (38/54) | -1 |
| Barracuda (`barracuda`) | collectible | 2% (52/2295) | 2.5 | 50% (26/52) | 62% (13/21) | 77% (20/26) | 71% (37/52) | +6 |
| [BAT] (`bat_legend`) | collectible | 2% (52/2295) | 1.0 | 31% (15/49) | 100% (4/4) | 73% (11/15) | 63% (31/49) | +10 |
| Cod (`cod`) | collectible | 2% (52/2295) | 3.0 | 77% (40/52) | 77% (17/22) | 75% (30/40) | 71% (37/52) | +4 |
| Mahi-mahi (`mahi_mahi`) | collectible | 2% (52/2295) | 4.5 | 63% (33/52) | 57% (13/23) | 79% (26/33) | 71% (37/52) | +8 |
| Manta Ray (`manta_ray`) | collectible | 2% (52/2295) | 2.0 | 40% (21/52) | 69% (11/16) | 67% (14/21) | 71% (37/52) | -4 |
| Remora (`remora`) | collectible | 2% (52/2295) | 2.0 | 62% (32/52) | 86% (19/22) | 78% (25/32) | 71% (37/52) | +7 |
| Swordfish (`swordfish`) | collectible | 2% (52/2295) | 2.0 | 42% (22/52) | 63% (12/19) | 68% (15/22) | 71% (37/52) | -3 |
| Tuna (`tuna`) | collectible | 2% (52/2295) | 3.0 | 56% (29/52) | 60% (12/20) | 86% (25/29) | 71% (37/52) | +15 |
| [BEE] (`bee_legend_2`) | collectible | 2% (50/2295) | 1.0 | 50% (25/50) | 100% (4/4) | 80% (20/25) | 60% (30/50) | +20 |
| [DEER] (`deer_legend`) | collectible | 2% (50/2295) | 1.0 | 34% (17/50) | 62% (10/16) | 59% (10/17) | 52% (26/50) | +7 |
| Impala (`impala`) | collectible | 2% (50/2295) | 2.0 | 56% (28/50) | 81% (13/16) | 50% (14/28) | 52% (26/50) | -2 |
| Toad (`toad`) | collectible | 2% (49/2295) | 3.0 | 51% (25/49) | 33% (1/3) | 52% (13/25) | 43% (21/49) | +9 |
| Butterfly (`butterfly`) | collectible | 2% (48/2295) | 3.0 | 79% (38/48) | 100% (12/12) | 74% (28/38) | 71% (34/48) | +3 |
| Hare (`hare`) | collectible | 2% (47/2295) | 3.0 | 59% (27/46) | 75% (18/24) | 74% (20/27) | 76% (35/46) | -2 |
| Moose (`moose`) | collectible | 2% (47/2295) | 2.1 | 66% (31/47) | 67% (4/6) | 52% (16/31) | 57% (27/47) | -6 |
| [WOLF] (`wolf_legend`) | reserve | 2% (47/2295) | 1.0 | 43% (20/47) | – (0/0) | 70% (14/20) | 51% (24/47) | +19 |
| Krill (`krill`) | collectible | 2% (44/2295) | 3.0 | 48% (21/44) | 38% (5/13) | 67% (14/21) | 52% (23/44) | +14 |
| Peacock (`peacock`) | collectible | 2% (43/2295) | 3.0 | 51% (22/43) | 39% (7/18) | 68% (15/22) | 49% (21/43) | +19 |
| [RHINOCEROS] (`rhinoceros_legend`) | collectible | 2% (42/2295) | 1.0 | 34% (13/38) | 25% (1/4) | 46% (6/13) | 37% (14/38) | +9 |
| Tortoise (`tortoise`) | collectible | 2% (42/2295) | 3.0 | 52% (22/42) | 100% (1/1) | 64% (14/22) | 48% (20/42) | +16 |
| [DUNG BEETLE] (`dung_beetle_legend`) | collectible | 2% (41/2295) | 1.0 | 20% (8/41) | 33% (2/6) | 62% (5/8) | 54% (22/41) | +9 |
| Ash (`honey_badger_legend`) | collectible | 2% (40/2295) | 1.0 | 41% (16/39) | 100% (4/4) | 50% (8/16) | 36% (14/39) | +14 |
| [KRILL] (`krill_legend`) | reserve | 2% (40/2295) | 1.0 | 32% (13/40) | 29% (2/7) | 46% (6/13) | 52% (21/40) | -6 |
| Andean Condor (`andean_condor`) | reserve | 2% (39/2295) | 1.4 | 44% (16/36) | – (0/0) | 50% (8/16) | 56% (20/36) | -6 |
| `handlock_legend_baboon` (no card today) | gone | 2% (38/2295) | 1.0 | 68% (25/37) | – (0/0) | 80% (20/25) | 78% (29/37) | +2 |
| `handlock_legend_butterfly` (no card today) | gone | 2% (38/2295) | 1.0 | 0% (0/37) | – (0/0) | – (0/0) | 78% (29/37) | – |
| `handlock_legend_eagle` (no card today) | gone | 2% (38/2295) | 1.0 | 16% (6/37) | – (0/0) | 83% (5/6) | 78% (29/37) | +5 |
| Golden Orb-Weaver (`golden_orb_weaver`) | collectible | 2% (37/2295) | 2.0 | 14% (5/37) | – (0/0) | 20% (1/5) | 51% (19/37) | -31 |
| Polar Bear (`polar_bear`) | reserve | 2% (37/2295) | 2.0 | 57% (17/30) | – (0/0) | 71% (12/17) | 60% (18/30) | +11 |
| Dart Frog (`dart_frog`) | collectible | 2% (36/2295) | 3.0 | 47% (17/36) | 0% (0/1) | 53% (9/17) | 50% (18/36) | +3 |
| [CUCKOO] (`cuckoo_legend`) | collectible | 2% (35/2295) | 1.0 | 40% (14/35) | 92% (12/13) | 57% (8/14) | 49% (17/35) | +9 |
| Meerkat (`meerkat`) | collectible | 1% (34/2295) | 2.0 | 32% (11/34) | 50% (1/2) | 64% (7/11) | 56% (19/34) | +8 |
| Sloth (`sloth`) | collectible | 1% (34/2295) | 3.0 | 90% (28/31) | 100% (6/6) | 46% (13/28) | 45% (14/31) | +1 |
| [FALCON] (`falcon_legend`) | collectible | 1% (33/2295) | 1.0 | 34% (11/32) | 75% (6/8) | 55% (6/11) | 75% (24/32) | -20 |
| [BOAR] (`boar_legend`) | collectible | 1% (32/2295) | 1.0 | 24% (7/29) | 75% (3/4) | 57% (4/7) | 41% (12/29) | +16 |
| Iris (`chameleon_legend`) | collectible | 1% (32/2295) | 1.0 | 29% (9/31) | 67% (2/3) | 44% (4/9) | 39% (12/31) | +6 |
| Jellyfish (`jellyfish`) | collectible | 1% (32/2295) | 3.0 | 44% (14/32) | – (0/0) | 43% (6/14) | 53% (17/32) | -10 |
| Anteater (`anteater`) | reserve | 1% (31/2295) | 3.0 | 70% (21/30) | 80% (4/5) | 33% (7/21) | 40% (12/30) | -7 |
| [MANTA RAY] (`manta_ray_legend`) | collectible | 1% (30/2295) | 1.0 | 40% (12/30) | 91% (10/11) | 75% (9/12) | 67% (20/30) | +8 |
| Tarantula (`tarantula`) | collectible | 1% (30/2295) | 2.0 | 63% (19/30) | 88% (14/16) | 53% (10/19) | 40% (12/30) | +13 |
| Nurse Bumblebee (`nurse_bumblebee`) | collectible | 1% (28/2295) | 2.0 | 54% (15/28) | – (0/0) | 87% (13/15) | 82% (23/28) | +5 |
| [PIRANHA] (`piranha_legend`) | collectible | 1% (28/2295) | 1.0 | 18% (5/28) | 36% (4/11) | 100% (5/5) | 68% (19/28) | +32 |
| [TUNA] (`tuna_legend`) | collectible | 1% (28/2295) | 1.0 | 32% (9/28) | 73% (8/11) | 78% (7/9) | 68% (19/28) | +10 |
| Eagle (`eagle`) | collectible | 1% (27/2295) | 2.5 | 53% (10/19) | 50% (2/4) | 10% (1/10) | 16% (3/19) | -6 |
| [MACAQUE] (`macaque_legend`) | collectible | 1% (26/2295) | 1.0 | 4% (1/26) | 0% (0/1) | 100% (1/1) | 65% (17/26) | +35 |
| [ELEPHANT] (`elephant_legend`) | collectible | 1% (25/2295) | 1.0 | 32% (8/25) | 50% (2/4) | 75% (6/8) | 52% (13/25) | +23 |
| `food_otk_legend_honey_badger` (no card today) | gone | 1% (25/2295) | 1.0 | 52% (13/25) | – (0/0) | 77% (10/13) | 56% (14/25) | +21 |
| `food_otk_legend_octopus` (no card today) | gone | 1% (25/2295) | 1.0 | 52% (13/25) | – (0/0) | 62% (8/13) | 56% (14/25) | +6 |
| `food_otk_legend_squirrel` (no card today) | gone | 1% (25/2295) | 1.0 | 52% (13/25) | – (0/0) | 54% (7/13) | 56% (14/25) | -2 |
| Rabbit (`rabbit`) | collectible | 1% (25/2295) | 3.0 | 96% (24/25) | 100% (22/22) | 79% (19/24) | 80% (20/25) | -1 |
| Bison (`bison`) | collectible | 1% (24/2295) | 2.0 | 21% (5/24) | 31% (5/16) | 60% (3/5) | 71% (17/24) | -11 |
| [FAWN] (`deer_legend_2`) | collectible | 1% (24/2295) | 1.0 | 25% (6/24) | 75% (6/8) | 83% (5/6) | 71% (17/24) | +12 |
| `fish_legend_jellyfish` (no card today) | gone | 1% (24/2295) | 1.0 | 25% (6/24) | 0% (0/1) | 67% (4/6) | 75% (18/24) | -8 |
| `fish_legend_manta_ray` (no card today) | gone | 1% (24/2295) | 1.0 | 42% (10/24) | – (0/0) | 80% (8/10) | 75% (18/24) | +5 |
| `fish_legend_piranha` (no card today) | gone | 1% (24/2295) | 1.0 | 21% (5/24) | – (0/0) | 80% (4/5) | 75% (18/24) | +5 |
| `fish_legend_tuna` (no card today) | gone | 1% (24/2295) | 1.0 | 21% (5/24) | – (0/0) | 80% (4/5) | 75% (18/24) | +5 |
| Hammerhead (`hammerhead`) | collectible | 1% (24/2295) | 3.0 | 67% (16/24) | 65% (13/20) | 62% (10/16) | 50% (12/24) | +12 |
| [SARDINE] (`sardine_legend`) | collectible | 1% (24/2295) | 1.0 | 29% (7/24) | 50% (5/10) | 86% (6/7) | 71% (17/24) | +15 |
| Yuki (`squirrel_legend`) | collectible | 1% (23/2295) | 1.0 | 30% (7/23) | 100% (1/1) | 43% (3/7) | 30% (7/23) | +12 |
| Hercules Beetle (`hercules_beetle`) | collectible | 1% (22/2295) | 2.0 | 18% (4/22) | 33% (3/9) | 50% (2/4) | 82% (18/22) | -32 |
| `hoofed_legend_boar` (no card today) | gone | 1% (22/2295) | 1.0 | 23% (5/22) | – (0/0) | 60% (3/5) | 68% (15/22) | -8 |
| `hoofed_legend_giraffe` (no card today) | gone | 1% (22/2295) | 1.0 | 50% (11/22) | – (0/0) | 55% (6/11) | 68% (15/22) | -14 |
| `hoofed_legend_wildebeest` (no card today) | gone | 1% (22/2295) | 1.0 | 32% (7/22) | – (0/0) | 100% (7/7) | 68% (15/22) | +32 |
| `hoofed_legend_zebra` (no card today) | gone | 1% (22/2295) | 1.0 | 32% (7/22) | – (0/0) | 71% (5/7) | 68% (15/22) | +3 |
| Wolverine (`wolverine`) | collectible | 1% (22/2295) | 3.0 | 23% (5/22) | 33% (2/6) | 80% (4/5) | 55% (12/22) | +25 |
| Viper (`viper`) | collectible | 1% (21/2295) | 3.0 | 52% (11/21) | – (0/0) | 64% (7/11) | 71% (15/21) | -8 |
| `dog` (no card today) | gone | 1% (18/2295) | 3.0 | 62% (10/16) | – (0/0) | 40% (4/10) | 38% (6/16) | +3 |
| Mosquito (`mosquito`) | collectible | 1% (17/2295) | 3.0 | 12% (2/17) | 0% (0/1) | 50% (1/2) | 53% (9/17) | -3 |
| Crocodile (`crocodile`) | collectible | 1% (15/2295) | 2.3 | 67% (10/15) | 75% (3/4) | 70% (7/10) | 67% (10/15) | +3 |
| Electric Eel (`electric_eel`) | collectible | 1% (15/2295) | 2.0 | 47% (7/15) | 67% (2/3) | 57% (4/7) | 60% (9/15) | -3 |
| Shark (`great_white_shark`) | collectible | 1% (15/2295) | 1.9 | 67% (10/15) | 0% (0/1) | 80% (8/10) | 67% (10/15) | +13 |
| Woodpecker (`woodpecker`) | collectible | 1% (14/2295) | 2.0 | 57% (8/14) | – (0/0) | 50% (4/8) | 43% (6/14) | +7 |
| Anaconda (`anaconda`) | collectible | 1% (12/2295) | 3.0 | 42% (5/12) | – (0/0) | 80% (4/5) | 67% (8/12) | +13 |
| [GLYPTODONT] (`cairn`) | reserve | 1% (12/2295) | 1.0 | 11% (1/9) | 0% (0/1) | 0% (0/1) | 11% (1/9) | -11 |
| `canines_legend_leopard` (no card today) | gone | 0% (11/2295) | 1.0 | 45% (5/11) | – (0/0) | 40% (2/5) | 27% (3/11) | +13 |
| `canines_legend_wolf` (no card today) | gone | 0% (11/2295) | 1.0 | 36% (4/11) | – (0/0) | 25% (1/4) | 27% (3/11) | -2 |
| `raccoon_dog` (no card today) | gone | 0% (11/2295) | 3.0 | 73% (8/11) | – (0/0) | 25% (2/8) | 27% (3/11) | -2 |
| Skunk (`skunk`) | collectible | 0% (11/2295) | 2.0 | 70% (7/10) | – (0/0) | 57% (4/7) | 60% (6/10) | -3 |
| Rue (`skunk_legend`) | collectible | 0% (11/2295) | 1.0 | 40% (4/10) | – (0/0) | 75% (3/4) | 60% (6/10) | +15 |
| Albatross (`albatross`) | collectible | 0% (10/2295) | 2.0 | 100% (10/10) | 100% (2/2) | 60% (6/10) | 60% (6/10) | +0 |
| Borealis (`borealis`) | reserve | 0% (10/2295) | 1.0 | 29% (2/7) | – (0/0) | 0% (0/2) | 0% (0/7) | +0 |
| Cuckoo (`cuckoo`) | collectible | 0% (10/2295) | 2.0 | 0% (0/10) | – (0/0) | – (0/0) | 50% (5/10) | – |
| Stag Beetle (`stag_beetle`) | collectible | 0% (10/2295) | 3.0 | 0% (0/10) | – (0/0) | – (0/0) | 30% (3/10) | – |
| Stick Insect (`stick_insect`) | collectible | 0% (10/2295) | 3.0 | 0% (0/10) | – (0/0) | – (0/0) | 30% (3/10) | – |
| Dolphin (`dolphin`) | collectible | 0% (9/2295) | 3.0 | 67% (6/9) | 100% (4/4) | 100% (6/6) | 78% (7/9) | +22 |
| `food_aggro_legend_refill` (no card today) | gone | 0% (8/2295) | 1.0 | 12% (1/8) | – (0/0) | 100% (1/1) | 50% (4/8) | +50 |
| `food_aggro_legend_repeat` (no card today) | gone | 0% (8/2295) | 1.0 | 25% (2/8) | – (0/0) | 50% (1/2) | 50% (4/8) | +0 |
| `verminus` (no card today) | gone | 0% (8/2295) | 1.0 | 57% (4/7) | – (0/0) | 50% (2/4) | 57% (4/7) | -7 |
| Dingo (`dingo`) | reserve | 0% (7/2295) | 3.0 | 80% (4/5) | – (0/0) | 75% (3/4) | 60% (3/5) | +15 |
| `giants_legend_oxpecker` (no card today) | gone | 0% (7/2295) | 1.0 | 0% (0/7) | – (0/0) | – (0/0) | 43% (3/7) | – |
| Macaw (`macaw`) | collectible | 0% (7/2295) | 1.4 | 29% (2/7) | – (0/0) | 50% (1/2) | 57% (4/7) | -7 |
| Coyote (`outrider`) | reserve | 0% (7/2295) | 2.0 | 80% (4/5) | – (0/0) | 50% (2/4) | 60% (3/5) | -10 |
| `raksha` (no card today) | gone | 0% (7/2295) | 1.0 | 20% (1/5) | – (0/0) | 100% (1/1) | 60% (3/5) | +40 |
| `aristocrats_legend_cuckoo` (no card today) | gone | 0% (6/2295) | 1.0 | 17% (1/6) | – (0/0) | 0% (0/1) | 0% (0/6) | +0 |
| `aristocrats_legend_opossum` (no card today) | gone | 0% (6/2295) | 1.0 | 0% (0/6) | – (0/0) | – (0/0) | 0% (0/6) | – |
| `aristocrats_legend_sloth` (no card today) | gone | 0% (6/2295) | 1.0 | 0% (0/6) | – (0/0) | – (0/0) | 0% (0/6) | – |
| Sea Turtle (`sea_turtle`) | collectible | 0% (6/2295) | 2.0 | 33% (2/6) | – (0/0) | 0% (0/2) | 0% (0/6) | +0 |
| `duplicator` (no card today) | gone | 0% (5/2295) | 2.0 | 20% (1/5) | – (0/0) | 0% (0/1) | 20% (1/5) | -20 |
| Vole (`vole`) | collectible | 0% (5/2295) | 2.0 | 0% (0/5) | 0% (0/2) | – (0/0) | 40% (2/5) | – |
| [JELLYFISH] (`jellyfish_legend`) | reserve | 0% (4/2295) | 1.0 | 50% (2/4) | 100% (1/1) | 50% (1/2) | 50% (2/4) | +0 |
| Octopus (`octopus`) | collectible | 0% (4/2295) | 1.0 | 25% (1/4) | – (0/0) | 100% (1/1) | 100% (4/4) | +0 |
| Naked Mole-Rat (`naked_mole_rat`) | reserve | 0% (3/2295) | 2.0 | 100% (3/3) | – (0/0) | 67% (2/3) | 67% (2/3) | +0 |
| [SLOTH] (`sloth_legend`) | collectible | 0% (3/2295) | 1.0 | 0% (0/3) | – (0/0) | – (0/0) | 33% (1/3) | – |
| Soldier Bee (`guard_bee`) | collectible | 0% (2/2295) | 3.0 | 50% (1/2) | – (0/0) | 0% (0/1) | 0% (0/2) | +0 |
| Opossum (`opossum`) | collectible | 0% (2/2295) | 2.0 | 50% (1/2) | – (0/0) | 100% (1/1) | 50% (1/2) | +50 |

The played-minus-deck gap mostly shows which games a card gets played in, not how strong it is. Hornet, Raven, Chameleon and Falcon lose 10 to 14 points when played. They sit in Bird/Rodent lists that won 93–99% of their games, so in those lists the reactive cards come out in the games that went long or went badly. Food payoffs played rarely gain the most: Tally +39 (20 plays), Marmot +29 (14), [RODENT] +28 (4), Vesper +29 (5). They reach the board in games already being won on food. Two counts are floors. Vesper's guard and the Vulture's fly-in enter with no logged action, so only their placements from hand count (Vesper 6%, Vulture 12%). And a Caterpillar that turned into a Butterfly counts as a Butterfly play in lists that also hold the Butterfly.

## Cards people put in a deck and never played

| card | status today | person-games in deck | creditable person-games | replayed games in hand |
|---|---|---|---|---|
| `handlock_legend_butterfly` (no card today) | gone | 38 | 37 | 0 |
| Cuckoo (`cuckoo`) | collectible | 10 | 10 | 0 |
| Stag Beetle (`stag_beetle`) | collectible | 10 | 10 | 0 |
| Stick Insect (`stick_insect`) | collectible | 10 | 10 | 0 |
| `giants_legend_oxpecker` (no card today) | gone | 7 | 7 | 0 |
| `aristocrats_legend_opossum` (no card today) | gone | 6 | 6 | 0 |
| `aristocrats_legend_sloth` (no card today) | gone | 6 | 6 | 0 |
| Vole (`vole`) | collectible | 5 | 5 | 2 |
| [SLOTH] (`sloth_legend`) | collectible | 3 | 3 | 0 |

Few cards were held and never placed, and each sits in one or two lists. The retired Handlock legendary Butterfly was in 38 person-games, nearly all one Primate/Bird list. Cuckoo was in the shipped Egg Control list, played 10 times. Stag Beetle and Stick Insect sat in one list for 10 games. Vole (5 games) and [SLOTH] (3) were tried once or twice. These cards never reached the board in people's hands, so the record says nothing about them in play.

## Cards held at least 20 times and played from under a quarter of those hands

| card | played when in hand | person-games in deck |
|---|---|---|
| [RODENT] (`rodent_legend`) | 13% (3/23) | 86 |
| Marmot (`marmot`) | 23% (8/35) | 61 |

Two food payoffs are drawn and then held. [RODENT] ("Roar: gain as much food as you gained this turn") reached the hand in 23 replayed games and was played in 3. Marmot (+1 strength for each 10 food) reached the hand in 35 and was played in 8. Each pays only late in a food game, and the game usually ends before that turn comes. One collectible card, the Pigeon, is in no person's list: it is new since 2026-10-28.

## Collectible cards today in no person's deck (1)

Pigeon

## Decks people built (135 distinct lists over 2295 person-games)

| games played with the list | lists | person-games |
|---|---|---|
| 20+ | 33 | 1668 |
| 5–19 | 55 | 518 |
| 2–4 | 35 | 97 |
| 1 game | 12 | 12 |

People build a list and then keep playing it. 135 distinct lists exist, but the 33 played 20 or more times carry 73% of person-games (1,668 of 2,295). Only 12 lists were played once.

The 25 most played lists:

| games | person win rate | deck name | tags | a shipped bot list | dates | most copies |
|---|---|---|---|---|---|---|
| 293 | 54% (158/293) | custom_55d05758c6 | Cat | yes | 20260930–20261016 | 3×Alley Cat, 3×Caracal, 3×Cougar, 3×Lion, 3×Lynx, 3×Tiger … |
| 252 | 93% (234/252) | custom_9d84ea7605 | Bird/Rodent | no | 20261001–20261004 | 3×Bird Egg, 3×Black Bear, 3×Falcon, 3×Mouse, 3×Owl, 3×Raven … |
| 132 | 99% (131/132) | custom_b2e0f9bf9a | Rodent/Bird | no | 20261004–20261013 | 3×Bird Egg, 3×Lemming, 3×Mouse, 3×Owl, 2×Black Bear, 2×Chameleon … |
| 92 | 60% (55/92) | custom_69b142f541 | Bird/Egg | no | 20261001–20261002 | 3×Bat, 3×Bird Egg, 3×Black Bear, 3×Owl, 3×Rat, 3×Raven … |
| 56 | 62% (35/56) | custom_58dd722dce | Bird/Snake | yes | 20260930–20261001 | 3×Bird Egg, 3×Owl, 3×Raven, 3×Snake Egg, 2×Black Mamba, 2×Cottonmouth … |
| 56 | 50% (28/56) | custom_f5db7f0945 | Rodent | no | 20261029–20261104 | 3×Chipmunk, 3×Gopher, 3×Hamster, 3×Mara, 3×Marmot, 3×Squirrel … |
| 47 | 89% (42/47) | custom_de3e4370bf | Cat/Bird | no | 20261004–20261004 | 3×Black Bear, 3×Caracal, 3×Lion, 3×Lynx, 3×Owl, 2×Alley Cat … |
| 47 | 51% (24/47) | custom_74e88ec3d7 | Canine/Cat | yes | 20261014–20261015 | 3×African Wild Dog, 3×Badger, 3×Bush Dog, 3×Coyote, 3×Street Dog, 3×Wolf … |
| 44 | 95% (42/44) | custom_6ee46027c5 | Cat/Bird | no | 20261004–20261004 | 3×Black Bear, 3×Caracal, 3×Lion, 3×Lynx, 3×Owl, 2×Black Panther … |
| 42 | 60% (25/42) | custom_52b9388277 | Bird/Snake | no | 20261002–20261011 | 3×Bird Egg, 3×Black Bear, 3×Python, 3×Rattlesnake, 3×Raven, 3×Snake Egg … |
| 40 | 52% (21/40) | custom_7a0c4722f8 | Beetle/Bird | no | 20261027–20261030 | 3×Blue Whale, 3×Dung Beetle, 3×Elephant, 3×Giraffe, 3×Krill, 3×Oxpecker … |
| 37 | 78% (29/37) | custom_6892f63f99 | Primate/Bird | yes | 20261010–20261012 | 3×Baboon, 3×Caterpillar, 3×Chimpanzee, 3×Gorilla, 3×Grizzly Bear, 3×Stork … |
| 36 | 72% (26/36) | custom_29e5c0e686 | Cat | no | 20261022–20261024 | 3×Alley Cat, 3×Bobcat, 3×Cheetah, 3×Lion, 3×Serval, 3×Tiger … |
| 36 | 69% (25/36) | custom_21955f693e | Colony/Queen | no | 20261024–20261026 | 3×Soldier Wasp, 3×Nurse Bee, 3×Queen Bee, 3×Soldier Ant, 3×Worker Bee, 3×Worker Wasp … |
| 28 | 82% (23/28) | custom_a514fc7745 | Colony/Worker | yes | 20261001–20261010 | 3×Soldier Wasp, 3×Queen Bee, 3×Soldier Ant, 3×Worker Ant, 3×Worker Bee, 3×Worker Wasp … |
| 28 | 57% (16/28) | custom_77d00a11de | Bird/Arachnid | no | 20261015–20261019 | 3×City Spider, 3×Cockroach, 3×Piranha, 3×Python, 3×Toad, 3×Vulture … |
| 26 | 35% (9/26) | custom_83ec9b628d | Hoofed | no | 20261029–20261029 | 3×Deer, 3×Gazelle, 3×Giraffe, 3×Warthog, 3×Wildebeest, 3×Zebra … |
| 25 | 64% (16/25) | custom_fb1d1c4070 | Bird/Egg | no | 20261001–20261001 | 3×Bat, 3×Bird Egg, 3×Black Bear, 3×Owl, 3×Rat, 3×Raven … |
| 25 | 56% (14/25) | custom_f1e4288c3c | Rodent/Bear | yes | 20261009–20261010 | 3×Black Bear, 3×Dart Frog, 3×Hedgehog, 3×Jellyfish, 3×Owl, 3×Tortoise … |
| 25 | 96% (24/25) | custom_eadc53bd16 | Cat/Bear | no | 20261024–20261025 | 3×Alley Cat, 3×Black Bear, 3×Bobcat, 3×Lion, 3×Serval, 3×Tiger … |
| 24 | 75% (18/24) | custom_fca34ab289 | Fish | yes | 20261010–20261011 | 6×Mahi-mahi, 3×Cod, 3×Sardine, 3×Sunfish, 3×Tuna, 2×Barracuda … |
| 24 | 88% (21/24) | custom_f535156ae6 | Cat | yes | 20261010–20261018 | 3×Alley Cat, 3×Bobcat, 3×Caracal, 3×Lion, 3×Lynx, 3×Tiger … |
| 24 | 58% (14/24) | custom_c008e5a677 | Cat | no | 20261030–20261104 | 3×Alley Cat, 3×Bobcat, 3×Caracal, 3×Lion, 3×Serval, 3×Tiger … |
| 24 | 62% (15/24) | custom_233469decb | Colony/Worker | no | 20261030–20261104 | 3×Soldier Wasp, 3×Nurse Bee, 3×Soldier Ant, 3×Worker Ant, 3×Worker Bee, 3×Worker Wasp … |
| 24 | 71% (17/24) | custom_3efd4f4c98 | Fish | no | 20261030–20261104 | 3×Barracuda, 3×Cod, 3×Mahi-mahi, 3×Sardine, 3×Sunfish, 3×Tuna … |

The single most played list is a Cats list identical to a shipped bot list (293 games, 54%). The lists people built themselves and won most with are Bird/Rodent lists from 1–13 October: 93% over 252 games and 99% over 132. Both run three each of Owl, Bird Egg and Mouse with Black Bear, and the first adds Raven and Falcon. The lists played since 29 October (Rodent, Hoofed, Colony, Fish, Cat) win 35–71%, on smaller counts.

## People's decks against the bots' decks

People: 1591 person-games on a list of their own (704 more on a shipped bot list are left out). Bots: 1751 bot seats on a shipped deck (47 distinct lists; the 464 bot seats on a player's saved deck, from the gauntlet, are left out). Copies per deck, averaged over games.

|  | people, by game | people, each list once (103) | bots, by game |
|---|---|---|---|
| mean printed strength | 3.30 | 3.58 | 4.36 |
| common copies per deck | 18.0 | 17.6 | 17.2 |
| legendary copies per deck | 4.0 | 4.0 | 3.5 |
| rare copies per deck | 8.0 | 8.4 | 8.6 |
| strength 0 copies per deck | 2.1 | 2.0 | 0.5 |
| strength 1 copies per deck | 3.6 | 3.4 | 1.3 |
| strength 2 copies per deck | 7.1 | 6.0 | 4.2 |
| strength 3 copies per deck | 4.2 | 4.4 | 5.7 |
| strength 4 copies per deck | 4.8 | 3.7 | 4.2 |
| strength 5 copies per deck | 3.8 | 4.6 | 4.6 |
| strength 6 copies per deck | 1.7 | 2.1 | 3.5 |
| strength 7 copies per deck | 1.5 | 1.6 | 3.0 |
| strength 8 copies per deck | 0.7 | 1.3 | 1.5 |
| strength 9 copies per deck | 0.2 | 0.4 | 0.5 |
| strength 10 copies per deck | 0.0 | 0.1 | 0.2 |

People's own lists are smaller than the shipped bot decks. Mean printed strength is 3.3 by game (3.6 counting each list once) against 4.4. Per deck, people hold about twice as many 0–2 strength cards (12.8 by game, 11.4 by list, against 6.0) and about half as many 6+ cards (4.1 by game, 5.5 by list, against 8.7). The low cards people take are the ones that do something on landing or later (Owl's Scout, Bird Egg, Mouse, Hornet). The rarity split hardly differs.

The 30 cards whose copies per deck differ most between people and bots (by game):

| card | people, by game | people, each list once | bots, by game | people − bots |
|---|---|---|---|---|
| Owl (`owl`) | 1.51 | 0.93 | 0.19 | +1.32 |
| Bird Egg (`bird_egg`) | 1.33 | 0.73 | 0.08 | +1.24 |
| Raven (`raven`) | 1.32 | 0.74 | 0.08 | +1.24 |
| Black Bear (`black_bear`) | 1.63 | 1.40 | 0.40 | +1.22 |
| Hornet (`hornet`) | 1.16 | 0.76 | 0.33 | +0.83 |
| Lion (`lion`) | 0.55 | 0.64 | 1.34 | -0.79 |
| Mouse (`mouse`) | 1.02 | 0.52 | 0.47 | +0.56 |
| Tiger (`tiger`) | 0.28 | 0.34 | 0.76 | -0.48 |
| Cougar (`cougar`) | 0.02 | 0.03 | 0.47 | -0.44 |
| Falcon (`falcon`) | 0.87 | 0.40 | 0.43 | +0.44 |
| Chameleon (`chameleon`) | 0.69 | 0.39 | 0.30 | +0.40 |
| Aurum (`goose_legend`) | 0.42 | 0.21 | 0.03 | +0.39 |
| Muskrat (`muskrat`) | 0.07 | 0.25 | 0.44 | -0.36 |
| Jerboa (`jerboa`) | 0.62 | 0.23 | 0.26 | +0.36 |
| Wolf (`wolf`) | 0.04 | 0.06 | 0.39 | -0.35 |
| Chinchilla (`chinchilla`) | 0.62 | 0.21 | 0.28 | +0.33 |
| Groundhog (`groundhog`) | 0.12 | 0.14 | 0.44 | -0.32 |
| `dog` (no card today) | 0.00 | 0.00 | 0.32 | -0.32 |
| African Wild Dog (`african_wild_dog`) | 0.03 | 0.05 | 0.35 | -0.32 |
| Sloth (`sloth`) | 0.04 | 0.12 | 0.35 | -0.31 |
| Fox (`fox`) | 0.04 | 0.06 | 0.33 | -0.29 |
| Skunk (`skunk`) | 0.00 | 0.00 | 0.29 | -0.29 |
| Dingo (`dingo`) | 0.00 | 0.00 | 0.28 | -0.28 |
| Jaguar (`jaguar`) | 0.13 | 0.13 | 0.41 | -0.28 |
| Cape Buffalo (`cape_buffalo`) | 0.07 | 0.06 | 0.35 | -0.28 |
| Hedgehog (`hedgehog`) | 0.04 | 0.20 | 0.32 | -0.28 |
| Cheetah (`cheetah`) | 0.15 | 0.14 | 0.43 | -0.27 |
| Grizzly Bear (`grizzly_bear`) | 0.05 | 0.17 | 0.33 | -0.27 |
| Chimpanzee (`chimpanzee`) | 0.08 | 0.14 | 0.34 | -0.27 |
| Squirrel (`squirrel`) | 0.18 | 0.15 | 0.44 | -0.26 |

The gap is mostly one deck idea: Owl, Bird Egg, Raven, Black Bear, Hornet, Mouse, Falcon and Chameleon run 0.4–1.3 more copies per person deck than per bot deck. Counting each list once roughly halves most of these gaps (Raven 1.32 to 0.74 copies), so part of it is a few lists played hundreds of times. The cards people leave out compared with the bots are the Canines (Wolf, African Wild Dog, Fox, Dingo), the big Cats (Lion, Tiger, Cougar, Cheetah, Jaguar) and mid-sized bodies (Cape Buffalo, Grizzly Bear, Elephant, Sloth).

Tags, copies per deck (the 15 that differ most by game):

| tag | people, by game | people, each list once | bots, by game |
|---|---|---|---|
| Bird | 5.8 | 4.6 | 1.7 |
| Cat | 5.0 | 5.0 | 7.5 |
| Canine | 0.4 | 0.6 | 2.5 |
| Egg | 1.5 | 1.1 | 0.2 |
| Bear | 1.7 | 1.7 | 1.1 |
| Fish | 0.7 | 0.8 | 1.3 |
| Snake | 0.9 | 1.3 | 0.4 |
| Worker | 0.3 | 0.2 | 0.7 |
| Colony | 2.3 | 1.5 | 2.6 |
| Hoofed | 1.2 | 1.3 | 1.0 |
| Rodent | 5.2 | 4.3 | 5.5 |
| Soldier | 0.2 | 0.1 | 0.5 |
| Queen | 0.3 | 0.2 | 0.6 |
| Nurse | 0.1 | 0.1 | 0.3 |
| Arachnid | 0.2 | 0.2 | 0.0 |

By tag, people play Birds at more than three times the bots' rate (5.8 against 1.7 copies) and Canines at a sixth (0.4 against 2.5). Cats stay common in both but fall from 7.5 to 5.0.

## How a person's game ends

Turn: the person's own turns begun when the game ended. Every person-game.

| ended by | person | games | median turn | middle half | range |
|---|---|---|---|---|---|
| hq_capture | won | 47% (1150/2461) | 5.0 | 3–7 | 2–17 |
| food | won | 19% (479/2461) | 7 | 5–9 | 3–21 |
| hq_capture | lost | 15% (363/2461) | 5 | 4–7 | 1–17 |
| food | lost | 15% (358/2461) | 7.0 | 5–8 | 2–15 |
| concede | lost | 4% (93/2461) | 5 | 2–6 | 0–18 |
| concede | won | 0% (6/2461) | 8.5 | 7–13 | 7–16 |
| passes | won | 0% (4/2461) | 3.5 | 1–8 | 1–9 |
| passes | lost | 0% (4/2461) | 3.5 | 1–9 | 1–10 |
| exhaustion | won | 0% (1/2461) | 15 | 15–15 | 15–15 |
| timeout | lost | 0% (1/2461) | 3 | 3–3 | 3–3 |
| timeout | won | 0% (1/2461) | 4 | 4–4 | 4–4 |
| exhaustion | lost | 0% (1/2461) | 8 | 8–8 | 8–8 |

A person who wins usually takes the den (1,150 of 1,629 wins, median turn 5) rather than reaching 100 food (479, median turn 7). Losses split evenly between the two (363 den, 358 food). The den race is decided about two turns earlier than the food race.

By turn (person's own turns), every person-game:

| turn | games | took den | lost den | won on food | lost on food | conceded | other |
|---|---|---|---|---|---|---|---|
| 0 | 7 | 0 | 0 | 0 | 0 | 7 | 0 |
| 1 | 18 | 0 | 3 | 0 | 0 | 13 | 2 |
| 2 | 164 | 135 | 22 | 0 | 1 | 4 | 2 |
| 3 | 313 | 243 | 54 | 2 | 8 | 5 | 1 |
| 4 | 354 | 185 | 75 | 39 | 44 | 10 | 1 |
| 5 | 370 | 147 | 58 | 81 | 59 | 23 | 2 |
| 6 | 332 | 106 | 59 | 100 | 59 | 8 | 0 |
| 7 | 287 | 112 | 37 | 67 | 63 | 6 | 2 |
| 8 | 218 | 78 | 20 | 65 | 44 | 9 | 2 |
| 9 | 160 | 56 | 17 | 53 | 30 | 2 | 2 |
| 10 | 97 | 40 | 7 | 23 | 24 | 2 | 1 |
| 11–13 | 114 | 42 | 8 | 38 | 23 | 2 | 1 |
| 14+ | 27 | 6 | 3 | 11 | 3 | 2 | 2 |

Den captures peak on turn 3 (243 taken), and a person takes the den in most games that end by turn 4. Food wins start on turn 4 and peak on turn 6. Only 141 of 2,461 games (6%) go past turn 10. Endings on turn 0 or 1 are nearly all concessions.

By opponent:

| opponent | person-games | person won | took den | lost den | won on food | lost on food | mean turn |
|---|---|---|---|---|---|---|---|
| expert | 1916 | 67% (1282/1916) | 45% (868/1916) | 15% (288/1916) | 22% (413/1916) | 14% (274/1916) | 5.9 |
| normal | 420 | 71% (297/420) | 59% (247/420) | 10% (44/420) | 12% (50/420) | 16% (67/420) | 5.4 |
| human | 80 | 50% (40/80) | 26% (21/80) | 26% (21/80) | 10% (8/80) | 10% (8/80) | 7.0 |
| easy | 45 | 49% (22/45) | 31% (14/45) | 22% (10/45) | 18% (8/45) | 20% (9/45) | 6.0 |

Against the Expert, people win 67% (1,282 of 1,916) and take its den in 45% of games, while losing their own in 15%. So the Expert loses mostly by its den. Between two people (80 person-games), den and food endings split evenly. The 45 games against Easy, at 49%, are too few to read.

## Concessions

How often a person concedes, by opponent:

| opponent | person conceded |
|---|---|
| easy | 9% (4/45) |
| expert | 4% (72/1916) |
| human | 8% (6/80) |
| normal | 3% (11/420) |

People concede rarely: 4% against the Expert (72 of 1,916) and 3–9% elsewhere, on small counts. A closed tab leaves no log line, so walk-outs are not counted here.

Conceded before both players had finished a turn (turn counter 0 or 1): 22% (20/93).

The turn a person conceded on (their own turns begun):

| turn | concessions |
|---|---|
| 0 | 8% (7/93) |
| 1 | 14% (13/93) |
| 2 | 4% (4/93) |
| 3 | 5% (5/93) |
| 4 | 11% (10/93) |
| 5 | 25% (23/93) |
| 6 | 9% (8/93) |
| 7 | 6% (6/93) |
| 8 | 10% (9/93) |
| 9 | 2% (2/93) |
| 10 | 2% (2/93) |
| 11–13 | 2% (2/93) |
| 14+ | 2% (2/93) |

One concession in five (20 of 93) comes before both players have finished a turn. That is a restart after the opening hand, not a lost position. The rest bunch on turns 4–5 (33 of 93). In the 25 later concessions that replay, the person was behind on food in 17 (median 27 against 35). People concede when a lost race shows, around the turn the den race usually ends.

In the 25 concessions that replay and come after both players' first turn: food behind the opponent at the concession in 68% (17/25); median food 27 against 35.

Other endings without a result for the person: {'timeout': 1}. A person who closes the tab leaves no log line at all; those games are not here.

## Turns 1 and 2: people against the Expert in the same games

851 person-vs-Expert games whose replay gets through both players' first two turns (286 replay to the end, 565 break later). Counts are actions on the player's own first and second turn; "placements" include those an effect grants (marked free). The first player's turn 1 has one action in logs that record `first_turn_actions: 1` and two in older ones.

person goes first (the Expert second); per game:

| own turn | who | games | draws | placements | row 1 | row 2 | row 3 | row 4 | row 5 | den |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | person | 396 | 0.21 (85) | 1.04 (413, 15 free) | 0.91 (359) | 0.13 (50) | 0.01 (3) | 0.00 (1) | 0.00 (0) | 0.00 (0) |
| 1 | Expert | 396 | 0.89 (352) | 1.17 (465, 42 free) | 0.78 (308) | 0.27 (107) | 0.07 (26) | 0.02 (8) | 0.04 (16) | 0.00 (0) |
| 2 | person | 396 | 0.35 (137) | 1.72 (682, 47 free) | 0.67 (264) | 0.67 (266) | 0.18 (71) | 0.08 (32) | 0.11 (44) | 0.01 (5) |
| 2 | Expert | 396 | 0.43 (170) | 1.66 (657, 62 free) | 0.46 (182) | 0.61 (241) | 0.30 (120) | 0.17 (68) | 0.10 (39) | 0.02 (7) |

Going first, people spend turn 1 placing, almost always in row 1 in front of their own den (0.91 of 1.04 placements). They draw in about one game in five (0.21). The Expert, going second with two actions, draws in most games (0.89) and places once (1.17, more of them forward in rows 2–5). On turn 2, the Expert reaches further: 0.57 placements in rows 3–5 per game against the person's 0.37.

person goes second (the Expert first); per game:

| own turn | who | games | draws | placements | row 1 | row 2 | row 3 | row 4 | row 5 | den |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | person | 455 | 0.20 (91) | 1.85 (840, 25 free) | 1.29 (587) | 0.42 (191) | 0.04 (18) | 0.03 (12) | 0.07 (32) | 0.00 (0) |
| 1 | Expert | 455 | 0.82 (375) | 0.55 (250, 12 free) | 0.49 (223) | 0.03 (15) | 0.02 (10) | 0.00 (2) | 0.00 (0) | 0.00 (0) |
| 2 | person | 455 | 0.34 (153) | 1.74 (791, 49 free) | 0.41 (187) | 0.67 (304) | 0.31 (143) | 0.19 (88) | 0.14 (62) | 0.02 (7) |
| 2 | Expert | 455 | 0.71 (321) | 1.40 (639, 46 free) | 0.55 (250) | 0.51 (234) | 0.16 (72) | 0.08 (36) | 0.10 (45) | 0.00 (2) |

Going second, people use both turn-1 actions to place (1.85 per game) and draw in one game in five (0.20). The Expert, going first, draws in most games (0.82) and places about one game in two (0.55). On turn 2, people reach further than the Expert: 0.64 placements in rows 3–5 against 0.34. Whoever goes second reaches further on turn 2. The steady difference is the turn-1 draw: the Expert draws on turn 1 about four times as often as people do.

The cards most placed on a person's turn 1, against the Expert's turn 1 in the same games:

| person's turn 1 | times | Expert's turn 1 | times |
|---|---|---|---|
| Black Bear (`black_bear`) | 191 | Sardine (`sardine`) | 49 |
| Owl (`owl`) | 56 | Alley Cat (`alley_cat`) | 41 |
| Queen Adira (`lion_legend_4`) | 36 | Chipmunk (`chipmunk`) | 36 |
| Sardine (`sardine`) | 35 | Queen Ant (`queen_ant`) | 33 |
| Aurum (`goose_legend`) | 33 | Lion (`lion`) | 29 |
| Groundhog (`groundhog`) | 33 | Oxpecker (`oxpecker`) | 26 |
| Mouse (`mouse`) | 32 | Black Bear (`black_bear`) | 22 |
| Worker Wasp (`worker_wasp`) | 30 | Mole (`mole`) | 19 |
| Okapi (`okapi`) | 27 | Sunfish (`sunfish`) | 17 |
| Princess Lea (`lion_legend_2`) | 25 | Beaver (`beaver`) | 16 |
| Prince Leo (`lion_legend`) | 25 | Caracal (`caracal`) | 15 |
| Snow Leopard (`snow_leopard`) | 24 | Queen Melissia (`bee_legend`) | 13 |

People's most common opener is the Black Bear (191 turn-1 placements; "Roar: in 2 turns, draw 2 cards"), well ahead of Owl (56) and Queen Adira (36). People get their cards from the Bear's delayed draw where the Expert takes the draw action. The Expert's openers spread over many decks' cheap bodies (Sardine, Alley Cat, Chipmunk, Queen Ant).

## A person's den fell within five turns, by opponent deck (replayed games)

Opponent deck read by its two most common tags (copies), today's cards.

| opponent deck | pilot | deck names (games) | person-games | den fell within 5 turns | den fell at all |
|---|---|---|---|---|---|
| Cat/Hoofed | expert | optimizer_1 (1) | 1 | 100% (1/1) | 100% (1/1) |
| Cat/Rodent | expert | custom_43e1171d61 (1), custom_caaf15135c (1) | 2 | 50% (1/2) | 50% (1/2) |
| Bird/Egg | expert | martin_314569a27d (2) | 2 | 50% (1/2) | 50% (1/2) |
| Cat/Bear | expert | custom_9bd1910a1c (30), bot_optimized (5), martin_8973dbe0bf (2) | 37 | 41% (15/37) | 46% (17/37) |
| Colony/Queen | expert | martin_3bb056c51f (2), custom_66aad48092 (1) | 3 | 33% (1/3) | 33% (1/3) |
| Fish | expert | custom_3efd4f4c98 (12), fish (7), custom_fb1718883a (3) | 23 | 30% (7/23) | 30% (7/23) |
| Rodent/Cat | expert | custom_ed1ae30ccf (28), custom_3a364fed40 (5) | 33 | 30% (10/33) | 33% (11/33) |
| Canine/Cat | expert | custom_ba0b0e0c03 (13), custom_6fdc64aea5 (3), canines (1) | 17 | 29% (5/17) | 29% (5/17) |
| Hoofed | expert | custom_766dd8aa87 (12) | 12 | 25% (3/12) | 33% (4/12) |
| Primate/Bird | expert | custom_c7da58ce92 (12), martin_77238db25c (2) | 14 | 14% (2/14) | 21% (3/14) |
| Cat | expert | custom_c008e5a677 (23), lions30 (10), cats_midrange (1) | 36 | 11% (4/36) | 17% (6/36) |
| Colony/Worker | expert | custom_233469decb (18), colony (1) | 19 | 11% (2/19) | 11% (2/19) |
| Arachnid/Bird | expert | custom_4bb54fbad2 (8), custom_80e4cf4987 (4) | 12 | 8% (1/12) | 8% (1/12) |
| Beetle/Bird | expert | custom_17b2e7212e (12), custom_7a0c4722f8 (1) | 13 | 8% (1/13) | 8% (1/13) |
| Rodent | expert | custom_f5db7f0945 (14), food_otk (4), food_aggro (1) | 19 | 5% (1/19) | 5% (1/19) |
| Egg/Snake | expert | custom_13c21d2fb9 (10) | 10 | 0% (0/10) | 10% (1/10) |
| Rodent/Primate | expert | food_aggro (7) | 7 | 0% (0/7) | 0% (0/7) |
| Rodent/Bird | expert | den_rush (3), food_aggro (2) | 5 | 0% (0/5) | 20% (1/5) |
| Bird/Beetle | expert | martin_34e9ec4b5f (3), giants (1) | 4 | 0% (0/4) | 0% (0/4) |
| Bird/Bear | expert | martin_805478ab5f (4) | 4 | 0% (0/4) | 25% (1/4) |
| Cat | normal | cats_midrange (3) | 3 | 0% (0/3) | 0% (0/3) |
| Fish/Hoofed | expert | token (3) | 3 | 0% (0/3) | 33% (1/3) |
| Snake/Cat | expert | removal (3) | 3 | 0% (0/3) | 0% (0/3) |
| Bird/Snake | expert | egg_control (2) | 2 | 0% (0/2) | 0% (0/2) |
| Bird/Snake | normal | egg_control (2) | 2 | 0% (0/2) | 0% (0/2) |
| Cat | easy | cats_midrange (2) | 2 | 0% (0/2) | 0% (0/2) |
| a person's deck: Cat | human | custom_55d05758c6 (2) | 2 | 0% (0/2) | 0% (0/2) |
| Hoofed/Fish | expert | optimizer_4 (2) | 2 | 0% (0/2) | 0% (0/2) |
| Rodent/Bird | easy | aggro_hq_rush (1) | 1 | 0% (0/1) | 0% (0/1) |
| Canine/Primate | normal | canine_buff_tempo (1) | 1 | 0% (0/1) | 0% (0/1) |
| Bear/Bird | normal | ramp (1) | 1 | 0% (0/1) | 0% (0/1) |
| a person's deck: Bird/Snake | human | custom_52b9388277 (1) | 1 | 0% (0/1) | 0% (0/1) |
| a person's deck: Cat/Bird | human | custom_5e5755b2f9 (1) | 1 | 0% (0/1) | 0% (0/1) |
| Cat/Bear | normal | bot_optimized (1) | 1 | 0% (0/1) | 0% (0/1) |
| Bear/Rodent | expert | martin_ce499c15b8 (1) | 1 | 0% (0/1) | 0% (0/1) |
| Rodent/Colony | expert | martin_ed25f719a2 (1) | 1 | 0% (0/1) | 100% (1/1) |
| Fish/Colony | expert | custom_9521e7ffd0 (1) | 1 | 0% (0/1) | 0% (0/1) |
| all |  |  | 301 | 18% (55/301) | 22% (67/301) |

On today's cards (301 person-games, almost all from 29 October on), a person's den fell within five turns in 18% of games (55), most of all their den losses (67). The early losses gather on a few opponent decks: Cat/Bear 15 of 37 (mostly one saved list, `custom_9bd1910a1c`), Rodent/Cat 10 of 33, Fish 7 of 23, Canine/Cat 5 of 17, Hoofed 3 of 12. Against Colony/Worker, Rodent, Beetle/Bird and Arachnid/Bird, the den fell within five turns about once in 10 to 20 games. Most rows hold fewer than 40 games.

# Card effect and number inventory — 2026-07-15

## What this is for

This is a map, not a rules change. For every kind of live card behavior, it shows where the
game carries it out and where the important numbers come from. It makes a future wording or
balance change easier to check: update the card, follow its row, and make sure the stated
number and the game behavior still agree.

The inventory covers the current `cards.json` pool. Ordinary strength and food costs always
come from the card's own data. The tables below cover added card text and special behavior.

## Reading the “number source” column

- **Card data** — printed strength or food cost belongs to that card's record.
- **Shared setting** — a named value in `engine/config.py`; safe to vary for a balance run.
- **Written in behavior** — the number is embedded in the game behavior today. It is a
  follow-up candidate for the consistency work, not an instruction to change it blindly.
- **Derived / no fixed number** — the result depends on the board, hand, or ordinary rules.

## Universal rules and keywords

| Card text or category | Where the game handles it | Number source |
| --- | --- | --- |
| Every printed strength | `data/cards.json` → `engine/strength.py:46-109` | Card data |
| “Costs N food” (Borealis, Aquila, Bulwark, Elephant) | `cards.json.food_cost` → `effects.py:99-111, 462-463` | Card data; text/cost guard exists |
| Flight | `statics.py:52-54`; placement generation | No fixed number |
| Apex Predator | `statics.py:23-50`; `effects.py:123-157` | No fixed number |
| Fragile, Immovable, Stealth | `statics.py:84-119`; removal/choice helpers | No fixed number |
| “Cannot be covered” / Chameleon / Snow Leopard | `statics.py:23-50` | No fixed number |
| Cougar and Outrider placement reach | `statics.py:57-81` | No fixed number |
| Armadillo sheltering adjacent allies | `statics.py:95-119` | No fixed number |

## Strength that changes during play

| Cards | Where the game handles it | Number source |
| --- | --- | --- |
| Goliath | `strength.py:38-49` | Derived: remove-pile size |
| Rattlesnake | `effects.py:1006-1019` | Written in behavior: +1 per shuffle |
| Lobo, Verminus, Vesper, Guard Hornet, Raksha | `strength.py:56-89` | Shared settings: `anthem_*`, `guard_hornet_*`, `raksha_anthem` |
| Dhole, Clarion, Red Wolf, Dingo, Bush Dog, Shuck | `effects.py:892-965` | Shared settings: `*_grant` |
| Coyote | `effects.py:887-890` | Shared setting for strength threshold; draw-one is written in behavior |

## Food, delayed food, and food conditions

| Cards | Where the game handles it | Number source |
| --- | --- | --- |
| Eon, Egg Eater, Jackal | `effects.py:996-1029` | Shared settings: `eon_food`, `egg_eater_food`, `jackal_food` |
| Queen Honoria, Queen Marabunta | `effects.py:177-199, 1479-1482` | Shared settings: `queen_honoria_per_play`, `queen_marabunta_per_colony` |
| Worker Ant, Worker Bee, Worker Wasp, Methuselah | `effects.py:1455-1489` | Shared settings: `worker_*`, `methuselah_food` |
| Flying Squirrel, Squirrel, Chipmunk, Hedgehog, Gopher, Groundhog | `effects.py:1466-1476, 1588-1616` | Shared settings; food wording is guarded |
| Rat King | `effects.py:1582-1586` | `rat_king_per_rodent` is shared; draw-one is written in behavior |
| Sloth | `effects.py:1154-1162` | Shared settings: `sloth_delay`, `sloth_food` |
| Scrooge | `effects.py:1573-1577` | Shared setting: `scrooge_gain_multiplier`; amount is derived from food gained this turn |
| Hamster and Muskrat | `effects.py:1598-1607` | Shared setting: `fed_threshold`; Hamster draw-two is shared (`hamster_draw`) |
| Falstaff | `effects.py:308-324` | Shared setting: `falstaff_food_rider` |
| Oxpecker | `effects.py:1636-1640` | Written in behavior: 1 food; card data supplies the starting deck strengths |

## Removal, return, and placement effects

| Cards | Where the game handles it | Number source |
| --- | --- | --- |
| King Theron, Queen Adira | `effects.py:161-174, 1446-1453` | No fixed number; Queen Adira draw-one is written in behavior |
| Jaguar, Serval, Stoop, Rhinoceros, Hippopotamus | `effects.py:1216-1259` | Shared settings: removal thresholds |
| Gray Wolf, Hyena, Soldier Ant, Bulwark, Pestis | `effects.py:878-884, 928-934, 1231-1250, 1361-1381` | Derived or no fixed number; Soldier Ant uses `colony_synergy_threshold` |
| Rat and Hornet | `effects.py:1264-1311` | No fixed number |
| Skunk | `effects.py:1408-1424` | Written in behavior: lock lasts two turns; see the instance-identity debt item |
| Sirocco and Gale | `effects.py:1384-1405` | No fixed number |
| Lemming | `effects.py:1427-1443` | No fixed number |
| African Wild Dog and Alpha | `effects.py:909-925` | Shared settings: `awd_pups`, `alpha_pups` |
| Jerboa, House Cat, Dog, Queen Bee, Termite Queen, Prince Leo, Princess Lea | `effects.py:1103-1147` | No fixed number; ordinary “one more” behavior is represented by a single extra-placement step |

## Drawing, looking, and other card-specific behavior

| Cards | Where the game handles it | Number source |
| --- | --- | --- |
| Owl | `effects.py:610-630` | Written in behavior: look at 3, draw 1 |
| Raven | `effects.py:583-607` | Written in behavior: draw 3, return 2 |
| Mouse and Fathom | `effects.py:1062-1067, 367-411` | Written in behavior: draw 1 matching card |
| Bird Egg and Snake Egg | `effects.py:1070-1077, 499-534` | Shared settings: `egg_hatch_delay`, `egg_hatch_draw` |
| Black Bear and Grizzly Bear | `effects.py:1553-1570` | Shared settings: delays and Black Bear draw count |
| Black Swan | `effects.py:1032-1044` | No printed fixed number; once-per-turn rule is behavior |
| Ember | `effects.py:1055-1059` | No fixed number |
| Lynx, Caracal, Cheetah, Falcon, Bat, Aurum, Fox, Mock Scout | `effects.py:943-945, 1494-1509, 1145-1152` | Written in behavior: draw 1 |
| Impala, Mock Draw2, Nurse Bee, Nurse Bumblebee | `effects.py:1090-1092, 1512-1543` | Written in behavior: draw 2 |
| Chinchilla | `effects.py:1592-1596` | Shared settings: `chinchilla_draw`, `chinchilla_bonus_actions` |
| Andean Condor | `effects.py:1626-1633` | Derived: comparison of revealed card strengths |
| Mock Saboteur and Mock Removal | `effects.py:1517-1532` | No fixed number |

## Live special text that is handled outside the effect registry

The following live cards have text but do not have their own row in `EFFECTS`. That is
intentional: their behavior is generic keyword, strength, placement, or event machinery
listed above.

`anaconda`, `aquila`, `armadillo`, `black_panther`, `borealis`, `chameleon`, `cougar`,
`eagle`, `elephant`, `falstaff`, `goliath`, `guard_hornet`, `king_theron`, `lobo`,
`mock_apex_5`, `mock_apex_6`, `mock_flyer_7`, `mock_immovable_6`, `outrider`,
`polar_bear`, `porcupine`, `raksha`, `rattlesnake`, `snow_leopard`, `tiger`, `verminus`,
and `vesper`.

## Shelved-card behavior deliberately kept in the engine

`black_widow`, `carmilla`, `gazelle`, `impala`, `opossum`, `pufferfish`, and `vulture`
remain in `EFFECTS` but are not current card records. Their cards are documented as shelved
or dormant in `docs/cards/shelved-cards.md:42-52` and
`docs/cards/card-candidates.md:6-9`. This is deliberate retention for possible return, not
a live card/data mismatch. It does mean the effect registry alone is not a list of the
current pool.

## What this inventory says to do next

1. Before changing a printed number, find its row and update the stated source together
   with card text.
2. Treat every “written in behavior” value as a decision point for the open consistency
   work: move it to a named shared setting or card data, then add a guard.
3. When reintroducing a shelved card, restore its data and text alongside its retained
   behavior, then add it to the relevant consistency checks.

## How it was checked

This was read-only. The current card records were compared to the `EFFECTS` registry,
handler locations, `Config` use sites, `statics.py`, and `strength.py`. No game, test, or
simulation was run.

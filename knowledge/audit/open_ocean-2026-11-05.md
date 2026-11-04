# Card audit: Open Ocean (2026-11-05)

Does the rules engine do what each collectible Open Ocean card's printed text says? 26 cards, tested in
`animal_kingdom/tests/audit/test_open_ocean.py` (96 tests, written from the printed text and keywords.md/rulings.md).
No engine change was needed; one card has a text that reads two ways.

- sperm_whale: ok
- orca: ok
- tuna_legend: ok
- manta_ray_legend: ok
- swordfish: ok
- barracuda: ok
- manta_ray: ok
- remora: ok
- cod: ok
- sardine: ok
- mahi_mahi: ok
- tuna: ok
- sunfish: ok
- octopus_legend_2: ok
- jellyfish: ok
- sperm_whale_legend: two readings: A (literal) "remove the strongest adjacent enemy" names the strongest one, and if it has Armor it can't be removed, so nothing happens; B (the engine) the strongest adjacent enemy that can be removed, so a weaker enemy beside an Armor one is removed. B matches the Tarantula and City Spider rulings ("Armor excluded" before picking). Test `test_sperm_whale_legend_strongest_armored_weaker_stays` is xfail(strict) to A until Martin rules.
- whale_shark: ok
- blue_whale: ok
- octopus: ok
- great_white_shark: ok
- dolphin: ok
- albatross: ok
- sea_turtle: ok
- hammerhead: ok
- krill: ok
- sardine_legend: ok

Counts: 26 covered, 25 ok, 0 fixed, 1 two readings, 0 wrong and unfixed. No engine file touched, so nothing for the
Rust mirror (`engine_rs`).

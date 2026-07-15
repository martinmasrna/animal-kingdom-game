# Tech-debt register

Durable, cross-review register. “Owner” says where an implementation proposal belongs; this file records the seam even when another area owns the eventual change.

| Item | Where | Severity | Why it is still here | What unblocks it / owner |
| --- | --- | --- | --- | --- |
| Benchmark checkpoints do not fingerprint loaded game data or resolved config | `sim/benchmark_set.py:146-160` | Critical | Resume identity predates frequent retuning and same-path config reuse. | Version and hash card/map data plus resolved `Config`; reject old checkpoints. Engine/sim. |
| Place actions identify a card, not an instance | `engine/actions.py`; `effects.py:114-120,446-480`; `bots/determinize.py:57-71` | High | Card IDs were sufficient before per-instance locks and counters. | Carry `iid` or bind the chosen eligible instance; add locked/unlocked determinization regression. Engine. |
| Printed numeric effects have incomplete config/text linkage | `engine/config.py`; `engine/effects.py`; `tests/test_card_text_consistency.py` | High | Food/cost guards were added reactively after desyncs. | Classify every printed number as Config or typed data; extend generic consistency tests. Code Health, then Cards/Balance. |
| Synthetic deck registration mutates global registry and environment | `sim/deck_optimizer.py:130-151`; `decks.py:38-58`; `sim/benchmark_set.py:138` | High | Spawned workers needed synthetic decks without a registry interface. | Explicit registry/worker payload, or scoped registration with `finally` cleanup. Engine/sim. |
| Public action application does not validate legal actions | `engine/rules.py:62-79`; `effects.py:69-80` | Medium | Bots and recorder validate before calling; engine assumes trusted callers. | Validate publicly and reserve any trusted path explicitly. Engine. |
| Landmark/type model is dormant after animals-only cut | `engine/cards.py:20-25`; `effects.py` `is_unit` branches | Medium | Deliberately deferred to avoid mixing mechanics cleanup with the card cut. | Remove in a focused diff or retain with documented fixtures/tests. Already in Engine backlog. |
| Shelved-card behavior remains in the live effect registry | `engine/effects.py:981-1092, 1314-1347, 1675-1688, 1760` | Low | The card documents deliberately retain handlers for possible reintroduction. | Keep the inventory current; either make the registry explicitly include dormant entries or remove handlers with the shelved-card decision. Cards/Engine. |
| `_find_unit` means any stack depth, not top | `engine/effects.py:263-268` | Low | It previously caused a rules bug; remaining callers were verified appropriate. | Rename/split before adding callers that need visibility. Engine when touched. |
| Engine package has loader I/O despite pure-engine wording | `engine/resources.py`; `engine/config.py` | Low | Convenience loaders were colocated with model types. | Define “pure after construction” or move adapters outward. Code Health. |
| Boundary-level test gaps | `tests/`; `cli.py`; analysis executables | Medium | Milestone work emphasized mechanics and active workflows. | Parser/smoke/provenance contracts, beginning with checkpoint and action boundaries. Code Health. |

Not duplicated: the `UnitInstance` object-model to struct-of-arrays migration is already correctly parked in `docs/engine/backlog.md`; this review found no reason to raise its priority.

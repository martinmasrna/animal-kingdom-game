# Why legendary naming stopped improving: diagnosis, 2026-10-16

Read this before any naming round. It is a diagnosis of the feedback loop, written by /last-hope after reading every naming session from 2026-10-04 to 2026-10-16 (about 3.6 MB of transcript, seven readers, plus the git history of `docs/design/naming.md` and the card data) and running one test. It is not a new rule for names. Do not add it to `naming.md`.

## The one sentence

The loop learns from the wrong verifier: every session turned Martin's reasons for rejecting single names into rules, the rules reject most of the names he loves, and the lists were then judged at first sight by a verdict that reverses within days, so each "finally understood" was a coin flip read as a lesson.

## What every treatment had in common

Twenty-odd treatments in eight days (the counted timeline is at the end): research passes, a review page, "animals as namers", "because one day she...", plain-English nicknames, real given names, a second layer, sound over meaning, archetype names, the gold set, a 1000-word essay, image-and-feeling, psychological principles, mass generation with a rule filter. All of them did the same thing: read the last one to three verdicts, extract a pattern, write it into `naming.md`, generate the next list from it. `naming.md` grew from 472 words and 13 rule bullets (10-09) to 1,530 words and 26 bullets (10-16). The shared assumption, never questioned: **Martin's verdict reasons, written down, generate or select the names he wants.**

## Where the loop breaks

### 1. The verifier is anti-correlated with the target (tested)

Test: a cold Sonnet judge was given `naming.md` (with its Gold and Settled sections removed) and 74 names from the record with their card, shuffled, no verdicts, and asked PASS or FAIL strictly by the rules.

| Group | Passed the rules |
|---|---|
| Martin's 17 gold names | 6 of 17 |
| Gold names the rules file doesn't cite as examples (12) | 1 of 12 (Lobo) |
| Settled, not gold (Luna, Rue, Aya, Calypso, Cuco, Redbeak, Stonetusk) | 5 of 7 |
| Rejected or reopened names (50) | 9 of 50 |
| Overall accuracy | 52 of 74; "reject everything" scores 50 of 74 |

Gold names the rules reject: Aurum, Big Gus, Eon, Iris, King Theron, Lord Bumbleton, Pestis, Queen Adira, Roach King, Scarlett, Vesper. Rejected names the rules pass: Deepeye, Goldbelly, Krag, Snowtail, Thunderchest, Old Brokentusk, Twiga, Zuri, Hrafn.

The rules are true of the names they were written from and nothing else. Every rule is negative (no verbs, no human things, no dictionary words, no everyday names, no templates), and nearly every rule has a gold counterexample: Yuki and Lobo are foreign dictionary words (the Twiga construction), Pestis and Aurum are Latin (the Mephitis construction), Scarlett and Big Gus are everyday Western given names, Lord Bumbleton and Roach King are the title template, Black Swan names the species, Eon is an abstract noun, Greywhisker is the mark compound that Highneck, Snowtail, Mossback, Deepeye and Goldmane failed on. The agent has been checking its lists against a filter that would have thrown away two thirds of the names Martin is happiest with. Martin said this himself: "I don't think this can be templatized" (10-09), "stop trying to find a single golden pattern" (10-16).

### 2. The controls barely move the output, so the agent learned from dice

Counted per sitting (lists shown in chat; a page counts once):

| Sitting | Lists | Options | Locked that day | Still gold 10-16 | Reopened or downgraded within 5 days |
|---|---|---|---|---|---|
| 10-09 | 11 rounds + 3 pages | ~290 | 7 | 2 | 4 |
| 10-14 | 17 lists + 1 page | ~240 | 7 | 2 | 3 |
| 10-16 | ~25 lists + 611 generated | ~850 | 2 | too new | 0 |

On 10-14, 7 of 17 lists produced a lock, and the technique behind the list did not predict it: hits came from a plant list (Rue), a spread-across-sources list (Luna), a mixed list (Yuki), a sound-first list (Aya), a fire list (Cinder), a given-names list (Calypso, Iris); the same techniques missed on the chipmunk, gorilla, tuna and manta. A list that hits two times in five confirms any theory on the next list almost half the time. That is exactly the history: seven theories in two hours on 10-14, each announced as the pattern, each refuted by the next list, each written into the doc anyway. On 10-16 the lists were the most rule-driven and the narrowest (one theory, ten variations) and 2 of 25 hit.

What did predict a hit: breadth. Every lock came from a list built from several unrelated sources at once (Rue from six angles, Luna from eleven, Redbeak and Stonetusk from twelve), and Martin grabbed it on sight. Every miss was one idea ten ways (the wolf's cold-and-white list, the macaque six times, the leopard three times, the honey badger seven times).

### 3. The target moves with exposure, and the loop measures first sight

Martin's first-sight verdict is unstable:

- 7 of the 16 names locked this week were reopened or downgraded within five days (Mimi, Zuri, Twiga, Eber; Cinder within one minute; Vixen; Calypso "maybe not that great").
- The same name reverses over time: Vesper was not kept on 10-09 and is gold on 10-16 (listed twice). Aurum and Pestis were "maybe not" on 10-09 and gold on 10-16. Scarlett was good on 09-28, replaced by Vixen on 10-14, back on 10-16.
- Martin named the mechanism on 10-09: "it's difficult for me to tell whether I like a name because it's objectively good, or because I already got used to it."

Where the gold set comes from: 11 of 17 are names from Martin's own June design, lived with for 3.5 months. The other six are Claude's (Scarlett, Big Gus, Lord Bumbleton, Roach King, Yuki, Iris); each was either grabbed on sight in two minutes or, in Roach King's case, never put to a naming round at all and absorbed through play. None came from a rule. So a name's final status is decided by living with it on the card, through art and play, and the loop never measures that; it measures the first-sight coin and then writes rules from it.

### 4. The lossiest hops in the channel

Martin's feeling, his voice note, the agent's reading, a rule, a list, his reaction. Two hops lose almost everything:

- **Rejection reason into rule.** A reason is about one name ("Drum for a gorilla is Acorn for a squirrel"). As a filter it removes gold (section 1).
- **The agent's framing before the list.** A marked pick or a theory stated above the list contaminates the read: "I cannot look at this unbiased now because you just ruined it with your pick" (10-14). Lists with reasons attached make Martin judge the reasoning instead of the name.

### 5. The base rate

Sixteen names settled in about nine hours across three sittings from about 1,380 options is one settle per 85 options and one per 35 minutes, and four of those sixteen are gold after a week. Professional naming is a group process over weeks, after art, with placeholders and long candidate lists (see the research note below). One person naming fifty legendaries in three sittings is hard at any skill level; the pain is partly calibration. The failure is that the process made it worse each round instead of staying flat.

## Why each previous treatment had to fail

More rules narrow the lists toward one theory, which lowers the chance a list contains a grab (section 2). The theory is confirmed or refuted by a coin (section 2) so the next rule follows either way. The names that do land are judged again days later by a different standard (section 3), and the reopenings feed back as new rules (section 1). Research passes fed the same rule-writer. The essay, the gold set and the image-and-feeling step improved the inputs and the two 10-16 hits followed the image-and-feeling step, but the lists after it were still generated one theory at a time and filtered by the same doc. Mass generation with a rule filter (10-16 evening) is the purest form of the broken loop: 611 names reduced to 100 by a filter that rejects most gold.

## Alternatives that survived, ranked

1. **The generator has no taste for this and nothing structural will help.** Partly true and not the break: six of Claude's names are gold, sixteen settled, and broad lists hit two times in five. Separated from the diagnosis by Test 2 below: if rule-free broad lists hit at the same rate as rule-driven ones, the generator was never the drag.
2. **The characters were not settled, so there was nothing to name.** Supported for the 10-16 cards (Martin's macaque is a crime boss, not a glutton; his honey badger is John Wick) and the two 10-16 hits came right after he gave the image himself. A contributing cause, not the structural one: the 10-14 hits came with no such step.
3. **The target is pure noise.** No: a gold set exists, is stable across 10-09 and 10-16 for the June names, and four loop names reached it.

## The tests

**Test 1, run today: does the rules file select for gold?** Prediction: no. Result above. Disproof would have been 15 or more of 17 gold passing and 10 or fewer of 50 rejects passing.

**Test 2, one sitting of Martin's, about ten minutes: do the rules carry his taste at all?** Three open cards (leopard, manta, giraffe). For each, two pools of 15 names: pool R generated strictly from `naming.md` plus the latest theory, pool F generated with no rules at all from six unrelated sources, rule-breakers allowed. Shuffled into one unlabeled list of 30 per card, no reasons, no pick. Martin marks "this is it" or "close". Prediction: his marks fall in pool F at least as often as in pool R, and at least two of the three cards get a mark. Disproof: 80% or more of the marks in pool R means the rules do carry his taste and this diagnosis is wrong. Zero marks in 90 names means alternative 1 is the real story.

**Test 3, one week later, three minutes: is first sight a verdict?** The 16 names locked this week plus 16 rejected names from the same lists, shuffled, cold: "this is it" or "nope". Prediction: at least 30% of the locked names flip to nope or meh, and at least one rejected name flips to fine. Disproof: locked names 90% or more stable means first sight is reliable and section 3 is wrong.

## What changing the work would take (Martin's call, not a treatment)

Stop writing rules from rejections; keep only the two or three constraints Martin stated as absolute (pronounceable, no human objects). Generate wide and heterogeneous (thirty or more per card from six unrelated sources, no theory above the list) and show them flat with no reasons and no pick. Get the character from Martin first in his own words (image, feeling, a film analogue), which he gives easily and which preceded both 10-16 hits. Treat a first-sight grab as a draft that lives on the card through art and play for a week, then a cold keep-or-nope pass; stop reopening on the day. Expect the base rate: about one settle per two to three broad lists, so the sixteen remaining names are several short sittings, not one.

## Research note (outside the record, 2026-10-16)

- Riot's narrative writers draft lists of about 100 to 200 candidate names per champion, sometimes over 500 with variants, set three to five goals first, and cross names out over rounds with designers and localization; Kindred kept a temporary name after many alternatives were tested (Riot Nexus "Naming New Champions", 2017, via secondary quotes). Wizards' creative lead collects "several suggestions" per name from every team member and picks; late renames are routine (Spectral Lynx, Alchor's Tomb, Onulet), and a placeholder once became the card (Maro).
- Mere exposure: liking rises with repeated exposure (Bornstein 1989 meta-analysis of 208 studies, r = 0.26), strongest for unfamiliar stimuli, and a delay before judging strengthens it. Easy-to-pronounce names are liked and trusted more regardless of length or foreignness (Laham, Koval and Alter 2012; Alter and Oppenheimer 2006). No study was found that compares a first-impression name judgment with the judgment after living with the name, so section 3 rests on this project's own record.
- Language models collapse onto a small pool of names (Elias, Elara, Marcus Chen in most of 20,000 stories; arXiv 2605.26492, 2606.02184), instruction templates reduce diversity even at high temperature (EMNLP Findings 2025), and a practitioner report found a concrete example in the prompt treated as a mandatory template, which is the "Lord XYZ" failure of 10-16. Volume from one model with one brief is not breadth; breadth needs unrelated sources and briefs.

## Record

The counted timeline of every treatment, the hit rates and the origin of each gold name are in the section below, built from the session transcripts (game repo `d1e24d24`, `328aae99`; company folder `8bf8a1d0` for 10-14; design repo `2b213d73` for 10-16).

## Timeline of treatments, counted

| When | Treatment (what changed in how naming was done) | Assumption it rested on | What happened next |
|---|---|---|---|
| 2026-06-29 | Initial pool, 14 legendary names in Martin's own deck design (Prince Leo, Princess Lea, King Theron, Queen Adira, Greywhisker, Black Swan, Aurum, Pestis, Eon, Vesper, Lobo, Scrooge, Methuselah, Fathom, Bulwark...) | none: Martin named them while designing | 12 of these are the gold set 3.5 months later |
| 09-28 | Alpha renamed from 3 options (Scarlett, Maia, Juniper) | a few options and a gut pick | Scarlett: instant "good, sure"; gold on 10-16 |
| 09-30 | "Legendary name pass": Bulwark to Brutonius to Brutus in 2 minutes; epithets dropped; Omen back to Black Swan | - | Brutus "questionable" on 10-16 |
| 10-08 23:35 | Overnight: 6 draft rules from existing names, 3 candidates per card for 27 cards, a review page | rules derived from kept names generate good candidates | 10-09 07:32: "I didn't like a lot of these suggestions... sounded like a verb" |
| 10-09 07:32 | Research agent 1 (MTG, Hearthstone, animal fiction, sound symbolism); rules rewritten (word type, 2-3 syllables, endings); 27 cards x 3 again | a pattern known to work makes a name good | 07:44: 14 of 53 cards kept or liked, mostly existing names; "for the others I didn't like any" |
| 10-09 07:47 | Rule "the card's idea in a word any player can decode"; 2 per card for 33 cards | the meaning pattern explains his 15 picks | 07:53: "100 times worse... Horrible, horrible" (Professor, Migration, Harvest, Gravepicker) |
| 10-09 07:54 | Rule "real given name + meaning quietly fits"; 6 probes | surface reading was the fault | 08:03: "too random... all sound very similar" (Kibo, Jabari, Baraka) |
| 10-09 08:04 | Method "picture first, name = shortest label"; handful at a time | name follows the picture | 08:13: "too on the nose, smells of AI" (Thickskin, Peeper, Gravepicker) |
| 10-09 08:14 | Rule "look and character, never ability" from Scarface | real famous animals are the template | 08:18: "you immediately jump to the other extreme... I didn't say never"; Big Gus "good", Ghost/One-Eye "very good, not these cards" |
| 10-09 08:24 | Research agent 2 (Opus: Sanderson, Tolkien, Riot, Blizzard); "who is doing the naming" | one consistent voice fixes it | 08:38: "this research was very useful"; Arne, Mimi settled; Magnus, Clara "21st-century names" |
| 10-09 08:40 | naming.md written (animals as namers; no Western given names; Simba approach: foreign word for the animal) | foreign animal-words avoid the Western-name feel | Twiga, Eber, Cuco settled (08:42-08:46); all three "fine I guess"/"keeping it simple" |
| 10-09 09:09 | Rules: pronounceable; name after art. Naming parked. | the picture gives the name something to stick to | Mimi, Zuri, Twiga, Eber reopened 10-14 ("all sound bad") |
| 10-14 16:44 | New page: 47 cards, 1-2 options, "my pick first", Latin/Swahili/Zulu words | the two shapes in naming.md | 16:47: "Unpronounceable gibberish, most of them"; 2 picks (Lord Bumbleton, Vixen) |
| 10-14 16:48 | Theory: plain-English nicknames (Stinker, Snowtail, Fatcheeks) | half-second test in English | 17:10: "garbage... lazy... Mrs. Sprout" |
| 10-14 17:11 | Theory: 5 commonalities incl. "each deck is a society" | shared traits of liked names | 17:14: "I wouldn't say each deck is a society" |
| 10-14 17:15 | Theory applied: Brimstone, Pinch, Snowdrop, Gloaming, Drum, with "my pick" marked | character from art + effect | 17:18: "stop saying which one is your pick... sounds so artificial, all these names" |
| 10-14 17:23 | Research agent 3 (how real animals get names); "because one day she..." sentences | names come from one seen thing | 17:36 "feels a lot better"; 17:49 "horrible... Domino, Disco, Grandpa... animals, not humans"; "one card at a time", "at least 10" |
| 10-14 17:50 | naming.md: animals are the namers; one card; 10+ options | - | skunk: 15 options, Rue locked 18:04 |
| 10-14 18:15-18:39 | Lists of 9-14 per card from "different angles" | breadth | Luna, Yuki, Aya, Cinder (unlocked 1 min later), Calypso, Iris locked; chipmunk, gorilla x2, jellyfish x1, tuna, manta x2: nothing |
| 10-14 18:21 | Theory: "sounds like a name first, meaning underneath" | Luna/Yuki/Rue pattern | Aya "maybe" |
| 10-14 18:36 | Theory: "real given names from anywhere with a fitting meaning" (into naming.md) | Luna/Yuki/Aya/Rue are real given names | Calypso, Iris locked; tuna "nope"; manta "yo-yo between these two failure modes" |
| 10-14 18:42 | Theory: "second layer that only fits this card" | the six locks share it | session ends; Claude proposes 40-name flat pages or parking |
| 10-16 13:12 | History subagent; 7 names applied to cards; process rules into naming.md | the record, read, prevents repeats | wolf list: Sirius "good... Harry Potter?"; macaque: "4-letter names again" |
| 10-16 13:46 | Theory: 3+ syllables / two words (Suvarna, Dhanraj) | lengths must vary | 13:48: "overindexing waaaay too much into meaning... Ragnaros, Geralt" |
| 10-16 13:49 | Theory: sound carries character (Bombalu, Grumbeloo) into naming.md | Ragnaros works on sound | 13:52: "all garbage. How is this such an IMPOSSIBLE task????" |
| 10-16 13:53 | Theory: existing archetype names (Ali Baba, Robin Hood, Fagin) | Scrooge/Brutus/Methuselah are references that work | 13:59: "might as well call him Donald Trump" |
| 10-16 14:00 | Theory: roots the English ear knows (Rapax, Avarus, Pilfrey) | Pestis/Aurum pattern | 14:03: "stop using Scrooge, Methuselah, Calypso and Brutus as references" |
| 10-16 14:03 | Gold set asked for and written into naming.md as the only examples | learn from sure names only | 14:07 gold list + "stop trying to find a single golden pattern" |
| 10-16 14:08 | Theory applied: gold-style (Mango King, Lord Tamarind, Fatcheeks) | copy the gold shapes | 14:11: "you didn't even ATTEMPT TO THINK... Lord XYZ... NOT A DUMB AUTOCORRECT"; essay ordered |
| 10-16 14:13 | 1000-word essay (picture before word; sound + owned meaning; word must also be a name; tone matches feeling) | explaining the gold set yields a method | 14:45 "sounds good" |
| 10-16 14:46 | "One image and one feeling" per card, Martin reacts first | agree on the character before names | Redbeak (Martin's edit of Redbill), Stonetusk (swapped in after "razor is human") settled; giraffe "drifting away again"; locust: Martin's own Yellow Death, "first of many" caught attention |
| 10-16 17:09-17:27 | Martin describes characters himself (crime boss; John Wick; the bogeyman of the herds); naming.md: "the effect tells you the character" | character from Martin, not art | leopard x3: "latched onto fire", "too poetic", "think from PSYCHOLOGICAL PRINCIPLES" |
| 10-16 17:45-18:08 | Theories in sequence: calm names (Brock, Krag); from the look (Frost, Chalk); cast a person (Otto, Igor); pet-dog names (Rocco, Buster) | each the last correction | "chalk and ivory are human words"; "you're just hallucinating"; "Ash... he is black and white"; "how did we go from John Wick to tough little dog" |
| 10-16 18:20 | Mass generation: Sol 211 + Astra 200 + Fable 200, cold, then rule filter; 100 rule-passing names | volume plus rules as filter, Martin's taste as selector | 15 + 11 survivors of 411; Martin: "I'm not giving feedback on 150 names"; then "give me 100 that pass the rules"; no verdict recorded; /last-hope opened 2 hours later |

## Hit rates, counted

| Sitting | Lists shown in chat | Options (approx.) | Locked that day | Still gold on 10-16 | Reopened or downgraded within 5 days |
|---|---|---|---|---|---|
| 10-09 (naming pass 1) | 11 rounds + 3 pages (~240 options) | ~290 | 7 (Zuri, Arne, Mimi, Twiga, Eber, Cuco, Big Gus) + Lord Bumbleton liked | 2 (Big Gus, Lord Bumbleton) | 4 (Mimi, Zuri, Twiga, Eber) |
| 10-14 | 17 lists + 1 page (47 cards) | ~240 | 7 (Rue, Luna, Yuki, Aya, Cinder, Calypso, Iris) + Vixen | 2 (Yuki, Iris) | 3 (Cinder in 1 minute, Vixen, Calypso doubted) |
| 10-16 | ~25 lists + 611 generated | ~850 | 2 (Redbeak, Stonetusk) | too new | 0 |
| Total loop | ~53 lists | ~1,380 | 16 | 4 | 7 |

naming.md: 472 words and 13 rule bullets on 10-09; 1,153 words on 10-14; 1,530 words and 26 bullets on 10-16. Lists with a hit: 10-09 about 5 of 11; 10-14 7 of 17; 10-16 2 of 25.

## Where the gold names came from

| Gold name | Origin | How it was accepted |
|---|---|---|
| Prince Leo, Princess Lea, King Theron, Queen Adira, Greywhisker, Black Swan, Aurum, Pestis, Eon, Vesper, Lobo | Martin's own deck design, in the repo on 2026-06-29, before any naming session on record ("Leo, Leah were my ideas, and perhaps Greywhisker", 10-09) | lived with for 3.5 months. On 10-09 Martin was unsure of Aurum, Pestis, Ember ("maybe not"), and Vesper was not kept; on 10-16 Aurum, Pestis and Vesper are gold |
| Scarlett | Claude, 09-28, one of 3 options | "'Scarlett' is good, sure." Replaced by Vixen 10-14, back 10-16 |
| Big Gus | Claude, 10-09 08:14, one of 5 | "Okay, that's a good name as well." Lived with through art and play |
| Lord Bumbleton | Claude, 10-09 page option | "pretty funny... maybe there's a better alternative" (10-09); kept 10-14; gold 10-16 |
| Roach King | Claude, 10-14, used in play narration, never put to a naming round | absorbed through play; gold 10-16 |
| Yuki, Iris | Claude, 10-14, from lists of 12 and 8 | "Yuki is good." "Iris is good." (2 minutes each) |

## Test 3, to run on or after 2026-10-23

Show Martin these 34 names cold, shuffled, each with its card, one keystroke each: "this is it" or "nope". No reasons, no reminder of which were locked. Then compare with the key.

Locked between 10-09 and 10-16 (18): Mimi (mimic octopus), Zuri (zebra), Twiga (giraffe), Eber (boar), Cuco (cuckoo), Arne (eagle), Big Gus (capybara), Lord Bumbleton (bumblebee), Rue (skunk), Luna (white wolf), Yuki (white squirrel), Aya (sloth), Cinder (leopard), Calypso (jellyfish), Iris (rainbow octopus), Vixen (fox), Redbeak (oxpecker), Stonetusk (boar).

Rejected from the same lists (16): Thistle (skunk), Plume (skunk), Avalanche (white wolf), Blanca (white wolf), Ermine (white squirrel), Pearl (white squirrel), Orchid (sloth), Selva (sloth), Monsoon (gorilla), Wildfire (leopard), Nerissa (jellyfish), Marina (jellyfish), Mira (mimic octopus), Echo (mimic octopus), Coral (oxpecker), Grizzle (boar).

Prediction: at least 30% of the locked names get "nope" or hesitation, and at least one rejected name gets "this is it". Disproof: 90% or more of the locked names hold.

## Test 2, run 2026-10-16: result

Pools generated by two cold Sonnet agents: pool R strictly from `naming.md`, pool F with no rules and six required kinds, 15 each for the leopard, the manta and the giraffe, shuffled into 30 per card, graded by Martin in a one-name-at-a-time page (https://claude.ai/artifact/TwNbyv79SspvPf3HHT781u) with four buttons.

| Verdict | From the rules pool (45) | From the rule-free pool (45) |
|---|---|---|
| This is it | 0 | 0 |
| Great name, not this card | 2 (Coldeye, One-Ear) | 1 (Cinder) |
| Close, not this card | 2 (Ashtail, Mirra) | 6 (Ember Tooth, Tamsin, Starlight, Nyx, Mira, Long Tom) |
| Absolutely not | 41 | 38 |

Reading: the rules did not carry Martin's taste (4 non-rejections from the rules pool, 7 from the rule-free pool; the 80%-in-R disproof is far off), so section 1 stands. But zero "this is it" in 90 names is the outcome that was named as evidence for alternative 1: two cold Sonnet generators with one brief each produced nothing he would take, where the 10-14 lists (Opus and Fable in context, several angles per list) produced a lock in 7 of 17 lists. So breadth is not volume from one cold model with one brief; the generator and the brief matter, and the slow loop's generation step must use several models and several unrelated briefs per card. Cinder came back as "great name, not this card", the same read Martin gave it on 10-14 after unlocking it, which is one small point for first-sight stability on the "great name" axis.

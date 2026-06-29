# Flavor Review — Reworked 7-Deck Pool

Audit lens: **flavor only** (theme, naming, tags, effect↔animal, strength↔animal, deck identity).
Balance is explicitly out of scope. Any suggestion that touches what a card *does* (effect wording
or strength value) is labelled **⚠ FLAVOR-DRIVEN CHANGE — needs a separate balance review**; every
other fix is a pure reskin (swap the animal / name / tag onto the existing strength + effect).

Source of truth: the 7 files in `docs/decks/` (uploaded 2026-06-28). `cards.md` §5–9 ignored (legacy).

Cards that already feel right are **not** listed — only genuine issues. Decks come out very strong
overall; the heaviest items are concentrated in **Colony** (caste one-species tension), **Canine**
(two theme/naming problems + a size-inversion), and the **Aggro/Colony hornet collision**.

---

## 1. Per-deck flavor findings

### Deck 1 — Cats Midrange Tempo
Cleanest deck in the pool. The lion royal-family legendaries (Prince Leo, Princess Lea, King Theron,
Queen Adira) all read well — Theron ("hunter") and Adira ("noble/strong") carry light resonance
without citing a myth; the Leo/Lea twin fetch is a deliberate designed pair. Keep all four.

- **Black Panther (rare, Cat 6) — species must be pinned, or it self-collides.** A "black panther"
  is not a species; it is a *melanistic leopard* (Africa/Asia) or a *melanistic jaguar* (Americas).
  If read as a black **jaguar**, it duplicates the deck's own **Jaguar** (one-species violation
  within the same deck). Fix (reskin, no mechanics): explicitly treat Black Panther as a melanistic
  **leopard** (Panthera pardus — a species that appears nowhere else in the pool). Worth a one-line
  art/flavor note so nobody later draws it as a jaguar. Snow Leopard is a separate species and is fine.
- **Serval (rare, Cat 2) — mild effect↔animal tension, but intentional.** A tiny serval (str 2)
  whose Battlecry only removes *big* enemies (str 6+) reads slightly backwards — you expect the small
  cat to pick off small prey. It's clearly the deliberate mirror of Jaguar (removes ≤5), and servals
  are famous leapers that punch above their size, so I'd **keep it** — just flagging that the pairing
  is the only thing carrying the flavor. No change recommended.

### Deck 2 — Egg Control
Thematically tight: the egg-eating snake paying out on egg removal, the scavenging vulture, the
hoarding raven, the scouting owl, the disruptive "black swan event." Keep almost all of it.

- **Rattlesnake (rare, Snake 6) — thin effect↔animal link.** "Whenever you shuffle a card, gain 5
  food" leans on rattle≈shuffle, which is a weak pun (shuffling is a deck action, not a rattle). It's
  acceptable and the snake earns its slot, but if you ever want a cleaner fit, a **Sidewinder**
  (literally shuffles through sand) maps onto "shuffle" more naturally — pure reskin (same tag/str/
  effect). Low priority; keep if you like the rattlesnake silhouette.
- **Strength note (no change):** Rattlesnake at 6 is high for a small-bodied snake, but "strength =
  danger/venom" is a defensible reading here. Leaving it.

### Deck 3 — Colony Food Swarm
Excellent eusocial flavor, and a genuinely nice touch: **wingless ants stay grounded (no Flight)
while the winged bees/wasps/hornets fly** — that consistency is doing real work, keep it. Termite
**King** is a standout: termites are the one eusocial group with a persistent king, so the King/Queen
split is more accurate than ants-or-bees would be.

- **Caste one-species tension — the headline (see Cross-pool §2.A for the full treatment).** Within
  this deck, Queen Bee / Worker Bee / Nurse Bee are all *one species* (honey bee, Apis mellifera) and
  Worker Ant / Soldier Ant are all *one species* (a single ant). By a strict read of §2.1 that's a
  triple- and a double-violation. The deck's whole identity, though, is *castes of one hive*, which is
  exactly how real colonies work. This needs a deck-level ruling, not a per-card reskin — see §2.A.
- **Champion of the Hive (legendary, hornet) — minor irony.** Hornets are the bee-hive's *predators*
  (they raid honeybee nests), so a hornet billed as "Champion of *the* Hive" reads slightly against
  type. It's defensible — hornets fiercely guard their *own* nests — so I'd keep it, but if you want
  it airtight, a **giant wasp / "Soldier Wasp"** champion sidesteps the irony. Low priority.

### Deck 4 — Ramp
Big-body flavor lands well. **Oxpecker** is the gem — a tiny bird that earns food per *big* unit in
your deck is precisely the oxpecker's real symbiosis with rhinos and buffalo. **Hippopotamus**
(kills things that wander into its space) and the **Immovable hoarding tortoise** are both spot-on.

- **Fig Tree / Watering Hole (Landmarks) — non-animal; see §2.C for my opinion.** Flagged as the
  permitted exception; the theme question is parked (`todo.md`). Opinion in cross-pool section.
- **Tortoise tag inconsistency (cross-pool, see §2.B):** the colossal tortoise here is `Megafauna`,
  but Food OTK's Giant Tortoise is tagless. Pick one convention for tortoises.
- **Black Bear (common, Bear 5) — flavor-thin effect.** "In 2 turns, draw 1" doesn't say "bear" the
  way Grizzly's delayed maul does. It's fine (you can read the delay as the bear lumbering/waking),
  just the weakest flavor-to-animal tie in the deck. No change needed.

### Deck 5 — Food OTK
Flavor MVP deck. **Opossum** ("Deathrattle: return this to hand" = playing dead then getting up),
**Pufferfish** (kills whatever eats it), and **Gazelle/Impala** (prey that, once eaten, feeds the
hunter) are all textbook-perfect for a sacrifice engine. Keep all of them.

- **Kraken octopus legendary (—, 4) — weak effect↔animal tie.** "Draw a legendary unit" doesn't
  obviously read as *octopus*. It works as "the deep summons its monsters," but it's the one Food-OTK
  effect that's carried by the art note rather than the animal. No reskin needed (it's the combo
  enabler and an octopus-as-eldritch-thing is evocative enough); just noting it's the soft spot.
- **Giant Tortoise (rare, —, 5) — tag inconsistency with Ramp (see §2.B).**

### Deck 6 — Aggro HQ Rush
Reads great as a rush deck: the fastest cat (Cheetah) and a diving falcon both rewarded for hitting
the enemy base, lemmings swarming onto empty ground, the plague rat nuking a whole tile, the skunk
spraying an enemy back to hand. Strong identity throughout.

- **"Hornet" (rare, —, 2) — cross-pool species collision + retag question (see §2.A).** This tagless
  expendable "self-sac to kill an adjacent enemy" hornet duplicates the species of Colony's **Guard
  Hornet** (one-species rule is pool-wide). The self-destruct-on-sting flavor is iconically *bee/wasp*,
  but bee and wasp are both taken by Colony. Cleanest reskin (pure, no mechanics): rename to a
  *distinct* stinging insect not used elsewhere — **Tarantula Hawk** (a wasp famous as a brutal
  single-kill, with one of the most painful stings on Earth) or **Velvet Ant** ("cow killer," another
  species). Either keeps the "expendable lethal sting" fantasy without colliding with the hornets.

### Deck 7 — Canine Buff Tempo
Good pack-buff fantasy (anthems = the alpha's presence, the rallying howl, the jackal scavenging the
dead for food). But it carries the audit's two clearest **theme** problems and a size-inversion.

- **"howl, voice of the pack" legendary (Canine 4) — a howl is not an animal (THEME).** As written
  the card *is* "a howl," which would be a non-animal that isn't a Landmark — a theme violation. The
  intent is obviously a **named wolf whose Battlecry is the great unifying howl** (the effect, "+1 to
  all Canines," is perfect). Fix (reskin, no mechanics): make the card a real wolf with a proper name
  and let "the howl" be its effect/epithet, not its identity. Names in §3.
- **"hellhound" legendary (Canine 6) — an invented/mythic creature (THEME + §2.1 naming).** A
  hellhound is a supernatural dog; §2.1 forbids invented creatures and direct myth references, and
  requires the animal stay real. The *effect* (pull a fallen pack-member back from the Remove Pile =
  raising the dead) is wonderful and very "black dog of folklore." Fix (reskin, no mechanics): make it
  a real black wolf/dog and give it a name that *evokes* the black-dog/underworld legend without
  citing it. Names in §3.
- **Fox / Dingo strength inversions vs Gray Wolf / Coyote (STRENGTH↔ANIMAL).** Real canid size runs
  Gray Wolf > Red Wolf > Coyote > Dingo/Jackal/Dhole > Fox (smallest). The cards have **Fox 5** and
  **Dingo 5** out-bodying **Gray Wolf 4** and **Coyote 3** — a fox out-muscling a wolf reads
  backwards. The deck file itself invites this flag ("Fox/Dingo/Red Wolf/alpha animals flexible").
  - *Reskin option (no mechanics):* since the animals are flagged flexible, reassign so body size
    tracks strength — e.g. let the str-5 "gas engine" (draw-when-buffed, a clever-opportunist effect)
    ride on a **Coyote** or **Jackal** rather than a Fox, and let the small str sit on the Fox.
  - *If the strengths are locked for the buff engine:* **⚠ FLAVOR-DRIVEN CHANGE — needs a separate
    balance review** to instead lower Fox/Dingo bodies toward real canid sizes. Don't do this silently.
- **Red Wolf (rare, 6) vs Gray Wolf (common, 4) — minor inversion.** Red wolves are *smaller* than
  gray wolves, so Red Wolf 6 > Gray Wolf 4 is mildly off. Lowest priority of the canine items; folds
  into the same body-vs-size question above. No standalone change recommended.

---

## 2. Cross-pool checks

### 2.A One-species-per-pool (commons + rares; legendaries exempt)
Two real findings; everything else (bears split polar/grizzly/black, the squirrel vs flying-squirrel,
the rat/mouse/jerboa/lemming spread, leopard vs snow-leopard once Black Panther is pinned) is clean.

1. **Hornet ×2 across decks — a true violation.** Colony **Guard Hornet** (common) and Aggro
   **Hornet** (rare) are the same species in different decks, and the rule is pool-wide. Resolve by
   reskinning the Aggro one to a distinct stinging insect (Tarantula Hawk / Velvet Ant — see Deck 6).

2. **Colony castes are one species each — a structural tension, needs a ruling not a reskin.**
   - Honey bee (Apis mellifera): **Queen Bee + Worker Bee + Nurse Bee** = three commons/rares of one
     species. Ant: **Worker Ant + Soldier Ant** = two commons of one species.
   - §2.1 says sex/age/subspecies count as the same species; castes are exactly that. *But* `README`
     decisions A and B explicitly bless caste-distinctness for this deck, and real colonies genuinely
     *are* one species in many castes — so the caste design is **more** true to nature, not less.
   - **My recommendation:** formally carve a narrow **"eusocial castes" exception** into §2.1 (castes
     of one Colony species may repeat *within the Colony tribe*), rather than diversifying species —
     splitting the hive across unrelated bee species would *cost* flavor. If you'd rather keep §2.1
     strict, the alternative reskin is to make each caste a *different* real social species (e.g. honey
     bee / carpenter bee / mason bee), but I'd advise against it on flavor grounds. Flagging for a
     human call; no silent change.

### 2.B Tag-taxonomy inconsistencies
- **Tortoise tagged two ways:** Ramp's colossal tortoise = `Megafauna`; Food OTK's Giant Tortoise =
  tagless (`—`). Same kind of animal, two tag treatments. Pick one — I'd lean **tagless** for both
  unless you want tortoises pulled into Megafauna synergies, since a slow tortoise isn't "megafauna"
  in the charismatic-herd sense the Ramp tag otherwise evokes. (Pure tag swap; no mechanics if no
  card references Megafauna yet, which per README is currently the case.)
- **`Fish` tag — doc drift, not a card problem.** `README` decision B lists `Fish` as
  "dormant/reserved (no current card)," but **Pufferfish** (Food OTK) is tagged `Fish`. Not a flavor
  fault — Pufferfish↔Fish is correct — just reconcile the README so Fish is marked *active*.
- Otherwise tags fit their animals well (Fox/Dhole/etc. = Canine, Cheetah = Cat, Chameleon = Lizard,
  spiders = Arachnid, tortoise/rhino/hippo/elephant = Megafauna). No animal↔tag *mismatches* found.

### 2.C Non-animals
- **Only Landmarks (Fig Tree, Watering Hole) and the "howl" legendary are non-animal.** The howl is a
  fixable mislabel (Deck 7 — make it a wolf). The Landmarks are the deliberate, parked exception.
- **My Landmark flavor opinion (the question is undecided — `todo.md`):** I *like* Landmarks as a
  sparingly-used type and would keep them. A watering hole and a fruiting fig tree are exactly the
  shared, contested *resources* a kingdom of animals would gather and fight over, so they read as
  part of the world rather than foreign objects — and "build the watering hole, reap food" is clean
  ramp flavor. The one genuine wart is mechanical-flavor, not conceptual: **Apex Predator "eats" a
  Landmark** (a tiger devouring a tree) reads badly (`keywords.md` notes this too). If you keep
  Landmarks, consider letting Apex Predators *trample/raze* rather than *eat* a Landmark — but that's
  a **⚠ FLAVOR-DRIVEN CHANGE — needs a separate balance review**, so I'm only noting it. Net: keep
  Landmarks, keep them rare (just these two), revisit only the "eats a tree" wording.

---

## 3. Legendary names (options — no single winner; the human chooses)

Cats (Prince Leo, Princess Lea, King Theron, Queen Adira) are already named and read well — left out.
Each entry below is a *named individual real animal*; names carry light folklore/literary/historical
resonance but avoid directly citing the myth-creature the card evokes (no Ouroboros/Phoenix/Cerberus/
Roc/Fenrir, etc.). A few borderline picks are flagged inline.

### Egg Control
**Ancient cycle-snake** (Snake 6, draw/shuffle/remove → food; "Ouroboros" art note):
- **Eon** — the unending cycle of draw-shuffle-remove made into a name; spare and timeless.
- **Sempiterna** — "everlasting"; an elegant, eternal-feminine ring for the self-renewing serpent.
- **Coil** — evokes the tail-in-mouth loop without naming the myth.

**Giant anaconda** (dynamic str = removed units; "swallows everything"):
- **Goliath** — green anacondas are literally nicknamed the goliath of snakes; evokes a famous *giant*
  (a man, not a snake-myth), so it reads as size, not citation.
- **Maw** — the all-swallowing mouth; pure menace, scales with the "eats everything" fantasy.
- **Gorge** — to gorge / a thing that engulfs; doubles as a place that swallows.

**Fire-coloured rebirth bird** (Bird 5, Flight, shuffles back when removed; "Phoenix" art note —
pick a real vivid bird, e.g. Scarlet Ibis or Golden Pheasant):
- **Ember** — the coal that rekindles; rebirth without saying the word.
- **Cinder** — rises from its own ashes; slightly darker, very on-theme.
- **Aurelia** — "golden/dawn"; the bird that returns with each sunrise.

**Golden egg** (Egg 0, Fragile, draw each turn; "goose that laid the golden egg" folklore):
- **Aurum** — Latin gold; clean and regal for the one perfect egg.
- **Fortune** — the lucky egg that keeps paying out (the draw engine).
- **Gilda** — from "gild/gilded"; a name that quietly says golden.

### Colony Food Swarm
**Ant queen** (Colony 4, +4 food per other Colony):
- **Marabunta** — the folkloric word for the legendary all-consuming army-ant swarm; mythic-flavored
  but not a myth-creature cite, and pure ant.
- **Antonia** — a regal Roman name with "ant" hiding in it; matriarch energy.
- **Imperata** — "the commanding one"; an empress for the colony engine.

**Champion of the Hive** (Colony 2, Flight, +2 per Colony; "deadly hornet" — keep epithet, add a name):
- **Vesper, Champion of the Hive** — *Vespa* is the hornet genus; martial, evening-toned.
- **Maxima, Champion of the Hive** — the *giant* hornet (Vespa mandarinia = "maxima"); biggest soldier.
- **Reaver, Champion of the Hive** — plain menace for a card that scales into a lone bruiser.

**Bee queen** (Colony 5, +5 food per Colony played):
- **Honoria** — "honour" + honey; a stately honey-monarch name.
- **Apia** — from *Apis* (the bee genus); compact and regal.
- **Melissa** — Greek for "honeybee." *Borderline:* Melissa was also a bee-nymph, so it brushes
  folklore — but it reads first as an ordinary name, so I'd allow it; flagging for your call.

**Hilariously fat bumblebee** (Colony 3, Flight, +3 food rider):
- **Falstaff** — Shakespeare's rotund, jovial knight; literary (not a myth), perfectly captures a
  fat, merry bumblebee. My favourite for tone.
- **Lord Fuzzwick** — a pompous, fuzzy little noble; leans into the comedy.
- **Tubbins** — affectionate and round; pure good-natured silliness.

### Ramp
**Colossal ancient tortoise** (Megafauna 5, Immovable, +10 food/turn; the ramp wall):
- **Methuselah** — the proverbially oldest; light biblical/folklore resonance for an ancient.
- **Jonathan** — a nod to the real, world-famous oldest living tortoise; "real named individual"
  taken literally, and quietly funny.
- **Aldabra** — the giant-tortoise atoll/species name; evocative and unmistakably tortoise.

**Giant polar bear** (Bear 10, Apex Predator, Costs 20):
- **Borealis** — of the far north; cold grandeur.
- **Tundra** — the white waste made flesh; blunt and big.
- **Whiteclaw** — a descriptive individual-name for the white giant. *(Avoided "Nanook" — that's a
  folklore bear-spirit, borderline cite.)*

**Giant harpy eagle** (Bird 8, Flight, Apex Predator, Costs 20):
- **Aquila** — Latin for eagle (and the constellation); clean, soaring, no myth-creature.
- **Tempest** — the storm that drops out of the sky; matches the Apex dive.
- **Skyrender** — descriptive epithet-name for a 20-cost sky predator. *(Avoided "Roc" — direct
  giant-bird myth.)*

**Titanic rhino** (Megafauna 10, Immovable, Costs 20, removes all adjacent; fortress finisher):
- **Bulwark** — a living rampart; perfect for the Immovable stomp-wall.
- **Bastion** — the fortress that also flattens its surroundings.
- **Rampart** — same fortress register, slightly more aggressive. *(Avoided "Behemoth/Juggernaut" —
  both are myth/deity-derived cites.)*

### Food OTK
**Kraken-like octopus** (—, 4, draw a legendary):
- **Fathom** — the unsounded deep; mysterious and apt for a "summon the monsters" effect.
- **Nautilus** — deep-sea, with a literary (Verne) rather than mythic ring.
- **Abyssa** — the abyss personified; ominous and oceanic. *(Avoided "Kraken/Nereus.")*

**Old wise mouse** (Rodent 1, food + draw + extra play):
- **Greywhisker** — the elder of the warren; age in one word.
- **Eldwin** — "old friend/elder"; a kindly sage name.
- **Pip the Wise** — small-and-humble made a title; affectionate.

**Black widow "the Devourer"** (Arachnid 5, sac up to 3 friendly, draw each; female name):
- **Carmilla, the Devourer** — gothic literary man-eater (not a myth); femme-fatale to the bone.
- **Vespera, the Devourer** — "evening/dusk"; dark and elegant for a cannibal widow.
- **Mortessa, the Devourer** — "mort" (death) feminised; on-the-nose menace. *(Avoided "Lilith" —
  folklore demon, borderline cite.)*

**Squirrel "Keeper of the Stash"** (Rodent 4, store food → double in 2 turns):
- **Scrooge, Keeper of the Stash** — literary miser/hoarder; instantly legible and a little funny.
- **Croesus, Keeper of the Stash** — proverbial "rich as Croesus" (a historical king, not a myth);
  evokes a vast hoard.
- **Cache, Keeper of the Stash** — the buried stash as a name; spare and thematic. *(Avoided "Midas" —
  direct golden-touch myth.)*

### Aggro HQ Rush
**Rat King** (Rodent 3, +1 str per other unit; "writhing mass of rats"):
- **Verminus** — a Latinate vermin-monarch; grand and grimy.
- **Gnashtail** — the tangled, gnashing mass made a name; visceral.
- **Pied** — a quiet nod to the Pied Piper's rats (folklore, not cited whole); ominous and brief.

**Plague Rat** (Rodent 3, remove everything from an adjacent crossroad):
- **Pestis** — from *Yersinia pestis*, the plague bacterium; clinical and chilling, no myth.
- **Blight** — the spreading ruin; simple and total, matching the tile-wipe.
- **Miasma** — the bad-air that was once blamed for plague; folklore-flavored, not a creature cite.

**Legendary skunk "Choking Cloud"** (—, 5, mass-bounce all adjacent enemies):
- **Sirocco** — a choking desert wind; the cloud that drives everyone back.
- **Reek** — blunt, funny, and exactly what clears the HQ front.
- **Mephitis** — literally the skunk genus (*Mephitis mephitis*) and the old word for noxious vapour;
  evocative and accurate. *Borderline:* also a minor Roman vapour-deity — flagging, but the genus tie
  makes it defensible.

**Legendary bird of prey "Great Raptor"** (Bird 6, Flight, remove adjacent ≤6):
- **Stoop** — the falcon's killing dive; a single sharp verb-name.
- **Peregrine** — "the wanderer" (and a falcon species); noble reach-flyer.
- **Skystriker** — descriptive epithet-name for the beachhead snipe.

### Canine Buff Tempo
**Towering alpha wolf** (Canine 4, +2 str per other Canine; self-scaling leader):
- **Lobo** — the real, legendary wolf "Lobo, King of Currumpaw" (Seton); a true named individual with
  folklore weight, fully real animal. Strong pick.
- **Greyback** — the scarred old pack-leader; descriptive and rugged.
- **Rurik** — a hard, chieftain-flavored name for the alpha. *(Avoided "Fenris/Fenrir" — direct
  wolf-myth.)*

**"hellhound"** (Canine 6, return a fallen Canine from the Remove Pile + give +2; must become a real
black wolf/dog — see Deck 7):
- **Shuck** — from England's "Black Shuck," the spectral black dog of folklore; evokes the legend
  while the card stays a real black wolf. Best fit for the raise-the-dead effect.
- **Grimm** — the churchyard "grim" (a folkloric black dog that guards the dead); ominous and apt.
- **Mourn** — names the funeral/underworld tone directly without any creature cite. *(Avoided
  "Cerberus/Garm" — direct hell-hound myths.)*

**Wolf matriarch** (Canine 4, your other Canines have +2; anthem):
- **Ylva** — Old Norse for "she-wolf"; a real name that simply *means* the thing.
- **Raksha** — the wolf-mother who adopts the pack in Kipling (literary, not myth); perfect for an
  anthem matriarch.
- **Luna** — moon-named, classic for a lead wolf; warm and recognizable.

**"howl, voice of the pack"** (Canine 4, give +1 to all other Canines in hand and field; must be a
real wolf whose Battlecry *is* the howl — see Deck 7):
- **Clarion** — a clarion call; the rallying summons made a name.
- **Cantor** — the lead voice that the chorus answers; the wolf who starts the howl.
- **Echo** — the howl carrying across the territory and lifting the whole pack.

---

## 4. Summary of the biggest findings
1. **Canine theme problems (must-fix):** "howl, voice of the pack" is literally a *howl* (non-animal,
   non-Landmark) and "hellhound" is an *invented/mythic creature* — both need to become real, named
   wolves/dogs (effects are great; only the identity/name needs reskinning).
2. **Colony caste vs one-species-per-pool:** honey-bee castes (Queen/Worker/Nurse Bee) and ant castes
   (Worker/Soldier Ant) each collapse to one species under §2.1, yet that's how real colonies work and
   the README already blesses it. Recommend formally adding a narrow "eusocial castes" exception rather
   than splitting the hive across species. Needs a human ruling.
3. **Hornet collision:** Colony Guard Hornet and Aggro Hornet are the same species pool-wide; reskin
   the tagless Aggro one to a distinct stinging insect (Tarantula Hawk / Velvet Ant).
4. **Canine size-inversions:** Fox 5 and Dingo 5 out-body Gray Wolf 4 / Coyote 3 (a fox out-muscling a
   wolf). Reskin which animal carries the engine, or treat body changes as a ⚠ balance-gated edit.
5. **Black Panther must be pinned to a melanistic *leopard*** so it doesn't duplicate the deck's Jaguar.
6. **Small stuff:** tortoise tag inconsistency (Megafauna vs tagless), the README's stale "Fish
   dormant" note (Pufferfish uses it), and the Apex-Predator-eats-a-Landmark wart.
7. **Landmark opinion:** keep them (sparingly) — a watering hole / fig tree read as contested kingdom
   resources, not foreign objects; only the "predator eats a tree" wording needs a later look.
8. **Legendary names:** 24 legendaries (all but the four Cats) get 2–3 explained candidates each in §3,
   carefully evoking folklore/literature without citing the myth-creatures they resemble.

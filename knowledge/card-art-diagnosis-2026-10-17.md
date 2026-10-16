# Why card art kept costing this much: diagnosis, 2026-10-17

Read this before changing how card art is made. It is a diagnosis of the feedback loop, written by /last-hope after reading the whole record (the 2,049-line manifest, every version of `cards/art-principles.md`, the skill, the spec, the overnight handoff, the research findings, the 1,857-image research set, Sol's actual image prompts from the Codex session logs, and Martin's 3,408 messages across 43 sessions since 2026-09-26, the post-10-10 ones through four readers) and running one test. It is not a new rule for art. Do not add it to `art-principles.md`.

## The one sentence

The loop's learner cannot see the target and its levers do not move the output: every treatment had an agent turn Martin's reactions into words between him and an image model, and a cold agent given all 39 KB of those words picks Martin's picture no better than an agent given nothing (11 of 31 against 10 of 31, chance 8), so three weeks of rules were written by a judge that cannot judge, from rounds whose outcome the words never changed.

## What every treatment had in common

The counted timeline is at the end. In three weeks: an art-direction doc (09-25), "the animal is the hero" and "myth in the animal" (09-28), a principles rewrite with good/bad sheets and a gut grade of 106 cards (10-04), habitat sections (10-05), True Names, a Sonnet gate, a Luna verbatim proxy, a manifest and a review page (10-09), the research findings and "the proven template", Sol's rewrite restored, swatch and layout arms (10-10), four bets, named backdrops, photo pose skeletons (10-11), legendary, pair and scale templates (10-12), character rules (10-14), the diag rounds and a gouache template (10-15). `art-principles.md` went from nothing on 10-04 to 39 KB on 10-16 in 60 commits, 44 of them in the last seven days. Four decisions reversed within a day or two with evidence cited both ways: Sol's rewrite (the enemy on 10-09, "part of the recipe, never bypassed" on 10-10), gates (built 10-09 morning, "no gates" 10-09 evening, a judge again in the overnight brief, "Martin judges anatomy" 10-11), a separate legendary template (10-12, back to one template the same day), primates on all fours (10-16 morning, "hands and gaze, not its sitting" 10-16 afternoon).

All of them did the same thing: read Martin's last verdicts, write what they seemed to mean into text (a template, a rule, a True Name, a brief, a line), send the text to the image model, read the next verdicts. The shared assumption, never tested: **an agent can tell from Martin's words which picture he will like, and can write words that make the model paint it.**

## Where the loop breaks

### 1. The verifier is blind (tested twice)

On 10-04 Claude graded the 106 live cards wow/good/fine/weak before reading Martin's grades. Exact agreement 40 of 106; expected by chance from the two marginals, 33. Of Martin's 15 wows, Claude called 2 wow, 5 good, 4 fine and 3 weak. The record kept the file (`cards/bar/claude-blind.md`) and never computed this.

Today's test (details at the end): 31 review rounds from the manifest where Martin picked one of 3 or 4 candidates, candidates shuffled, three cold agents asked which one he picked.

| Agent | Agreed with Martin | Chance |
|---|---|---|
| Sonnet, no guidance | 10 of 31 | 8.2 |
| Sonnet, after reading all of `art-principles.md` | 11 of 31 | 8.2 |
| Opus, after reading all of `art-principles.md` | 9 of 31 | 8.2 |
| Majority of the three | 8 of 31 | 8.2 |

The three agents agreed with each other on 10, 14 and 15 of 31 pairs, also near chance. The rules file did not move any of them. Disproof would have been 19 or more of 31. So the party writing the rules cannot see what the rules are about, every "what works" it wrote is unverified, and Martin said it on 10-10: "the models cannot judge that... you rejected a bunch of good cards just because... the head was turned slightly towards the camera", and "it's too long already, with too many rules for me to be able to process it properly." Fifty more commits followed.

### 2. The controls do not move the output, so the agent learned from dice

- The record's own controlled test (`research/findings.md` section 6, 10-15): ten diag rounds, same lines, one lever changed each; night versus day, named backdrop, loose sheet, a single loose painting, dropping "painted in the most detail", the 10-09 recipe, a similar-subject reference, an in-hand repaint. No lever moved the finish. The subject did.
- Attempts per settled picture by day, while the rules grew: 22.5 (10-09), 8.7, 3.9, 12.2, 6.0, 4.4, 71 (10-15, one settle), 7.5 (10-16). No trend. The 10-11 low is the four-bet design's floor (four pictures, one pick) on whole-habitat first passes, not a learned gain.
- The Luna verbatim route and Sol's rewrite performed the same within the one batch family that ran both: Savanna, Luna 11 of 291 settled, Sol 12 of 243. The 10-10 ruling that "the verbatim stretch was the worst in the record" compared different cards through a different pipeline.
- Of 22 named experiment arms, 17 produced zero settled pictures (swatch, swatch+ref, sheet, paint, reverse, short, detailed, model-chooses, keep-line+rules, combine...). Each was read as "that lever is wrong". With four pictures per arm and a 10% base rate, zero is the expected result of a working lever too.
- 31% of cards settled in one round; the mean is 3 rounds; the top fifth of cards took 44% of all rounds. Cape Buffalo took 65 pictures and 7 rounds, Greywhisker 46 and 15, the Squirrel legendary 36 and 9. Martin on 10-12: "this is what, like, fifth round or fourth we're already spending on these two cards. This is usually a signal that, like, something is wrong on a fundamental level."

Martin named the mechanism on 10-10: "This entire art generation feels like rolling a dice or like shaking a black box that you don't know how it works", and "the harder I try, the worse the final outcome is."

### 3. The target moves with context, and the loop measures first sight

- Three readers counted 34 reversals in Martin's own messages between 10-10 and 10-16: a settled Crocodile, Mole-Rat and Termite Queen rejected the next day as "repainted photography" once seen beside the commons; the Gorilla pick changed in five minutes; the "sultan" Macaque rejected as humanised on 10-14 and preferred over all four replacements on 10-16 ("is the sultan one even that bad?"); the Wild Dog pack ("I don't see what was wrong with it in the first place"); the Vulture ("the original image is much, much quieter"); the Tiger back to its 09-26 crouch on 10-16; the coral snake back to the bite close-up; Borealis and Raksha kept their originals after 12 and 65 pictures.
- On 10-15, after calling a whole round "all too sharp and photorealistic", he said: "maybe I'm just being completely delusional and the art is fine."
- His 10-04 grades did not protect a card: 8 of 15 wows were repainted afterwards, as were 9 of 16 weaks. Repaints were driven by habitat moves and consistency passes, not by what he had rated.
- Published same-person test-retest correlations for aesthetic judgments of images cluster around 0.6 to 0.7 with wide individual spread (Vessel and Rubin; Tractinsky et al., median 0.60). A verdict that correlates 0.65 with itself cannot be fitted by rules written from single verdicts.

The commons he calls wow (Eagle, Viper, Cheetah, Oxpecker, Hyena, Raven, Hornet, Jerboa) are stable; the unstable part is "legendary enough" and "too photographic", the two judgments that drove most repaint rounds and that no one, including Martin, can state in words ("I cannot explain why").

### 4. The lossiest hops in the channel

Martin's feeling, his voice note (transcribed: "gepard", "Canad", "done" for dawn), the agent's reading, a line, the template, Sol's rewrite, the image model, the review page, his pick and note, a rule. Two hops lose the most:

- **Sol's rewrite.** Measured on 356 attempts joined to their Codex session logs: the 376-word template becomes a 396-word spec in the Codex image skill's own format. "Never a landscape with a small animal in it" survives in 31 of 295; "silhouette reads" in 150 of 312; Sol adds "crisp" or "selective crisp detail on face, hands, fur" in 100 of 356 prompts, which is the finish Martin rejected on 10-15. The record's `prompt` field is what Sol received, not what the model got. Martin asked on 10-10 at 19:01: "show me actual prompts (the ones that reached image model)"; no session compared them per picture. Whether the added words matter is unproven: attempts with Sol-added render words settled more often (34 of 293) than those without (3 of 63), which is what dice look like, not a lever.
- **Verdict into rule.** A verdict is about one picture in one set on one day. Written as a rule it is true of that picture; the next card fails a rule not yet written (the 14 character rules of 10-14 followed the City legendaries; the hoard rule followed Scrooge; the primate rules followed the Macaque twice). The verdicts themselves moved store three times (manifest reviews until 10-12, the artifact database, the card table from 10-15), so after 10-12 his notes exist only in chat.

### 5. The base rate

1,612 pictures, 203 settles, 117 cards, 8 days: about 8 pictures and 3 rounds per card, and about 12 pictures per card over its life. A four-bet round is four pictures and one pick, so the floor of this design is 4 per card, and the first passes of 10-11 and 10-13 ran at it. A commissioned card goes sketch, colour rough, final, with revisions at each stage over weeks (Hearthstone's published process); AI game-art workflows describe batches of about 20 narrowed to 3 and a human cleanup pass on every asset. Eight pictures per card with one human pick is not a failing rate. What is unsustainable is Martin's attention per round ("I fucking wasted 5 hours today to do 20 cards"), the rounds that did not converge (69% of cards took two or more), and the agent cost of carrying the loop (2.5 GB of session transcripts, most of it art).

## Why each previous treatment had to fail

A rule written by a blind judge from a single first-sight verdict (sections 1 and 3) changes words that do not move the picture (section 2), so the next round's hit or miss is a coin either way, and either way it is read as a lesson and written down (60 commits). Research passes and findings fed the same rule-writer: `findings.md` is careful and counted, and its "best recipe" is the one that happened to be used on the easiest cards (iconic Savanna mammals, one or two pictures each) at the start. Gates were a judge that agrees with Martin at chance, which is why he saw them reject good pictures. The overnight rebuild changed the words and got the same dice. True Names, briefs and named backdrops improved the inputs the agent could see (the idea, the hero, the backdrop) and the first passes went at the floor; they could not touch the two judgments nobody can see or state.

## Alternatives that survived, ranked

1. **The image model cannot make this art reliably and nothing structural will help.** Partly true and not the break: 15 wows exist, and a 10% per-picture rate with four distinct bets gives a pick about one round in three, which is what happened. Separated by Test 2 below.
2. **Sol's rewrite is the culprit.** The channel loss is real (section 4) and untested as a cause; the within-Savanna comparison says the route did not matter. A single direct test settles it (Test 3).
3. **Martin's target is noise.** No: the wow commons are stable over three weeks and across seeing them in play. The unstable region is "legendary enough" and "photographic", and those are exactly the cards that ate the rounds.
4. **Nothing is broken; the cost is the base rate.** Half true: the per-card floor was reached on first passes. But 60 rule commits bought no measurable change, and that is the part that cost the time.

## The tests

**Test 1, run today: do the rules carry his taste to a cold agent?** Result above. The rules added 1 agreement over blind (11 against 10 of 31). Disproof would have been 19 or more.

**Test 2, one Martin sitting of about ten minutes: is the generator or the loop the drag?** Four open or weak cards. For each, eight pictures: four from the current skill with its rules and template, four from a one-line prompt (the card's True Name and habitat, the reference sheet, nothing else), all through the same route, shuffled, no labels. Martin taps "would install", "close" or "no" on each. Prediction: the rule-free four get as many "would install" as the skill's four. Disproof: the skill's pictures take 75% or more of the installs, which means the words do move the picture and section 2 is wrong.

**Test 3, no Martin time, about 20 pictures: does Sol's rewrite change what he gets?** Ten lines, each generated twice: once through Sol as now, once with the template sent verbatim to the image model through the Luna proxy. Twenty pictures on one page, pairs unlabelled, Martin marks the better of each pair. Prediction: the Sol side wins about half. Disproof: the verbatim side wins 8 or more of 10, which makes the rewrite the lever and alternative 2 the story.

**Test 4, one week later, three minutes: is a first-sight pick a verdict?** The 31 picks of Test 1 shown again, cold and shuffled against one rejected candidate each: "keep" or "swap". Prediction: at least 30% swap. Disproof: 90% or more keep, which means first sight is reliable and section 3 is wrong.

## What changing the work would take (Martin's call, not a treatment)

Stop writing rules from verdicts; keep the few constraints he stated as absolute (one animal is the hero, real animals, no human-made things, the template and sheet as they are). Make the agent's job breadth and logistics, never taste: distinct ideas per card, cards shown flat with no pick and no reasons, every picture of a round on the page. Spend the quota on more distinct bets per card in one round rather than on repaint rounds, since a repaint round costs his attention again and converges at the dice rate. Treat a pick as a draft that lives on the board for a week; a repaint needs a reason he states on the card table, and "more legendary" or "too photographic" is a reason to park the card, not to roll again. If anyone wants a judge, it has to be learned from his 1,600 recorded picks and non-picks and beat 60% on held-out picks before it filters a single picture; the agents' 30% is the bar. Track two numbers a week, pictures per settled card and rounds per card, and treat a quiet week at the floor as success.

## Research note (outside the record, 2026-10-17)

- Same-person consistency for aesthetic judgments of images: within-observer correlations around 0.67 for abstract and 0.71 for real-world images (Vessel and Rubin), median 0.60 with a range from -0.09 to 0.90 across people (Tractinsky et al.); summarised in "Beautiful secrets" (arXiv 2204.05623).
- Personal aesthetic models: a pretrained aesthetic model personalised with 5 to 15 of a user's ratings (PAMELA, arXiv 2604.07427); from scratch, about 137 ratings per rater in FLICKR-AES (Ren et al., ICCV 2017). Martin has about 1,600 recorded picks and non-picks in the manifest.
- Commissioned card art: sketch, colour rough, final, revisions at each stage, from a written brief, by an external artist (Hearthstone wiki, Ben Thompson interviews). AI game-art workflows: generate about 20 variants, keep 3, reuse as references; a human cleanup pass on every asset (Relish Games, RocketBrush).
- The Codex image skill's prompting guide (`~/.codex/skills/.system/imagegen/references/prompting.md`) tells Sol to normalise every request into a labelled spec (scene, subject, details, constraints, output intent) and to add detail when a prompt is "generic". That is the rewrite measured in section 4.

## Test 1 record

Sample: 31 manifest reviews with a recorded pick among 3 or 4 shown candidates whose files exist in `cards/bar/r1/` (seed 7 of 31 eligible), candidates shuffled per question. Agents read `GRADER_BRIEF.md` (card name, rarity, habitat, text, True Name; pick the one Martin picked) and the images at 480x720.

| Card | Martin | Sonnet blind | Opus + rules | Sonnet + rules |
|---|---|---|---|---|
| boar | 3 | 2 | 2 | 2 |
| rhinoceros | 1 | 3 | 2 | 3 |
| octopus_legend | 3 | 2 | 1 | 3 |
| vesper | 1 | 4 | 1 | 1 |
| moose | 1 | 3 | 1 | 3 |
| tortoise | 1 | 2 | 2 | 4 |
| honey_badger | 3 | 3 | 3 | 1 |
| whale_shark | 2 | 2 | 4 | 4 |
| egg_eater | 2 | 2 | 3 | 3 |
| remora | 1 | 4 | 2 | 1 |
| hippopotamus | 3 | 3 | 2 | 3 |
| swordfish | 3 | 2 | 4 | 4 |
| blue_whale | 3 | 3 | 1 | 1 |
| termite_queen | 3 | 1 | 4 | 1 |
| orca | 4 | 4 | 4 | 4 |
| mahi_mahi | 2 | 3 | 1 | 2 |
| sirocco | 1 | 3 | 4 | 3 |
| skunk | 4 | 1 | 4 | 2 |
| giraffe | 2 | 2 | 3 | 3 |
| manta_ray | 1 | 3 | 3 | 3 |
| fathom | 3 | 3 | 4 | 3 |
| tuna_legend | 1 | 3 | 4 | 3 |
| cod | 4 | 2 | 2 | 2 |
| hyena | 2 | 2 | 2 | 2 |
| manta_ray_legend | 1 | 3 | 1 | 4 |
| dung_beetle | 3 | 4 | 2 | 2 |
| oxpecker | 2 | 3 | 2 | 2 |
| jellyfish | 4 | 1 | 1 | 1 |
| mackerel | 1 | 2 | 3 | 1 |
| gazelle | 3 | 3 | 3 | 3 |
| methuselah | 2 | 1 | 1 | 3 |

## Timeline of treatments, counted

| When | Treatment | Assumption | What the numbers did |
|---|---|---|---|
| 09-25 to 09-26 | Art-direction doc from Martin's brief; after batch 1: figure/ground contrast, no template pose, each card in its own habitat, references carry only the hand | writing the principle fixes the next batch | 09-26: "bro I think I just wasted 12 eur, this is fucking garbage"; "I want us to create our own [style]" |
| 09-28 to 09-30 | "The animal is the hero"; myth in the animal (canine legendaries); count the legs (Cairn); rodent group repaint; per-card prompts through Sol with five references | each lesson into the doc | the early era: 361 template-era pictures, 62 still live; most of Martin's wows date from here, at one to three pictures each |
| 10-04 | Gut grade of 106 cards; Claude's blind bar; `art-principles.md` as single source of truth with good/bad sheets; per-card prompt and labelled references, "three phrasings by three rolls"; `edit.sh`, `calmbg.py`, `selsat.py` | a written bar plus surface edits | 417 pictures that day; Aurum, Lobo, Falstaff, Gale, Cairn locked; Borealis back to its original; Raksha restarted |
| 10-05 | Habitat sections; supernormal defined | - | Brutus, Black Swan locked |
| 10-09 | "Why two pipelines?" Research, skill spec, True Names agreed in chat, Luna verbatim proxy (Sol's silent rewrite found), manifest, review page, Sonnet gates, four ideas one picture each, no pre-selected pick; gates removed the same evening | a self-improving skill | 405 pictures, 18 settles (22.5 per settle); 13 commons settled; "stop pre-selecting one for me" |
| 10-10 00:37 to 01:04 | Rares seen beside commons | - | "repainted photography", "WHAT THE ACTUAL FUCK IS THIS", "we're fucking WALKING BACKWARDS", "I fucking wasted 5 hours today to do 20 cards" |
| 10-10 night | Overnight rebuild: research over 1,857 images, "the proven early template", Sol restored, swatch / swatch+ref / none / layout / thumbnail-sheet arms, photography prompt rules (lens blur, camera light, mono hue, then "one hue is fine") | the best recipe is in the data | 252 pictures, 29 settles; 11:09 "You tried to be too clever for your own good"; 11:30 "the harder I try, the worse the final outcome is"; 14:32 "how do we stop slipping into the yo-yo pattern of overcorrection??" |
| 10-10 evening | Four bets per card from Martin's voice notes; Sol owns translation; small batches | breadth plus his eye | Jungle first pass; 17:17 "10-20% progress after 10 hours of work... it claims to have 'found the problem'" |
| 10-11 | Named backdrops, two layers, real corners, photo pose skeletons; "Martin judges anatomy, the session shows every picture"; habitat-by-habitat order | - | 236 pictures, 61 settles (3.9 per settle, the floor): Savanna and Jungle second pass, Ocean first pass; Mocha parked after four rounds |
| 10-12 | Legendary template from Leo's prompt, then back to one template the same day; pair template; scale template; "bets differ by idea, every line has a hook" | the legendary feeling is a clause | 159 pictures, 13 settles; Squirrel legendary 9 rounds, Scrooge rounds 18 to 20; "did you actually read the card effect?"; "fifth round... something is wrong on a fundamental level" |
| 10-13 | Meadow first pass; City as "nature inside the city"; two-value contrast rule; hoard rule | - | 187 pictures, 31 settles |
| 10-14 | Five character rules in one day (an animal never a character; babies; the legend stays; phenomenon must be known real; a legendary is a moment never a portrait); Greywhisker rounds to 15 | the humanised look is a prompt word | 115 pictures, 26 settles; Greywhisker picked after 46 pictures; "read the fucking card effect and strength" |
| 10-15 | Aristo-1: 32 pictures "all too sharp and photorealistic"; ten diag rounds; gouache template; verdicts moved to the card table | a lever exists for the finish | 71 pictures, 1 settle; findings section 6: no lever moved it; "maybe I'm just being completely delusional and the art is fine" |
| 10-16 | Four distinct ideas re-demanded ("for the love of fucking god"); primates on all fours, then hands-and-gaze; Tiger back to the 09-26 crouch; "We're done with art for now" | - | 181 pictures, 24 settles (7.5 per settle, where 10-09 started at 22.5 and 10-11 reached 3.9) |

Per-arm settle rates from the manifest: template 76 of 654, sol-rewrite 58 of 217, edit 32 of 91, early-template 4 of 7, raw 2 of 11, pair-cut 2 of 32; paint, none, swatch, swatch+ref, sheet, reverse, short, detailed, model-chooses, keep-line+rules, combine, paint-v2: 0 of 150 together. Attempts per card by rarity: common 12.1, rare 9.6, legendary 12.1; rounds per card: common 2.9, rare 2.5, legendary 3.6.

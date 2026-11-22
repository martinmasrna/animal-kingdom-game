# The creature builder (an idea, not started)

A tool in which Martin builds the game's creatures himself by picking parts and moving sliders, as Spore's creature creator did, instead of describing them in words to an image model. Raised in a brainstorm on 2026-11-22 and parked the same day (Martin: "I don't think there's much point in doing it right now ... we'll come to it later at some point"). Nothing is built. His thinking on the world and the art that this serves is in [`design.md`](design.md), "The world and the art".

## Why he wants it

His words, 2026-11-22: "you creating like a custom tool where you hand me a few knobs to turn is like the best workflow we've had so far"; of Spore's creator, "I don't have to actually paint. I don't have to actually like model. I just click around and slide some ... sliders ... if you give me tools like that, I'm able to like actually be pretty creative"; of generated art, "the insane transfer of information that had to happen ... me giving instructions in like English language" and "I'm always going to have that feeling that we're producing like AI slop"; and of what the tool is for beyond art, "it's probably much easier to build the world when you're actually building it, rather than just thinking about it in your head and then trying to put it into words". His doubt: "is this actually going to be possible to build something that's going to be even like remotely useful? ... to me it just sounds like unfeasible project".

## How it would work (Claude's proposal, 2026-11-22)

- **A creature is a recipe, not a picture:** a list of parts (this body, this head, these limbs), each with its slider values, and a palette. The tool draws the creature from the recipe, live.
- **Parts attach at sockets.** A body has places where a head, limbs, a tail or wings go; a picked part snaps on.
- **Each part has its own sliders:** size, length, thickness, bend, position, angle, how many. His "turn it up to the maximum" (monkeys with six arms, a shark that is all mouth) is literal: a count from two to six, a mouth dragged until it is most of the animal.
- **Flat, layered art, not 3D:** a paper cut-out puppet, which is what stands on the tilted board today.
- **One recipe gives everything:** the full-body figure for the board, a crop of the same figure for the card, and movement cheaply, since the parts are already separate (breathing, blinking, a bounce).
- **Shared parts are the world's generator made visible:** creatures built from one library in one style belong together, and families come out of shared anatomy.

## What is likely and what is not known

- **Likely buildable:** the tool itself (sliders, sockets, saving, exporting to the game). The same kind of work as the rim tool and the card tuning tool (`design/screen/square/card/tune/`), larger.
- **The parts are the real risk.** The tool cannot look better than its library: perhaps a hundred parts in one consistent style (one line weight, one light, one level of detail). That is the old art problem, done once and judged side by side as a set instead of once per creature.
- **The joins.** A head has to sit on a body with no visible seam. Styles with clearly separate segments hide this; Rayman has no arms or legs, only floating hands and feet, for this reason.
- **Sameness,** the ceiling Martin named in Spore. More base bodies and freer sliders raise it, and the library can grow whenever a part is missing. The research found Spore's sameness documented in play (parts carried fixed stats unrelated to shape), not in looks: [`research/world-generators.md`](research/world-generators.md).
- **Charm** cannot be known before a few creatures are made in it.

## The fallback that makes it worth trying

Even if the builder's own output is not good enough to ship, a creature built in it is an exact brief: "paint this creature" from a picture is a far better instruction to an artist or an image model than a paragraph of English. So the worst case still removes the bottleneck he described, and it is still a way to build the world by making things.

## How to start, when it is taken up

1. **Grey box first,** as the card was done: no painted parts, only plain shapes for a few bodies, heads, eyes and limbs, all on sliders. It answers the cheapest question: do creatures built by sliding have a silhouette and character he likes? If not, little is lost.
2. **Then the parts:** painted to one template, judged as a set.
3. **A second, separate experiment** proposed the same day: take one creature through AI 3D generation onto the tilted board, to see the real quality and cost of 3D models before deciding for or against them. Claude's position then: stay at flat figures standing in 3D space (what the game has), because 3D models make every card change expensive while cards still change daily, need a different renderer than the web page the client is, and AI 3D is uneven at rigging and animation; that last point may be out of date and needs the test.
4. **A rule to settle with it:** every creature is drawn full body, standing, and the card shows a crop of the same figure, so that no creature is a head floating on a tile.

One question was left open for Martin: whether the world starts from individual creatures, as Pokémon does, or from a few factions the creatures belong to, as League and Warcraft do.

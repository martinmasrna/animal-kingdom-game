INTRO = """# Puzzle set 1 (2026-11-05)

The first puzzles: two from the mined den captures (`knowledge/audit/forced-captures-2026-11-05.md`), twenty composed
by hand around one idea each, where the obvious move walks past the idea, and (phase 7) more, ten at a time; most of
phase 7's one-turn puzzles were found by a search over open boards with the idea's card in hand and then picked by
hand for an idea the obvious move misses. Every file passes
`tools/puzzles/solve.py check`: a legal position with no chance in it, the den forced against every defence, one winning
first turn (The herd has two, the same idea either way round). The boards read with the solver's den (A, "+") at the bottom and the defender's (B, "-") at the top, strength
after each name, a stack bottom to top. "Free" marks a placement a Roar gave. The defence's reply is the one the server
plays: the one that leaves the solver the fewest ways to finish.
"""
NOTES = {
 'river_horse': dict(difficulty=1, obvious="Rabbit first, onto 4,1, so its Bunny can step up: the Bunny lands on 5,1 beside the Hippo, which removes it, and the den is out of reach."),
 'shell_game': dict(difficulty=1, obvious="The Lion, the strongest card, onto the Hedgehog: the Spikes remove it, and the second cover leaves no action for the den."),
 'down_the_hole': dict(difficulty=2, obvious="Lion onto the Hamster, Lion onto 5,1: the den front is yours with no action left."),
 'the_pack': dict(difficulty=2, obvious="Look for a card that covers the Mouse: neither the Pup nor the Squirrel can, and the Squirrel at 4,1 or 4,3 goes nowhere."),
 'buried': dict(difficulty=2, obvious="The Black Mamba, the removal card: it can't touch a Grizzly (8), and the Lion can't cover one."),
 'the_whale_road': dict(difficulty=2, obvious="The Sloth onto the Oxpecker, the cheap cover: then only the Crocodile is left, and an Apex Predator can't take a den. (The player in the game spent both actions on the Titan Blue Whale.)"),
 'empty_handed': dict(difficulty=3, obvious="Nothing in hand, so draw: the deck is empty. Or roam the Elephant: it is cut off, so it can't take the den."),
 'thorns': dict(difficulty=3, obvious="The Cheetah onto the Hedgehog, the one den-front animal it can cover: the Spikes remove it. And with the Skunk on your own Lion at 4,2 (to send the Grizzly home), the Stick Insect covers the Skunk and cuts the chain."),
 'dam': dict(difficulty=3, obvious="Beaver into the chain at 3,2, the Lion to 4,2: the Cheetah covers the Beaver, which both cuts the chain and stops its timer. Two Lions straight up the lane: the Cheetah blocks 5,2 and only Pups are left to cover it."),
 'hunger': dict(difficulty=3, obvious="Both Lions now, one to 4,2 and one onto it or nearby: the Elephant can't be covered this turn anyway, and next turn there is only a Pup to cover what guards the den."),
 'first_in_line': dict(difficulty=2, obvious="The Lion straight to 4,2: the Boar beside it removes it."),
 'ink': dict(difficulty=4, obvious="The Mouse to 4,2: the Hippos remove it. The Octopus to 4,2 and stop there: the Hippos still remove the Octopus, so 4,2 is empty again and the den is three steps away."),
 'slow_poison': dict(difficulty=3, obvious="A Lion to 4,2 and the other onto the Toad: at the start of the defender's turn the poison removes that Lion, the Toad is back, and only a Pup is left."),
 'stripes': dict(difficulty=4, obvious="A Lion onto the Zebra: it flees and sends the Lion back to your hand, the gate is open, and the Zebra comes back next turn. Mamba first but on your own Lion with the Lion spent: the Cheetah covers the Mamba and nothing is left to answer it."),
 'shock': dict(difficulty=4, obvious="The Lion to 4,1 and the Grizzly to 5,1: the den is one step away, but the defender's Grizzly walks onto 1,3 and its Mouse into your den. Blocking 1,3 instead leaves you one step short."),
 'two_doors': dict(difficulty=3, obvious="Straight up the middle, a Lion to 4,2 and one to 5,2: the Grizzly covers the Lion at 5,2 and the other lane is two steps behind."),
 'bite': dict(difficulty=4, obvious="The Lion onto the Pup at 4,2, the natural cover: the Pup at 5,2 can then only be covered by something stronger than 1, and nothing is left but Pups."),
 'stepping_stone': dict(difficulty=5, obvious="Roam the Wolf through its pack to 4,2 at once and keep both Pups: next turn the Wolf must roam on to cover the Bobcat at 5,2, and the crossroad it leaves is empty, so it stands cut off at the den."),
 'head_on': dict(difficulty=3, obvious="The Squirrel or the Pup to 5,1 after the Lion: the Pigeon covers anything weaker than 5. Or anything placed beside the Boar first: it is removed."),
 'deep_water': dict(difficulty=4, obvious="The Krill at 4,2 and the Sperm Whale on top of it: the Whale's Roar also removes your own Lion at 3,2, and the Whale stands cut off."),
 'short_circuit': dict(difficulty=4, obvious="A Lion onto the Mouse and a Lion to 4,1: the den is safe this turn, but with two actions the defender's Cheetah steps onto 1,2 and its Mouse runs back into 1,3 or the den; and racing at once lets the Mouse take your den first."),
 'the_herd': dict(difficulty=3, obvious="The two Wildebeest up the lane, keeping the Buffalo: the defender's Lion covers the one at 3,2 and cuts the herd off."),
 'two_of_a_kind': dict(difficulty=2, obvious="The Lion onto the Bobcat and the Bobcat to 5,2: the den front is yours with no action left for the den."),
 'hunting_dogs': dict(difficulty=3, obvious="A Wolf to 4,2 and a Wolf onto the Hedgehog: the Spikes remove the second Wolf."),
 'fetch': dict(difficulty=4, obvious="The Cheetah onto the Toad and the Squirrel to 5,3: the den front is yours, but both actions are spent."),
 'nest': dict(difficulty=5, obvious="The Cuckoo straight onto the Hedgehog: its Roar finds nothing of strength 4 or less beside it, and the Spikes remove it."),
 'side_step': dict(difficulty=3, obvious="The Wolf onto the Zebra beside it: the Zebra flees and sends the Wolf back to your hand."),
 'leapfrog': dict(difficulty=4, obvious="The Bobcat or the Impala straight to the den front: the Armadillo at 5,2 is too strong for both, and the Boar removes the first animal placed beside it."),
 'undermined': dict(difficulty=4, obvious="The Lion onto the Hamster from 4,2: the Lion can't reach 5,2 without a link at 4,2, and two actions don't cover the link, the Hamster and the den."),
 'called_up': dict(difficulty=4, obvious="The Cheetah from your hand onto the Toad: it can't get there, lane 1 stops at 3,1; and the Coyote on its own only moves a Cheetah that is already near."),
 'talons': dict(difficulty=1, obvious="The Mouse first: it can't cover the Orb-Weaver (5), and the den needs the den front."),
 'small_horns': dict(difficulty=1, obvious="The Squirrel beside the Hippopotamus: the Hippo removes anything of strength 4 or less placed next to it."),
}

# 38 Costed tricks

Every number here is a placeholder.

**The question.** When trick-taking cards cost energy by rank and each trick's prize is shown in advance, do choosing which tricks to buy and following suit give a real decision?

## Setup

- Four suits, A to D, ranks 1 to 6. Each player's deck holds one card of every suit and rank: 24 cards.
- Cost by rank: ranks 1–2 cost 0, ranks 3–4 cost 1, rank 5 costs 2, rank 6 costs 3.
- Points start at 0. Target: 20.

## A hand

1. Each player shuffles its own deck and deals itself 8 cards. Energy 10 each for the hand; unspent energy is lost when the hand ends.
2. Trump suit: A in hand 1, B in hand 2, then C, D, A and so on.
3. The prize row: eight prizes, 1, 1, 1, 2, 2, 2, 3, 3, shuffled and laid face-up in order. Trick 1 is worth the first prize, trick 2 the second, and so on.
4. Eight tricks. The first leader of a hand alternates from hand to hand; after that, each trick's winner leads.

## A trick

- The leader plays a card face-up, paying its cost, or any card face-down for free.
- The follower: if it holds a card of the led suit it can pay for, it must play one of those; otherwise it plays any card it can pay for, or any card face-down for free.
- A face-down card has no suit and no rank and never wins, except that two face-down cards give the trick to the leader. After a face-down lead, any face-up card from the follower wins.
- Otherwise the highest trump wins; with no trump, the highest card of the led suit.
- The winner scores the trick's prize.

## End

At the end of a hand, a player on 20 or more wins; both on 20 or more: the higher wins, equal plays another hand. After 5 hands, the higher score wins; equal is a draw.

## Builder notes

- Hidden information: the Expert determinizes the opponent's hand from the cards not yet seen and never reads it.
- Greedy: wins a trick worth 2 or more with its cheapest winning card it can pay for; otherwise plays face-down, or its cheapest legal card when it must follow.
- The first-player check reads the first leader of hand 1.
- Set positions: free trick (the opponent led face-down: win with a free face-up card); don't overpay (two cards would win the trick: play the cheaper); lethal (on 18 points, the last trick of the hand is worth 2: win it).

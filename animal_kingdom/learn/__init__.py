"""Learned-pilot training: self-play TD(lambda) that fits `bots.learned_eval.LinearEval`
weights (see `docs/bots/learned-pilot-handoff.md` and the Session-1 plan).

Numpy-lazy: `bots/` and `engine/`
stay stdlib-only; only this package's training math imports numpy, and only inside function
bodies, so a core-only install never needs it.
"""

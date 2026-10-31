"""The cards shown beside a card when it is read large (`related` in cards.json: what its effect makes, brings or becomes)
match its text, so the collection never shows a token twice, a wrong one, or none (Martin, 2026-10-31: the Queen Ant
showed her Young Ant twice; the Bush Dog's Pup was shown nowhere)."""

import json
import re
from pathlib import Path

MAKES = re.compile(r"\b(place|play|add|put|turn into)\b", re.I)
CARDS = Path(__file__).resolve().parents[1] / "data" / "cards.json"


def _cards():
    return {c["id"]: c for c in json.loads(CARDS.read_text(encoding="utf-8"))["cards"] if c.get("status") != "planned"}


def _names(cards):
    """Card name -> ids (two cards may share a name: the common Butterfly and the legendary line's Butterfly)."""
    out = {}
    for cid, c in cards.items():
        n = c.get("name")
        if n and not c.get("unnamed") and not n.startswith("["):
            out.setdefault(n, []).append(cid)
    return out


def _named_in(text, names, skip):
    """The card names a text names as whole words (plural allowed), longest first so "Roach King" is not also "Roach"."""
    found = []
    if skip:   # the card's own name is blanked first, so Roach King's text does not name the Roach
        text = re.sub(r"\b" + re.escape(skip) + r"s?\b", " ", text)
    for n in sorted(names, key=len, reverse=True):
        if n == skip:
            continue
        if re.search(r"\b" + re.escape(n) + r"s?\b", text):
            found.append(n)
            text = re.sub(r"\b" + re.escape(n) + r"s?\b", " ", text)
    return found


def test_related_lists_are_clean():
    cards = _cards()
    for cid, c in cards.items():
        rel = c.get("related", [])
        assert len(rel) == len(set(rel)), f"{cid} shows a card twice: {rel}"
        for r in rel:
            assert r in cards, f"{cid} shows {r}, which is no card"


def test_every_token_has_a_maker():
    cards = _cards()
    made = {r for c in cards.values() for r in c.get("related", [])}
    orphans = [cid for cid, c in cards.items() if c.get("status") == "token" and cid not in made]
    assert not orphans, f"tokens no card shows: {orphans}"


def test_a_card_shows_what_its_text_makes():
    """"place a Pup", "add 2 Kittens", "play Princess Lea", "turn into a Butterfly": the named card is shown beside it."""
    cards, names = _cards(), _names(_cards())
    problems = []
    for cid, c in cards.items():
        text = c.get("text") or ""
        if not MAKES.search(text):
            continue
        rel = set(c.get("related", []))
        for n in _named_in(text, names, c.get("name")):
            sentence = next((s for s in re.split(r"(?<=[.!])\s+", text) if re.search(r"\b" + re.escape(n) + r"s?\b", s)), text)
            if MAKES.search(sentence) and not rel & set(names[n]):
                problems.append(f"{cid}: text makes {n!r} but shows none of {names[n]}")
    assert not problems, "\n".join(problems)


def test_a_card_shows_nothing_its_text_does_not_make():
    """A shown card is named in the text, or named by a shown card's own text (the Fawn's line: Young Stag, then Great
    Stag), or the card evolves into it, or the text says 'random' (the Stork's younglings)."""
    cards = _cards()
    problems = []
    for cid, c in cards.items():
        text = c.get("text") or ""
        if c.get("evolves") or "random" in text:
            continue
        rel = c.get("related", [])
        chain = text + " " + " ".join(cards[r].get("text") or "" for r in rel if r in cards)
        for r in rel:
            rn = cards.get(r, {}).get("name", "")
            if rn and not rn.startswith("[") and not re.search(r"\b" + re.escape(rn) + r"s?\b", chain):
                problems.append(f"{cid}: shows {r} ({rn}), which its text never makes")
    assert not problems, "\n".join(problems)

"""What the parity tools share: the two engines built from the same data, and the comparison of two positions."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))   # this tree, not an installed copy
import dataclasses, json

from animal_kingdom.engine import effects, rules
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.resources import load_bundled_json
from animal_kingdom.engine.state import MAP_ID
import ak_engine

RAW_CARDS = load_bundled_json("cards.json")
MAPS_JSON = json.dumps(load_bundled_json("maps.json"))


def engines(raw_cards=None, config=None, map_id=MAP_ID):
    """(the Python card table, the Config, the Rust Engine) for one card table and one config."""
    raw_cards = raw_cards or RAW_CARDS
    config = config or Config()
    return load_cards(raw_cards), config, ak_engine.Engine(json.dumps(raw_cards), MAPS_JSON, json.dumps(dataclasses.asdict(config)), map_id)


def canon(d):
    return json.dumps(d, sort_keys=True, default=list)


def diff_keys(a, b, path=""):
    """Where two JSON-shaped values differ, as a short list of paths with both sides."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append((f"{path}.{k}", a.get(k, "<missing>"), b.get(k, "<missing>")))
            else:
                out.extend(diff_keys(a[k], b[k], f"{path}.{k}"))
    elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            out.append((f"{path}[len]", len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(diff_keys(x, y, f"{path}[{i}]"))
    elif a != b:
        out.append((path, a, b))
    return out[:12]


def compare(py, rs, label, events=True, stats=None):
    """None when the Python position `py` and the Rust position `rs` agree on everything a player or a bot can read:
    the saved position (the board's tiles in the order they were taken), the legal actions in order, whether the turn
    may end, the result, the events since the last comparison, and each seat's mana, costs and income. Else what
    differs. `stats`: a Counter that takes what the position exercised."""
    a, b = py.to_dict(), rs.to_dict()
    if stats is not None:
        stats["positions"] += 1
        if a["pending"]:
            stats["choice: " + a["effect_stack"][-1]["op"]] += 1
        if a["scheduled"]:
            stats["positions with a Poison timer"] += 1
        if any(len(st) > 1 for st in a["board"].values()):
            stats["positions with a covered animal still on the board"] += 1
        for e in py.events:
            stats["event: " + e["e"] + (" from hand" if e.get("zone") else "")] += 1
    if canon(a) != canon(b):
        return f"state differs after {label}: " + "; ".join(f"{p}: py={x!r} rs={y!r}" for p, x, y in diff_keys(a, b))
    if list(a["board"]) != list(b["board"]):
        return f"board order differs after {label}: py={list(a['board'])} rs={list(b['board'])}"
    la, lb = [x.to_dict() for x in rules.legal_actions(py)], rs.legal_actions()
    if [canon(x) for x in la] != [canon(x) for x in lb]:
        sa, sb = {canon(x) for x in la}, {canon(x) for x in lb}
        if sa == sb:
            return f"legal action ORDER differs after {label}: py={la[:6]} rs={lb[:6]}"
        return f"legal actions differ after {label}: only py={[json.loads(x) for x in sorted(sa - sb)][:5]} only rs={[json.loads(x) for x in sorted(sb - sa)][:5]}"
    if rules.can_pass(py) != rs.can_pass():
        return f"can_pass differs after {label}: py={rules.can_pass(py)} rs={rs.can_pass()}"
    ta = rules.is_terminal(py)
    ta, tb = (ta.to_dict() if ta else None), rs.is_terminal()
    if canon(ta) != canon(tb):
        return f"terminal differs after {label}: py={ta} rs={tb}"
    if py.player_to_act() != rs.player_to_act():
        return f"player to act differs after {label}"
    if events:
        ea, eb = list(py.events), rs.take_events()
        py.events.clear()
        if [canon(x) for x in ea] != [canon(x) for x in eb]:
            return f"events differ after {label}: " + "; ".join(f"{p}: py={x!r} rs={y!r}" for p, x, y in diff_keys(ea, eb))
    for p in "AB":
        seen = {"mana_left": (rules.mana_left(py, p), rs.mana_left(p)), "mana_total": (rules.mana_total(py, p), rs.mana_total(p)),
                "power_cost": (effects.power_cost(py, p), rs.power_cost(p)), "leader_usable": (effects.leader_usable(py, p), rs.leader_usable(p)),
                "region_income": (rules.region_income(py, p), rs.region_income(p))}
        for u in py.hands[p]:
            seen[f"mana_cost {u.card_id}"] = (effects.mana_cost(py, u.card_id, p), rs.mana_cost(u.card_id, p))
            seen[f"strength {u.iid}"] = (effects.effective_strength(py, u), rs.effective_strength(u.iid))
        for k, (x, y) in seen.items():
            if x != y:
                return f"{k} of {p} differs after {label}: py={x} rs={y}"
    for stack in py.board.values():
        for u in stack:
            x, y = effects.effective_strength(py, u), rs.effective_strength(u.iid)
            if x != y:
                return f"strength of {u.card_id} ({u.iid}) differs after {label}: py={x} rs={y}"
    return None

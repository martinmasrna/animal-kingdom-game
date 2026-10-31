"""A card offered out of the deck (the Owl's Scout) is shown at the strength it would be drawn with: the royal jelly's +2
included, and the legendary Dung Beetle in the form it has reached (Martin, 2026-10-31: "Scouting with owl should display
real-time strength")."""

from animal_kingdom.engine.strength import card_strength
from animal_kingdom.web.match import Match, Seat


def _match():
    m = Match("T", Seat("ta", "A", deck="cats"))
    m.join(Seat("tb", "B", deck="cats"))
    return m


def test_a_scouted_card_carries_the_royal_jelly():
    m = _match()
    st = m.state
    cid = st.decks["A"][-1]
    plain = m._describe_option(cid, "A")
    assert plain["kind"] == "card" and plain["id"] == cid and plain["str"] == card_strength(st, cid, "A")
    st.jelly["A"] = {cid: [1, st.config.jelly_grant]}          # the jelly reached one copy left in the deck
    jellied = m._describe_option(cid, "A")
    assert jellied["str"] == plain["str"] + st.config.jelly_grant
    assert st.jelly["A"][cid] == [1, st.config.jelly_grant]      # describing it spends nothing


def test_a_scouted_dung_beetle_is_shown_in_its_reached_form():
    m = _match()
    st = m.state
    assert m._describe_option("dung_beetle_legend", "A")["id"] == "dung_beetle_legend"
    st.hungry_eaten["A"] = st.config.dung_beetle_legend_draw_at    # its Hungry animals have eaten enough for the second form
    shown = m._describe_option("dung_beetle_legend", "A")
    assert shown["v"] == "dung_beetle_legend" and shown["id"] == "dung_beetle_legend_form2"
    assert shown["str"] == card_strength(st, "dung_beetle_legend_form2", "A")

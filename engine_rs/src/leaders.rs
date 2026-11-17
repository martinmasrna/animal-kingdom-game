//! Leaders (the leaders prototype, engine/leaders.py and the Leaders section of engine/effects.py): a deck's leader on
//! its player's den, with a hero power, a once-per-game power or a passive. The passives hook in where they act
//! (effects.rs gain_food, fire_remove_event, start_of_turn, end_of_turn, do_placement; strength.rs).

use crate::data::*;
use crate::effects::{card_v, control_tag_count, matches, pn};
use crate::state::{Leader, State, Unit};
use crate::value::Value;
use crate::vmap;

pub const ADIRA: &str = "lion_legend_4";
pub const JULIETTE: &str = "bee_legend_2";
pub const BUMBLETON: &str = "bumblebee_legend";
pub const MELISSIA: &str = "bee_legend";
pub const SOLENIA: &str = "army_ant_legend";
pub const BABAJI: &str = "baboon_legend";
pub const XANTHE: &str = "butterfly_legend";
pub const ARNE: &str = "eagle_legend";
pub const GORILLA: &str = "gorilla_legend_2";
pub const GRIMM: &str = "raven_legend";
pub const MELISSIA_SPEC: &str = "tag:Colony&tag:Worker|tag:Colony&tag:Soldier|tag:Colony&tag:Nurse";
pub const XANTHE_LAST_STAGE: i32 = 4;

/// "power", "once" or "passive"; None: not a leader.
pub fn kind_of(id: &str) -> Option<&'static str> {
    match id {
        ADIRA | GRIMM | MELISSIA | BABAJI => Some("power"),
        XANTHE => Some("once"),
        JULIETTE | BUMBLETON | SOLENIA | ARNE | GORILLA => Some("passive"),
        _ => None,
    }
}

/// new_game's leaders (state.py): each must be a leader and in its deck.
pub fn set_leaders(st: &mut State, ids: [Option<&str>; 2]) -> Result<(), String> {
    for p in 0..2 {
        let Some(name) = ids[p] else { continue };
        if kind_of(name).is_none() {
            return Err(format!("'{name}' is not a leader"));
        }
        let id = st.card_id(name).ok_or_else(|| format!("unknown card {name:?}"))?;
        if !st.decks[p].contains(&id) && !st.hands[p].iter().any(|u| u.card == id) {
            return Err(format!("the leader '{name}' must be in its deck"));
        }
        st.leaders[p] = Some(Leader { id, kills: 0, stage: 0, spent: false });
    }
    Ok(())
}

#[inline]
pub fn leader_name(st: &State, p: Player) -> Option<&'static str> {
    if p > B {
        return None;
    }
    st.leaders[p as usize].map(|l| st.cname(l.id))
}

#[inline]
pub fn leads(st: &State, p: Player, id: &str) -> bool {
    leader_name(st, p) == Some(id)
}

pub fn any(st: &State) -> bool {
    st.leaders[0].is_some() || st.leaders[1].is_some()
}

/// Lady Juliette's leader: +1 to every animal of `owner`'s with a small starting deck (strength.py leader_bonus).
pub fn leader_bonus(st: &State, owner: Player) -> i32 {
    if !leads(st, owner, JULIETTE) || st.starting_decks[owner as usize].is_empty() {
        return 0;
    }
    if crate::strength::small_starting_deck(st, owner, CardId::MAX) {
        st.cfg().int("juliette_leader_bonus")
    } else {
        0
    }
}

/// strength.py hand_counter: Arne's leader shares the strongest copy's counter among copies in hand.
pub fn hand_counter(st: &State, inst: &Unit) -> i32 {
    let own = inst.strength_counter as i32;
    if !leads(st, inst.owner, ARNE) {
        return own;
    }
    st.hands[inst.owner as usize].iter().filter(|u| u.card == inst.card).map(|u| u.strength_counter as i32).fold(own, i32::max)
}

/// strength.py play_adjustment: [GORILLA]'s Roar (exactly his strength) and his leader (+1 on the turn's first play).
pub fn play_adjustment(st: &State, inst: &Unit) -> smallvec::SmallVec<[i32; 2]> {
    let mut out = smallvec::SmallVec::new();
    let owner = inst.owner;
    if owner > B {
        return out;
    }
    if let Some(n) = st.next_strength[owner as usize] {
        out.push(n - (crate::strength::card_strength(st, inst.card, owner) + hand_counter(st, inst)));
    }
    if leads(st, owner, GORILLA) && st.turn_flags.played[owner as usize].is_empty() {
        out.push(st.cfg().int("gorilla_leader_bonus"));
    }
    out
}

/// effects.py _settle_play_strength: what the play adds becomes the animal's counter (it keeps it on the board).
pub fn settle_play_strength(st: &mut State, player: Player, unit: &mut Unit) {
    let shared = hand_counter(st, unit);
    if shared != unit.strength_counter as i32 {
        let arne = st.card_id(ARNE);
        st.note_strength(unit.iid, shared - unit.strength_counter as i32, arne, false);
        unit.strength_counter = shared as i16;
    }
    let gorilla = st.card_id(GORILLA);
    for n in play_adjustment(st, unit) {
        if n != 0 {
            unit.strength_counter += n as i16;
            st.note_strength(unit.iid, n, gorilla, false);
        }
    }
    st.next_strength[player as usize] = None;
}

/// effects.py leader_draws: Queen Adira's and Grimm's powers.
pub fn leader_draws(st: &State, l: &Leader) -> i32 {
    let (base, per) = if st.cname(l.id) == GRIMM { ("grimm_leader_draw", "grimm_leader_per") } else { ("adira_leader_draw", "adira_leader_per") };
    st.cfg().int(base) + l.kills / st.cfg().int(per)
}

/// effects.py leader_usable.
pub fn usable(st: &State, player: Player) -> bool {
    if player > B {
        return false;
    }
    let Some(l) = st.leaders[player as usize] else { return false };
    let p = player as usize;
    match st.cname(l.id) {
        ADIRA | GRIMM | BABAJI => !st.decks[p].is_empty(),
        MELISSIA => st.decks[p].iter().any(|&c| matches(st, c, MELISSIA_SPEC)),
        XANTHE => {
            if l.spent {
                return false;
            }
            match l.stage {
                1 => !st.decks[p].is_empty(),
                3 | 4 => !st.decks[p].is_empty() || !st.hands[p].is_empty(),
                _ => false,
            }
        }
        _ => false,
    }
}

/// effects.py do_leader: the player presses their den (the action is paid).
pub fn do_leader(st: &mut State, player: Player) -> Result<(), String> {
    let p = player as usize;
    let Some(l) = st.leaders[p] else { return Err(format!("{} has no leader", player_name(player))) };
    let lid = st.cname(l.id);
    crate::emit!(st, "leader_power", vmap!("player" => pn(player), "card" => card_v(st, l.id)));
    let src = card_v(st, l.id);
    match lid {
        ADIRA | GRIMM => {
            let n = leader_draws(st, &l);
            st.effect_stack.push(vmap!("op" => Value::s("draw"), "player" => pn(player), "n" => Value::Int(n as i64), "by_card" => src));
        }
        MELISSIA => {
            st.effect_stack.push(vmap!("op" => Value::s("scout"), "player" => pn(player), "spec" => Value::s(MELISSIA_SPEC), "by_card" => src));
        }
        BABAJI => {
            let g = st.cfg().int("babaji_leader_grant");
            st.effect_stack.push(vmap!("op" => Value::s("scout"), "player" => pn(player), "spec" => Value::Null, "grant" => Value::Int(g as i64), "by_card" => src));
        }
        XANTHE => {
            st.leaders[p].as_mut().unwrap().spent = true;
            let g = st.cfg().int("xanthe_leader_grant") as i64;
            match l.stage {
                3 => st.effect_stack.push(vmap!("op" => Value::s("hand_grant_one"), "player" => pn(player), "amount" => Value::Int(g), "by_card" => src.clone())),
                4 => st.effect_stack.push(vmap!("op" => Value::s("hand_grant_all"), "player" => pn(player), "amount" => Value::Int(g), "by_card" => src.clone())),
                _ => {}
            }
            st.effect_stack.push(vmap!("op" => Value::s("draw"), "player" => pn(player), "n" => Value::Int(1), "by_card" => src));
        }
        _ => return Err(format!("'{lid}' has no power to use")),
    }
    Ok(())
}

/// effects.py _fire_remove_event: Queen Adira's leader counts an enemy her Cats removed, Grimm's every enemy removed.
/// `on_board`: the removed card was an animal on the board (Grimm counts no card discarded from a hand or deck).
pub fn count_kill(st: &mut State, owner: Player, on_board: bool, by_player: Option<Player>, by_card: Option<CardId>) {
    if let (Some(bp), Some(bc)) = (by_player, by_card) {
        if bp != owner && bp <= B && st.card(bc).has_tag(T_CAT) && leads(st, bp, ADIRA) {
            bump(st, bp);
        }
    }
    for p in [A, B] {
        if on_board && p != owner && leads(st, p, GRIMM) {
            bump(st, p);
        }
    }
}

fn bump(st: &mut State, p: Player) {
    let l = st.leaders[p as usize].as_mut().unwrap();
    l.kills += 1;
    let k = l.kills;
    crate::emit!(st, "leader", vmap!("player" => pn(p), "kills" => Value::Int(k as i64)));
}

/// effects.py start_of_turn: Xanthe's leader evolves at each of her owner's Dawns.
pub fn dawn(st: &mut State, player: Player) {
    if !leads(st, player, XANTHE) {
        return;
    }
    let l = st.leaders[player as usize].as_mut().unwrap();
    if l.stage < XANTHE_LAST_STAGE {
        l.stage += 1;
        let s = l.stage;
        crate::emit!(st, "leader", vmap!("player" => pn(player), "stage" => Value::Int(s as i64)));
    }
}

/// effects.py end_of_turn: Queen Solenia's leader, Dusk: gain 1 food for each animal you control.
pub fn dusk(st: &mut State, player: Player) {
    if !leads(st, player, SOLENIA) {
        return;
    }
    let n = st.cfg().int("solenia_leader_per") * control_tag_count(st, player, 0);
    let src = st.card_id(SOLENIA).map(|c| card_v(st, c)).unwrap_or(Value::Null);
    st.effect_stack.push(vmap!("op" => Value::s("gain_food"), "player" => pn(player), "by_card" => src, "amount" => Value::Int(n as i64)));
}

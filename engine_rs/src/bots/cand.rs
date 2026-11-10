//! The candidate network (tools/policy): a score per legal action from the position (the board_live feature vector)
//! and the action's own features, trained on which action the Expert's search took. The whole-turn search uses it to
//! choose which actions to search on at a decision, instead of applying and evaluating every one.
//!
//! The action features mirror tools/policy/extract.py `action_vec` column for column; the two must change together.

use crate::actions::{Action, Target, SKIP};
use crate::data::Player;
use crate::state::{State, Unit};
use crate::strength::{effective_strength, placement_strength};
use crate::value::Value;
use serde_json as sj;

use super::features::{extract, push_properties, BOARD_SLOTS};

const KINDS: usize = 6;
const OPT_N: usize = 8;
const EXTRA_N: usize = 8;

pub struct CandNet {
    dot: bool,                     // the score is the dot product of the two embeddings plus a bias on the action
    hidden: usize,
    pos_n: usize,
    act_n: usize,
    pos1_w: Vec<f64>, pos1_b: Vec<f64>,
    pos2_w: Vec<f64>, pos2_b: Vec<f64>,
    act1_w: Vec<f64>, act1_b: Vec<f64>,
    head1_w: Vec<f64>, head1_b: Vec<f64>,
    head2_w: Vec<f64>, head2_b: f64,
    bias_w: Vec<f64>, bias_b: f64,
}

fn mat(d: &sj::Value, key: &str) -> Result<Vec<f64>, String> {
    let rows = d.get(key).and_then(|v| v.as_array()).ok_or_else(|| format!("candidate net: missing {key}"))?;
    let mut out = Vec::new();
    for r in rows {
        match r.as_array() {
            Some(cols) => out.extend(cols.iter().map(|x| x.as_f64().unwrap_or(0.0))),
            None => out.push(r.as_f64().unwrap_or(0.0)),
        }
    }
    Ok(out)
}

/// `w` is column-major here (transposed at load: w[i * n_out + o]); each output still receives its additions in
/// ascending input order, skipping zero inputs, so the sums are bit-identical to the row-major loop.
fn linear(w: &[f64], b: &[f64], x: &[f64], n_out: usize, relu: bool) -> Vec<f64> {
    let mut out: Vec<f64> = b[..n_out].to_vec();
    for (i, &xi) in x.iter().enumerate() {
        if xi != 0.0 {
            let col = &w[i * n_out..(i + 1) * n_out];
            for (o, c) in out.iter_mut().zip(col.iter()) {
                *o += c * xi;
            }
        }
    }
    if relu {
        for o in out.iter_mut() {
            if *o < 0.0 {
                *o = 0.0;
            }
        }
    }
    out
}

fn linear_into(w: &[f64], b: &[f64], x: &[f64], out: &mut [f64]) {
    let n_out = out.len();
    out.copy_from_slice(&b[..n_out]);
    for (i, &xi) in x.iter().enumerate() {
        if xi != 0.0 {
            let col = &w[i * n_out..(i + 1) * n_out];
            for (o, c) in out.iter_mut().zip(col.iter()) {
                *o += c * xi;
            }
        }
    }
    for o in out.iter_mut() {
        if *o < 0.0 {
            *o = 0.0;
        }
    }
}

fn transpose(w: Vec<f64>, n_out: usize) -> Vec<f64> {
    if n_out == 0 || w.is_empty() { return w; }
    let n_in = w.len() / n_out;
    let mut t = vec![0.0; w.len()];
    for o in 0..n_out {
        for i in 0..n_in {
            t[i * n_out + o] = w[o * n_in + i];
        }
    }
    t
}

impl CandNet {
    pub fn load(path: &str) -> Result<CandNet, String> {
        let text = std::fs::read_to_string(path).map_err(|e| format!("candidate net {path}: {e}"))?;
        CandNet::from_json(&text).map_err(|e| format!("candidate net {path}: {e}"))
    }

    /// The network from its artifact's JSON text (the browser has no file to read: wasm.rs hands it over).
    pub fn from_json(text: &str) -> Result<CandNet, String> {
        let d: sj::Value = sj::from_str(text).map_err(|e| e.to_string())?;
        let hidden = d["hidden"].as_u64().ok_or("candidate net: hidden")? as usize;
        let pos_n = d["pos_n"].as_u64().ok_or("candidate net: pos_n")? as usize;
        let act_n = d["act_n"].as_u64().ok_or("candidate net: act_n")? as usize;
        let dot = d.get("head").and_then(|v| v.as_str()) == Some("dot");
        let (head1_w, head1_b, head2_w, head2_b, bias_w, bias_b) = if dot {
            (Vec::new(), Vec::new(), Vec::new(), 0.0, mat(&d, "bias_w")?, mat(&d, "bias_b")?[0])
        } else {
            (transpose(mat(&d, "head1_w")?, hidden), mat(&d, "head1_b")?, mat(&d, "head2_w")?, mat(&d, "head2_b")?[0], Vec::new(), 0.0)
        };
        Ok(CandNet {
            dot, hidden, pos_n, act_n,
            pos1_w: transpose(mat(&d, "pos1_w")?, hidden), pos1_b: mat(&d, "pos1_b")?,
            pos2_w: transpose(mat(&d, "pos2_w")?, hidden), pos2_b: mat(&d, "pos2_b")?,
            act1_w: transpose(mat(&d, "act1_w")?, hidden), act1_b: mat(&d, "act1_b")?,
            head1_w, head1_b, head2_w, head2_b, bias_w, bias_b,
        })
    }

    /// A score per action of `legal`, for `actor` to act in `st` (higher: likelier the search's choice).
    pub fn scores(&self, st: &State, actor: Player, legal: &[Action]) -> Vec<f64> {
        let pos = extract(st, actor, "board_live");
        debug_assert_eq!(pos.len(), self.pos_n);
        let h = linear(&self.pos1_w, &self.pos1_b, &pos, self.hidden, true);
        let p = linear(&self.pos2_w, &self.pos2_b, &h, self.hidden, true);
        let mut out = Vec::with_capacity(legal.len());
        let mut av: Vec<f64> = Vec::with_capacity(self.act_n);
        let mut q: Vec<f64> = vec![0.0; self.hidden];
        for (i, a) in legal.iter().enumerate() {
            action_vec_into(st, actor, a, i, &mut av);
            debug_assert_eq!(av.len(), self.act_n);
            linear_into(&self.act1_w, &self.act1_b, &av, &mut q);
            if self.dot {
                let mut s = self.bias_b;
                for (w, v) in self.bias_w.iter().zip(av.iter()) {
                    if *v != 0.0 {
                        s += w * v;
                    }
                }
                s += p.iter().zip(q.iter()).map(|(a, b)| a * b).sum::<f64>();
                out.push(s);
                continue;
            }
            let mut x = Vec::with_capacity(3 * self.hidden);
            x.extend_from_slice(&p);
            x.extend_from_slice(&q);
            x.extend(p.iter().zip(q.iter()).map(|(a, b)| a * b));
            let hh = linear(&self.head1_w, &self.head1_b, &x, self.hidden, true);
            let mut s = self.head2_b;
            for (w, v) in self.head2_w.iter().zip(hh.iter()) {
                s += w * v;
            }
            out.push(s);
        }
        out
    }
}

fn slot_vec(st: &State, me: Player, cr: u8, v: &mut Vec<f64>) {
    let opp = crate::data::other(me);
    let stack = &st.stacks[cr as usize];
    let n_props = 2 + crate::data::KEYWORDS.len() + crate::data::BOT_TAG_COUNT;
    if stack.is_empty() {
        v.extend(std::iter::repeat(0.0).take(7 + n_props));
        return;
    }
    let top = stack.last().unwrap();
    let sign = if top.owner == me { 1.0 } else if top.owner == opp { -1.0 } else { 0.0 };
    v.push(if top.owner == me { 1.0 } else { 0.0 });
    v.push(if top.owner == opp { 1.0 } else { 0.0 });
    v.push(sign * effective_strength(st, top, None) as f64 / 10.0);
    v.push(stack.len() as f64 / 4.0);
    let under = &stack[..stack.len() - 1];
    v.push(under.iter().filter(|u| u.owner == me).count() as f64 / 3.0);
    v.push(under.iter().filter(|u| u.owner == opp).count() as f64 / 3.0);
    v.push(sign * if top.placed_on_turn as i32 == st.turn_counter { 1.0 } else { 0.0 });
    push_properties(v, st.card(top.card), sign, true);
}

fn card_vec(st: &State, u: &Unit, strength: i32, v: &mut Vec<f64>) {
    let card = st.card(u.card);
    v.push(1.0);
    v.push(strength as f64 / 10.0);
    v.push(card.food_cost as f64 / 5.0);
    push_properties(v, card, 1.0, false);
}

/// extract.py `action_vec`: kind, the card played or moved, the target crossroad's slot, where it is, what the
/// placement does there, and the option index of a non-crossroad choice.
pub fn action_vec(st: &State, me: Player, a: &Action, legal_index: usize) -> Vec<f64> {
    let mut out = Vec::new();
    action_vec_into(st, me, a, legal_index, &mut out);
    out
}

/// `action_vec` written into `out` (cleared first): the same columns in the same order, no temporary vectors.
pub fn action_vec_into(st: &State, me: Player, a: &Action, legal_index: usize, out: &mut Vec<f64>) {
    let gm = st.map();
    let opp = crate::data::other(me);
    let n_props = 2 + crate::data::KEYWORDS.len() + crate::data::BOT_TAG_COUNT;
    let card_n = 3 + n_props;
    let slot_n = 7 + n_props;
    out.clear();
    out.resize(KINDS, 0.0);
    let mut extra = [0.0; EXTRA_N];
    let mut opt = [0.0; OPT_N];
    let mut target: Option<u8> = None;
    let mut strength: Option<i32> = None;
    match a {
        Action::Place { card: cid, target: t, iid } => {
            out[0] = 1.0;
            let hand = &st.hands[me as usize];
            let u = match iid {
                Some(i) => hand.iter().find(|x| x.iid == *i),
                None => None,
            }.or_else(|| hand.iter().find(|x| x.card == *cid));
            if let Some(u) = u {
                let s = placement_strength(st, u);
                card_vec(st, u, s, out);
                strength = Some(s);
            }
            if let Target::Cr(c) = t {
                target = Some(*c);
            }
        }
        Action::Roam { origin, target: t } => {
            out[1] = 1.0;
            if let Some(u) = st.stacks[*origin as usize].last() {
                let s = effective_strength(st, u, None);
                card_vec(st, u, s, out);
                strength = Some(s);
            }
            match t {
                Target::Cr(c) => target = Some(*c),
                Target::Hq(_) => extra[7] = 1.0,
            }
        }
        Action::Draw => out[2] = 1.0,
        Action::Pass => out[5] = 1.0,
        Action::Choice(v) => match v {
            Value::Str(s) if *s == SKIP => out[5] = 1.0,
            Value::Str(s) if gm.by_name.contains_key(*s) => {
                out[3] = 1.0;
                target = Some(gm.by_name[*s]);
            }
            _ => {
                out[4] = 1.0;
                opt[legal_index.min(OPT_N - 1)] = 1.0;
            }
        },
    }
    if out.len() == KINDS {
        out.resize(KINDS + card_n, 0.0);
    }
    debug_assert_eq!(out.len(), KINDS + card_n);
    let where_at = KINDS + card_n + slot_n;
    if let Some(cr) = target {
        slot_vec(st, me, cr, out);
        debug_assert_eq!(out.len(), where_at);
        out.resize(where_at + BOARD_SLOTS, 0.0);
        if let Some(k) = gm.sorted.iter().position(|&c| c == cr) {
            if k < BOARD_SLOTS {
                out[where_at + k] = 1.0;
            }
        }
        let stack = &st.stacks[cr as usize];
        let top = stack.last();
        extra[0] = if top.map_or(false, |t| t.owner == opp) { 1.0 } else { 0.0 };
        if let (Some(t), Some(s)) = (top, strength) {
            extra[1] = (s - effective_strength(st, t, None)) as f64 / 10.0;
        }
        extra[2] = if top.is_none() { 1.0 } else { 0.0 };
        extra[3] = if gm.hq_front[me as usize].contains(&cr) { 1.0 } else { 0.0 };
        extra[4] = if gm.hq_front[opp as usize].contains(&cr) { 1.0 } else { 0.0 };
        let mut en = 0; let mut al = 0;
        for &n in gm.neighbors(cr) {
            if let Some(t) = st.stacks[n as usize].last() {
                if t.owner == opp { en += 1; } else if t.owner == me { al += 1; }
            }
        }
        extra[5] = en as f64 / 4.0;
        extra[6] = al as f64 / 4.0;
    } else {
        out.resize(where_at + BOARD_SLOTS, 0.0);
    }
    out.extend_from_slice(&extra);
    out.extend_from_slice(&opt);
}

static GIVEN: std::sync::Mutex<Vec<(String, std::sync::Arc<CandNet>)>> = std::sync::Mutex::new(Vec::new());

/// A network handed over as text under the name a spec's `cand=` will ask for.
pub fn give(name: &str, text: &str) -> Result<(), String> {
    let net = std::sync::Arc::new(CandNet::from_json(text)?);
    let mut g = GIVEN.lock().unwrap();
    g.retain(|(n, _)| n != name);
    g.push((name.to_string(), net));
    Ok(())
}

/// The network a spec's `cand=` names: one handed over under that name, else the file at that path (read once).
pub fn named(name: &str) -> Result<std::sync::Arc<CandNet>, String> {
    if let Some((_, net)) = GIVEN.lock().unwrap().iter().find(|(n, _)| n == name) {
        return Ok(net.clone());
    }
    let net = std::sync::Arc::new(CandNet::load(name)?);
    GIVEN.lock().unwrap().push((name.to_string(), net.clone()));
    Ok(net)
}

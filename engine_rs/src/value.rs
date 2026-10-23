//! Plain JSON-shaped data, the way the Python engine keeps its effect steps, pending choices and scheduled timers:
//! nested maps and lists of strings, ints, bools and null. Kept dynamic on purpose so a step's keys are exactly the
//! Python engine's (the replay oracle compares the serialised position field by field). Keys and strings are
//! `&'static str`: the engine's own are literals, card ids and crossroad names are leaked once per process, and
//! strings read from JSON are interned.

use indexmap::IndexMap;
use rustc_hash::FxBuildHasher;
use serde_json as sj;
use std::collections::HashSet;
use std::sync::Mutex;

#[derive(Clone, Debug, PartialEq)]
pub enum Value {
    Null,
    Bool(bool),
    Int(i64),
    Str(&'static str),
    List(Vec<Value>),
    Map(IndexMap<&'static str, Value, FxBuildHasher>),
}

pub type Map = IndexMap<&'static str, Value, FxBuildHasher>;

static INTERNED: Mutex<Option<HashSet<&'static str>>> = Mutex::new(None);

/// A `&'static str` equal to `s`: the one interned before, or `s` leaked. Only for strings from outside the engine
/// (JSON, Python); the engine's own strings are literals or the per-process card and crossroad names.
pub fn intern(s: &str) -> &'static str {
    let mut guard = INTERNED.lock().unwrap();
    let set = guard.get_or_insert_with(HashSet::new);
    if let Some(x) = set.get(s) {
        return x;
    }
    let leaked: &'static str = Box::leak(s.to_string().into_boxed_str());
    set.insert(leaked);
    leaked
}

impl Value {
    pub fn map() -> Map {
        Map::default()
    }
    pub fn s(v: &'static str) -> Value {
        Value::Str(v)
    }
    pub fn i(v: i64) -> Value {
        Value::Int(v)
    }
    pub fn as_i64(&self) -> Option<i64> {
        match self {
            Value::Int(i) => Some(*i),
            Value::Bool(b) => Some(*b as i64),
            _ => None,
        }
    }
    pub fn as_str(&self) -> Option<&'static str> {
        match self {
            Value::Str(s) => Some(s),
            _ => None,
        }
    }
    pub fn as_bool(&self) -> bool {
        match self {
            Value::Bool(b) => *b,
            Value::Int(i) => *i != 0,
            Value::Null => false,
            Value::Str(s) => !s.is_empty(),
            Value::List(l) => !l.is_empty(),
            Value::Map(m) => !m.is_empty(),
        }
    }
    pub fn as_list(&self) -> Option<&Vec<Value>> {
        match self {
            Value::List(l) => Some(l),
            _ => None,
        }
    }
    pub fn as_list_mut(&mut self) -> Option<&mut Vec<Value>> {
        match self {
            Value::List(l) => Some(l),
            _ => None,
        }
    }
    pub fn as_map(&self) -> Option<&Map> {
        match self {
            Value::Map(m) => Some(m),
            _ => None,
        }
    }
    pub fn as_map_mut(&mut self) -> Option<&mut Map> {
        match self {
            Value::Map(m) => Some(m),
            _ => None,
        }
    }
    pub fn is_null(&self) -> bool {
        matches!(self, Value::Null)
    }

    pub fn to_json(&self) -> sj::Value {
        match self {
            Value::Null => sj::Value::Null,
            Value::Bool(b) => sj::Value::Bool(*b),
            Value::Int(i) => sj::Value::from(*i),
            Value::Str(s) => sj::Value::String(s.to_string()),
            Value::List(l) => sj::Value::Array(l.iter().map(|v| v.to_json()).collect()),
            Value::Map(m) => sj::Value::Object(m.iter().map(|(k, v)| (k.to_string(), v.to_json())).collect()),
        }
    }

    pub fn from_json(v: &sj::Value) -> Value {
        match v {
            sj::Value::Null => Value::Null,
            sj::Value::Bool(b) => Value::Bool(*b),
            sj::Value::Number(n) => Value::Int(n.as_i64().unwrap_or_else(|| n.as_f64().unwrap_or(0.0) as i64)),
            sj::Value::String(s) => Value::Str(intern(s)),
            sj::Value::Array(a) => Value::List(a.iter().map(Value::from_json).collect()),
            sj::Value::Object(o) => Value::Map(o.iter().map(|(k, v)| (intern(k), Value::from_json(v))).collect()),
        }
    }
}

pub fn m_get_i(m: &Map, k: &str) -> Option<i64> {
    m.get(k).and_then(|v| v.as_i64())
}
pub fn m_get_s(m: &Map, k: &str) -> Option<&'static str> {
    m.get(k).and_then(|v| v.as_str())
}
pub fn m_flag(m: &Map, k: &str) -> bool {
    m.get(k).map(|v| v.as_bool()).unwrap_or(false)
}

#[macro_export]
macro_rules! vmap {
    ($($k:expr => $v:expr),* $(,)?) => {{
        let mut m = $crate::value::Map::default();
        $( m.insert($k, $v); )*
        m
    }};
}

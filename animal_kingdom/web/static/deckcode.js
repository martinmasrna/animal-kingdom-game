// Deck codes (Hearthstone-style): readable lines for people and agents, then one compact line the game reads.
//   ### Colony copy
//   # 1x (0) Vesper
//   # 3x (1) Worker Ant
//   AK1:BAUEfw...
// The AK1 line is each card as a varint of (card number * 4 + copies), base64url. Import takes the AK1 line, or failing that,
// any lines shaped like "3x Worker Ant" (with or without the "(1)" strength), so a list typed by hand or by an agent works.
import { CARD_NUMS } from './cardnums.js';

const NUM = Object.fromEntries(CARD_NUMS.map((id, i) => [id, i + 1]));
const RANK = { legendary: 0, rare: 1, common: 2 }, sv = c => c.str === '*' ? -1 : c.str;
const b64 = bytes => btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const unb64 = s => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/')), ch => ch.charCodeAt(0));

// cards: {id: card}; list: card ids, one per copy.
export function encodeDeck(name, list, cards) {
  const n = {}; list.forEach(id => n[id] = (n[id] || 0) + 1);
  const ids = Object.keys(n).sort((a, b) => RANK[cards[a].rarity] - RANK[cards[b].rarity] || sv(cards[a]) - sv(cards[b]) || cards[a].name.localeCompare(cards[b].name));
  const bytes = [];
  for (const id of ids) { let v = NUM[id] * 4 + n[id]; do { bytes.push((v & 127) | (v > 127 ? 128 : 0)); v >>= 7; } while (v); }
  return [`### ${name}`, ...ids.map(id => `# ${n[id]}x (${cards[id].str}) ${cards[id].name}`), '#', 'AK1:' + b64(bytes)].join('\n');
}

// Returns {name, list} or null when the text holds no deck.
export function decodeDeck(text, cards) {
  let list = [];
  const m = String(text).match(/AK1:([A-Za-z0-9_-]+)/);
  if (m) try {
    const bytes = unb64(m[1]);
    for (let i = 0, v = 0, s = 0; i < bytes.length; i++) {
      v |= (bytes[i] & 127) << s; s += 7;
      if (!(bytes[i] & 128)) { const id = CARD_NUMS[(v >> 2) - 1], k = v & 3; if (cards[id]) for (let j = 0; j < k; j++) list.push(id); v = 0; s = 0; }
    }
  } catch { list = []; }
  if (!list.length) {
    const byName = Object.fromEntries(Object.values(cards).map(c => [c.name.toLowerCase(), c.id]));
    for (const line of String(text).split('\n')) {
      const q = line.match(/(\d+)\s*x\s*(?:\(\S+\)\s*)?(.+?)\s*$/i), id = q && byName[q[2].toLowerCase()];
      if (id) for (let j = 0; j < Math.min(+q[1], 3); j++) list.push(id);
    }
  }
  const name = (String(text).match(/^###\s*(.+)$/m) || [])[1];
  return list.length ? { name: (name || 'Imported deck').trim().slice(0, 40), list: list.slice(0, 30) } : null;   // a deck holds 30
}

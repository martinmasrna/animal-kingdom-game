// What the player does that only the client sees (web/events.py keeps it; web/playtest.py reads it back): the screens
// visited, each tutorial step reached, feedback opened, decks changed, and the page's own errors. Queued and sent in
// batches every few seconds and when the page hides; never shown, never blocking. Without a profile key nothing is sent.
const queue = [];
const key = () => { try { return localStorage.getItem('ak:key') || ''; } catch { return ''; } };

export function track(kind, data = {}) {
  queue.push({ kind, data: { ...data, at: Math.round(performance.now() / 100) / 10 } });
  if (queue.length >= 40) flush();
}

function flush() {
  if (!queue.length || !key()) return;
  const events = queue.splice(0, 50);
  fetch('/api/events', { method: 'POST', keepalive: true, body: JSON.stringify({ events }),
    headers: { 'Content-Type': 'application/json', 'X-AK-Key': key() } }).catch(() => {});
}

setInterval(flush, 5000);
addEventListener('visibilitychange', () => { track(document.hidden ? 'hidden' : 'shown'); if (document.hidden) flush(); });
addEventListener('pagehide', flush);
addEventListener('error', e => track('js_error', { msg: String(e.message).slice(0, 300), src: `${(e.filename || '').split('/').pop()}:${e.lineno}` }));
addEventListener('unhandledrejection', e => track('js_error', { msg: String(e.reason && (e.reason.message || e.reason)).slice(0, 300) }));

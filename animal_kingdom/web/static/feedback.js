// Feedback: one box for anything (a bug, an idea, something that felt off), sent to Martin with the moment it came
// from (web/feedback.py). No categories: sorting is the reader's job, not the player's. Keys typed in the box stay in it
// (Space, the arrows and Escape drive the game and the replay).

export function openFeedback({ api, toast, context, view }) {
  if (document.querySelector('.fbov')) return;
  const ov = document.createElement('div');
  ov.className = 'fbov';
  ov.innerHTML = `<div class="fbbox"><b>Feedback</b>
    <textarea class="field" maxlength="4000" placeholder="A bug, an idea, anything that felt off..."></textarea>
    <p>Sent with what's on your screen right now, so a bug can be seen as it happened.</p>
    <div class="btns"><button class="slab" data-x="cancel">Cancel</button><button class="play" data-x="send">Send</button></div></div>`;
  document.body.appendChild(ov);
  const box = ov.querySelector('textarea'), send = ov.querySelector('[data-x="send"]'), close = () => ov.remove();
  box.focus();
  ov.addEventListener('keydown', e => { e.stopPropagation(); if (e.key === 'Escape') close(); });
  ov.onclick = e => { if (e.target === ov) close(); };
  ov.querySelector('[data-x="cancel"]').onclick = close;
  send.onclick = async () => {
    const text = box.value.trim();
    if (!text) return box.focus();
    send.disabled = true;
    const r = await api('/api/feedback', { method: 'POST', body: JSON.stringify({ text, context: {
      ...context, screen: location.hash || '#/', window: `${innerWidth}x${innerHeight} @${devicePixelRatio}x`, browser: navigator.userAgent,
      local_time: new Date().toString() }, view }) }).catch(() => null);
    if (!r || !r.ok) { send.disabled = false; return toast(r ? await r.text() : 'Could not send: are you online?'); }
    close(); toast('Thanks! Every message gets read.', true);
  };
}
